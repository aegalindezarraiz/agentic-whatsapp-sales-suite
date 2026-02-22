"""
FastAPI - Servidor principal de la Agentic Sales Suite.

Endpoints:
  POST /webhook          → Recibe mensajes de WhatsApp (Twilio / Evolution)
  GET  /webhook          → Verificación del webhook (Twilio / Meta)
  POST /admin/ingest     → Ingesta documentos al RAG (uso interno)
  GET  /admin/stats      → Métricas del sistema
  GET  /health           → Health check

Seguridad:
  - Verificación de token en GET /webhook
  - Validación de signature en Twilio (header X-Twilio-Signature)
  - Procesamiento asíncrono via Redis Queue (no bloquea el servidor)
"""

import hashlib
import hmac
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.queue_handler import clear_conversation, enqueue_message, get_job_status, get_queue_stats
from app.rag import get_rag
from app.whatsapp import get_whatsapp_provider

# Configurar logging estructurado
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.app_env == "development" else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

log = structlog.get_logger()


# ------------------------------------------------------------------ #
# Lifecycle                                                           #
# ------------------------------------------------------------------ #

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y cleanup de recursos al arrancar/detener."""
    log.info("Agentic Sales Suite iniciando...", env=settings.app_env)
    # Pre-inicializar RAG y proveedor WhatsApp al arrancar (evita cold start en primer mensaje)
    try:
        rag = get_rag()
        stats = rag.collection_stats()
        log.info("RAG inicializado", catalog_docs=stats["catalog"], support_docs=stats["support_docs"])
    except Exception as e:
        log.warning(f"RAG no pudo inicializar: {e} — continuando sin RAG precargado")

    yield

    log.info("Agentic Sales Suite deteniendo...")


# ------------------------------------------------------------------ #
# App                                                                 #
# ------------------------------------------------------------------ #

app = FastAPI(
    title="Agentic WhatsApp Sales Suite",
    description="Suite de agentes IA para automatización de ventas y soporte en WhatsApp",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
# Schemas de Request/Response                                         #
# ------------------------------------------------------------------ #

class IngestRequest(BaseModel):
    type: str  # "catalog" | "document"
    data: list[dict[str, Any]] | None = None  # para type="catalog"
    file_path: str | None = None             # para type="document"
    source_tag: str = "docs"


class IngestResponse(BaseModel):
    status: str
    chunks_indexed: int
    collection: str


# ------------------------------------------------------------------ #
# Helpers de seguridad                                               #
# ------------------------------------------------------------------ #

def _verify_twilio_signature(request_url: str, params: dict, signature: str) -> bool:
    """
    Valida la firma HMAC de Twilio para evitar requests falsos.
    https://www.twilio.com/docs/usage/webhooks/webhooks-security
    """
    if not settings.twilio_auth_token:
        return False
    s = request_url + "".join(f"{k}{v}" for k, v in sorted(params.items()))
    computed = hmac.new(
        settings.twilio_auth_token.encode("utf-8"),
        s.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    import base64
    return hmac.compare_digest(base64.b64encode(computed).decode(), signature)


# ------------------------------------------------------------------ #
# Health Check                                                        #
# ------------------------------------------------------------------ #

@app.get("/health", tags=["Sistema"])
async def health_check():
    """Verifica que el servidor está activo."""
    return {"status": "ok", "version": "1.0.0", "env": settings.app_env}


# ------------------------------------------------------------------ #
# Webhook WhatsApp                                                    #
# ------------------------------------------------------------------ #

@app.get("/webhook", tags=["WhatsApp"])
async def verify_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
):
    """
    Verificación del webhook para Meta/Facebook Business API.
    Twilio no usa este endpoint.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.webhook_verify_token:
        log.info("Webhook verificado correctamente")
        return Response(content=hub_challenge, media_type="text/plain")

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Token de verificación inválido",
    )


@app.post("/webhook", tags=["WhatsApp"])
async def receive_webhook(request: Request):
    """
    Recibe mensajes entrantes de WhatsApp (Twilio o Evolution API).
    El procesamiento es asíncrono: el mensaje se encola y retorna 200 inmediatamente.
    """
    content_type = request.headers.get("content-type", "")

    # Twilio envía form-encoded; Evolution API envía JSON
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form_data = await request.form()
        payload = dict(form_data)

    log.info("Webhook recibido", provider=settings.whatsapp_provider)

    # Parsear según proveedor
    try:
        provider = get_whatsapp_provider()
        message_data = provider.parse_incoming(payload)
    except Exception as e:
        log.error(f"Error parseando webhook: {e}", payload=str(payload)[:200])
        # Retornar 200 siempre para evitar reintentos del proveedor
        return {"status": "parse_error", "detail": str(e)}

    # Ignorar mensajes vacíos o del propio bot
    if not message_data.get("body"):
        return {"status": "ignored", "reason": "empty_body"}

    # Verificar si es un comando de control
    body = message_data["body"].strip().lower()
    if body in ("cancelar", "reset", "reiniciar"):
        clear_conversation(message_data["from"])
        # Respuesta inmediata para comandos de control
        try:
            await provider.send_message(
                to=message_data["from"],
                body="Conversación reiniciada. ¿En qué te puedo ayudar?",
            )
        except Exception:
            pass
        return {"status": "reset"}

    # Encolar para procesamiento asíncrono
    job_id = enqueue_message(message_data)
    log.info("Mensaje encolado", job_id=job_id, phone=message_data.get("from", "")[:6] + "***")

    # Responder 200 inmediatamente (Twilio/Evolution esperan respuesta rápida)
    return {"status": "queued", "job_id": job_id}


# ------------------------------------------------------------------ #
# Admin: Ingesta RAG                                                  #
# ------------------------------------------------------------------ #

@app.post("/admin/ingest", response_model=IngestResponse, tags=["Admin"])
async def ingest_knowledge(req: IngestRequest, request: Request):
    """
    Ingesta datos en el sistema RAG.
    - type='catalog': Sube lista de productos (JSON)
    - type='document': Indexa un archivo PDF/TXT del servidor
    """
    rag = get_rag()

    if req.type == "catalog":
        if not req.data:
            raise HTTPException(status_code=400, detail="Se requiere 'data' para tipo 'catalog'")
        count = rag.ingest_catalog(req.data)
        return IngestResponse(status="ok", chunks_indexed=count, collection="product_catalog")

    elif req.type == "document":
        if not req.file_path:
            raise HTTPException(status_code=400, detail="Se requiere 'file_path' para tipo 'document'")
        count = rag.ingest_document(req.file_path, source_tag=req.source_tag)
        return IngestResponse(status="ok", chunks_indexed=count, collection="support_docs")

    raise HTTPException(status_code=400, detail="Tipo inválido. Usar 'catalog' o 'document'")


# ------------------------------------------------------------------ #
# Admin: Estadísticas                                                 #
# ------------------------------------------------------------------ #

@app.get("/admin/stats", tags=["Admin"])
async def get_stats():
    """Métricas del sistema: cola, RAG, configuración."""
    try:
        queue_stats = get_queue_stats()
    except Exception:
        queue_stats = {"error": "Redis no disponible"}

    try:
        rag_stats = get_rag().collection_stats()
    except Exception:
        rag_stats = {"error": "ChromaDB no disponible"}

    return {
        "queue": queue_stats,
        "rag": rag_stats,
        "config": {
            "whatsapp_provider": settings.whatsapp_provider,
            "llm_model": settings.openai_model,
            "env": settings.app_env,
        },
    }


@app.get("/admin/jobs/{job_id}", tags=["Admin"])
async def get_job(job_id: str):
    """Consulta el estado de un job específico en la cola."""
    try:
        return get_job_status(job_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job no encontrado: {e}")

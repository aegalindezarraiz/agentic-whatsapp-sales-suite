"""
FastAPI - Servidor principal de la Agentic Sales Suite.

Endpoints:
  POST /webhook/whatsapp   → Recibe mensajes de WhatsApp (Twilio / Evolution)
  GET  /webhook/whatsapp   → Verificación del webhook (Meta hub.challenge)
  GET  /webhook            → Alias de verificación (compatibilidad legacy)
  POST /webhook            → Alias para WhatsApp (compatibilidad legacy)
  POST /webhook/telegram   → Recibe updates de Telegram Bot API
  POST /admin/ingest       → Ingesta documentos al RAG
  GET  /admin/stats        → Métricas del sistema
  GET  /health             → Health check
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
from app.queue_handler import (
    clear_conversation,
    enqueue_message,
    enqueue_telegram_message,
    get_job_status,
    get_queue_stats,
)
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
        structlog.dev.ConsoleRenderer()
        if settings.app_env == "development"
        else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
log = structlog.get_logger()


# ------------------------------------------------------------------ #
# Lifecycle
# ------------------------------------------------------------------ #

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicialización y cleanup de recursos al arrancar/detener."""
    log.info("Agentic Sales Suite iniciando...", env=settings.app_env)
    try:
        rag = get_rag()
        stats = rag.collection_stats()
        log.info("RAG inicializado", catalog_docs=stats["catalog"], support_docs=stats["support_docs"])
    except Exception as e:
        log.warning(f"RAG no pudo inicializar: {e} — continuando sin RAG precargado")

    # Verificar proveedor Telegram si está configurado
    if settings.telegram_bot_token:
        try:
            from app.telegram import get_telegram_provider
            tg = get_telegram_provider()
            log.info("Telegram provider inicializado", bot=settings.telegram_bot_username)
        except Exception as e:
            log.warning(f"Telegram no pudo inicializar: {e}")

    yield
    log.info("Agentic Sales Suite deteniendo...")


# ------------------------------------------------------------------ #
# App
# ------------------------------------------------------------------ #

app = FastAPI(
    title="Agentic WhatsApp + Telegram Sales Suite",
    description="Suite de agentes IA para automatización de ventas y soporte en WhatsApp y Telegram",
    version="2.0.0",
    lifespan=lifespan,
)

_cors_origins = settings.cors_origins.split(",") if settings.cors_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ #
# Schemas
# ------------------------------------------------------------------ #

class IngestRequest(BaseModel):
    type: str                            # "catalog" | "document"
    data: list[dict[str, Any]] | None = None
    file_path: str | None = None
    source_tag: str = "docs"


class IngestResponse(BaseModel):
    status: str
    chunks_indexed: int
    collection: str


# ------------------------------------------------------------------ #
# Helpers de seguridad
# ------------------------------------------------------------------ #

def _verify_twilio_signature(request_url: str, params: dict, signature: str) -> bool:
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
# Health Check
# ------------------------------------------------------------------ #

@app.get("/health", tags=["Sistema"])
async def health_check():
    """Verifica que el servidor está activo."""
    return {"status": "ok", "version": "2.0.0", "env": settings.app_env}


# ------------------------------------------------------------------ #
# Webhook WhatsApp — GET (verificación Meta hub.challenge)
# ------------------------------------------------------------------ #

@app.get("/webhook/whatsapp", tags=["WhatsApp"])
@app.get("/webhook", tags=["WhatsApp"])
async def verify_whatsapp_webhook(
    hub_mode: str | None = Query(None, alias="hub.mode"),
    hub_challenge: str | None = Query(None, alias="hub.challenge"),
    hub_verify_token: str | None = Query(None, alias="hub.verify_token"),
):
    """
    Verificación del webhook para Meta/Facebook Business API.
    También acepta en /webhook para compatibilidad con configuraciones previas.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.webhook_verify_token:
        log.info("Webhook WhatsApp verificado correctamente")
        return Response(content=hub_challenge, media_type="text/plain")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Token de verificación inválido",
    )


# ------------------------------------------------------------------ #
# Webhook WhatsApp — POST (mensajes entrantes)
# ------------------------------------------------------------------ #

async def _handle_whatsapp_payload(request: Request) -> dict:
    """Parsea y encola un mensaje de WhatsApp. Retorna dict de respuesta."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
    else:
        form_data = await request.form()
        payload = dict(form_data)

    log.info("Webhook WhatsApp recibido", provider=settings.whatsapp_provider)

    try:
        provider = get_whatsapp_provider()
        message_data = provider.parse_incoming(payload)
    except Exception as e:
        log.error(f"Error parseando webhook WhatsApp: {e}", payload=str(payload)[:200])
        return {"status": "parse_error", "detail": str(e)}

    if not message_data.get("body"):
        return {"status": "ignored", "reason": "empty_body"}

    body = message_data["body"].strip().lower()
    if body in ("cancelar", "reset", "reiniciar"):
        clear_conversation(message_data["from"])
        try:
            await provider.send_message(
                to=message_data["from"],
                body="Conversación reiniciada. ¿En qué te puedo ayudar? 😊",
            )
        except Exception:
            pass
        return {"status": "reset"}

    job_id = enqueue_message(message_data)
    log.info("Mensaje WhatsApp encolado", job_id=job_id, phone=message_data.get("from", "")[:6] + "***")
    return {"status": "queued", "job_id": job_id}


@app.post("/webhook/whatsapp", tags=["WhatsApp"])
async def receive_whatsapp_webhook(request: Request):
    """
    Recibe mensajes entrantes de WhatsApp (Twilio o Evolution API).
    El procesamiento es asíncrono: encola y retorna 200 inmediatamente.
    """
    return await _handle_whatsapp_payload(request)


@app.post("/webhook", tags=["WhatsApp"])
async def receive_webhook_legacy(request: Request):
    """
    Alias de /webhook/whatsapp para compatibilidad con configuraciones previas.
    """
    return await _handle_whatsapp_payload(request)


# ------------------------------------------------------------------ #
# Webhook Telegram — POST (updates del bot)
# ------------------------------------------------------------------ #

@app.post("/webhook/telegram", tags=["Telegram"])
async def receive_telegram_webhook(request: Request):
    """
    Recibe updates de Telegram enviados por la Bot API (setWebhook).

    Telegram envía un objeto Update en JSON con cada mensaje nuevo.
    El procesamiento es asíncrono: encola y retorna 200 inmediatamente.
    Telegram reintenta si no recibe 200 en < 60s.
    """
    if not settings.telegram_bot_token:
        log.warning("Telegram webhook recibido pero TELEGRAM_BOT_TOKEN no configurado")
        return {"status": "disabled"}

    try:
        payload = await request.json()
    except Exception as e:
        log.error(f"Error leyendo payload Telegram: {e}")
        return {"status": "parse_error"}

    log.info("Webhook Telegram recibido", update_id=payload.get("update_id"))

    try:
        from app.telegram import get_telegram_provider
        provider = get_telegram_provider()
        message_data = provider.parse_incoming(payload)
    except Exception as e:
        log.error(f"Error parseando update Telegram: {e}")
        return {"status": "parse_error", "detail": str(e)}

    # Ignorar updates sin texto (fotos, stickers, etc. — por ahora)
    if not message_data.get("body"):
        return {"status": "ignored", "reason": "no_text"}

    chat_id = message_data["from"]
    body = message_data["body"].strip()

    # Comandos de control
    if message_data.get("is_command"):
        command = message_data.get("command", "")

        if command in ("start", "hola", "hello"):
            try:
                from app.telegram import get_telegram_provider
                tg = get_telegram_provider()
                bot_name = settings.telegram_bot_username or "Agentic Sentinel"
                await tg.send_message(
                    chat_id=chat_id,
                    text=(
                        f"👋 ¡Hola {message_data.get('profile_name', '')}! "
                        f"Soy *{bot_name}*, tu asistente de ventas y soporte.\n\n"
                        "Puedo ayudarte con:\n"
                        "• 🛍️ Información de productos y precios\n"
                        "• 🔧 Soporte técnico\n"
                        "• ❓ Consultas generales\n\n"
                        "¿En qué te puedo ayudar hoy?"
                    ),
                )
            except Exception as ex:
                log.error(f"Error enviando mensaje de bienvenida Telegram: {ex}")
            return {"status": "welcomed"}

        if command in ("reset", "reiniciar", "cancelar"):
            clear_conversation(str(chat_id))
            try:
                from app.telegram import get_telegram_provider
                tg = get_telegram_provider()
                await tg.send_message(
                    chat_id=chat_id,
                    text="✅ Conversación reiniciada. ¿En qué te puedo ayudar?",
                )
            except Exception:
                pass
            return {"status": "reset"}

        if command == "help":
            try:
                from app.telegram import get_telegram_provider
                tg = get_telegram_provider()
                await tg.send_message(
                    chat_id=chat_id,
                    text=(
                        "📋 *Comandos disponibles:*\n\n"
                        "/start — Iniciar conversación\n"
                        "/reset — Reiniciar conversación\n"
                        "/help  — Ver esta ayuda\n\n"
                        "También puedes escribirme directamente y te responderé 😊"
                    ),
                )
            except Exception:
                pass
            return {"status": "help_sent"}

    # Encolar mensaje normal para el agente
    job_id = enqueue_telegram_message(message_data)
    log.info(
        "Mensaje Telegram encolado",
        job_id=job_id,
        chat_id=str(chat_id)[:6] + "***",
        user=message_data.get("profile_name", "unknown"),
    )

    # Enviar "typing..." inmediatamente (UX)
    try:
        from app.telegram import get_telegram_provider
        tg = get_telegram_provider()
        await tg.send_action(chat_id=chat_id, action="typing")
    except Exception:
        pass

    return {"status": "queued", "job_id": job_id}


# ------------------------------------------------------------------ #
# Admin: Ingesta RAG
# ------------------------------------------------------------------ #

@app.post("/admin/ingest", response_model=IngestResponse, tags=["Admin"])
async def ingest_knowledge(req: IngestRequest, request: Request):
    """
    Ingesta datos en el sistema RAG.
    - type='catalog':  Sube lista de productos (JSON)
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
# Admin: Estadísticas
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
            "telegram_enabled": bool(settings.telegram_bot_token),
            "telegram_bot": settings.telegram_bot_username,
        },
    }


@app.get("/admin/jobs/{job_id}", tags=["Admin"])
async def get_job(job_id: str):
    """Consulta el estado de un job específico en la cola."""
    try:
        return get_job_status(job_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job no encontrado: {e}")

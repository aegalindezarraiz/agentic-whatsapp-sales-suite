"""
Sistema de colas con Redis + RQ para procesamiento asíncrono de mensajes.

Diseño:
  - El webhook recibe el mensaje y lo encola inmediatamente (< 1s)
  - Workers independientes procesan los mensajes y ejecutan los agentes
  - Manejo de reintentos automáticos en caso de fallo

Activar workers:
    rq worker whatsapp_messages --url redis://localhost:6379

Escalar:
    rq worker whatsapp_messages --url redis://localhost:6379 &  (x N workers)
"""

import logging
from typing import Any

import redis
from rq import Queue
from rq.job import Job

from app.config import settings

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Conexión Redis                                                      #
# ------------------------------------------------------------------ #

def get_redis_connection() -> redis.Redis:
    """Retorna conexión Redis lista para usar."""
    return redis.from_url(settings.redis_url, decode_responses=False)


def get_queue() -> Queue:
    """Retorna la cola RQ para mensajes de WhatsApp."""
    conn = get_redis_connection()
    return Queue(
        name=settings.redis_queue_name,
        connection=conn,
        default_timeout=120,  # 2 minutos max por job
    )


# ------------------------------------------------------------------ #
# Encolar mensaje                                                     #
# ------------------------------------------------------------------ #

def enqueue_message(message_data: dict[str, Any]) -> str:
    """
    Encola un mensaje entrante de WhatsApp para procesamiento asíncrono.

    Args:
        message_data: Dict con from, body, message_id, timestamp, profile_name

    Returns:
        Job ID para tracking.
    """
    queue = get_queue()

    job = queue.enqueue(
        "app.worker.process_whatsapp_message",  # función del worker
        message_data,
        job_timeout=120,
        result_ttl=3600,  # mantener resultado 1h para debugging
        failure_ttl=86400,  # mantener errores 24h
        retry=3,  # reintentar 3 veces en caso de fallo
    )

    logger.info(f"[Queue] Mensaje encolado — Job ID: {job.id}, From: {message_data.get('from')}")
    return job.id


def get_job_status(job_id: str) -> dict[str, Any]:
    """
    Consulta el estado de un job en la cola.

    Returns:
        Dict con: job_id, status, result, enqueued_at
    """
    conn = get_redis_connection()
    job = Job.fetch(job_id, connection=conn)

    return {
        "job_id": job_id,
        "status": job.get_status().value,
        "result": str(job.result) if job.result else None,
        "enqueued_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "ended_at": job.ended_at.isoformat() if job.ended_at else None,
    }


def get_queue_stats() -> dict[str, int]:
    """Retorna métricas de la cola para monitoreo."""
    queue = get_queue()
    conn = get_redis_connection()

    failed_queue = Queue("failed", connection=conn)

    return {
        "queued": len(queue),
        "started": queue.started_job_registry.count,
        "finished": queue.finished_job_registry.count,
        "failed": queue.failed_job_registry.count,
        "deferred": queue.deferred_job_registry.count,
    }


# ------------------------------------------------------------------ #
# Cache de conversación en Redis                                     #
# ------------------------------------------------------------------ #

CONVERSATION_TTL = 3600 * 2  # 2 horas de contexto de conversación


def get_conversation_history(phone: str) -> str:
    """
    Recupera el historial de conversación de un cliente desde Redis.

    Args:
        phone: Número de WhatsApp del cliente.

    Returns:
        Historial como string, o vacío si no existe.
    """
    conn = get_redis_connection()
    key = f"conv:{phone}"
    history = conn.get(key)
    return history.decode("utf-8") if history else ""


def save_conversation_turn(phone: str, role: str, message: str) -> None:
    """
    Agrega un turno al historial de conversación.

    Args:
        phone:   Número del cliente.
        role:    'cliente' o 'agente'.
        message: Texto del mensaje.
    """
    conn = get_redis_connection()
    key = f"conv:{phone}"

    # Obtener historial existente
    existing = conn.get(key)
    history = existing.decode("utf-8") if existing else ""

    # Agregar nuevo turno (mantener máx 10 turnos = ~2000 tokens)
    new_turn = f"[{role.upper()}]: {message}"
    turns = history.split("\n---\n") if history else []
    turns.append(new_turn)
    turns = turns[-10:]  # Ventana deslizante de 10 turnos

    conn.setex(key, CONVERSATION_TTL, "\n---\n".join(turns))


def clear_conversation(phone: str) -> None:
    """Limpia el historial de un cliente (por ejemplo, cuando escribe 'cancelar')."""
    conn = get_redis_connection()
    conn.delete(f"conv:{phone}")

"""
Worker RQ: procesa mensajes de WhatsApp y Telegram de forma asíncrona.

Este módulo es ejecutado por los workers de RQ, no por FastAPI directamente.
Los agentes CrewAI corren aquí para no bloquear el servidor HTTP.

Ejecutar workers:
  rq worker whatsapp_messages --url redis://localhost:6379

Flujo (WhatsApp y Telegram comparten el mismo pipeline CrewAI):
  1. Recibir message_data de la cola
  2. Recuperar historial de conversación
  3. Clasificar intención (Manager)
  4. Generar respuesta (Sales o Support)
  5. Validar respuesta (QA - Reflexion)
  6. Enviar respuesta por el canal correspondiente
  7. Guardar turno en historial
"""

import asyncio
import logging
import re
from typing import Any

from crewai import Crew, Process

from app.agents import (
    create_manager_agent,
    create_qa_agent,
    create_sales_agent,
    create_support_agent,
)
from app.queue_handler import get_conversation_history, save_conversation_turn
from app.tasks import (
    create_classify_intent_task,
    create_general_response_task,
    create_qa_validation_task,
    create_sales_response_task,
    create_support_response_task,
)
from app.tools import get_manager_tools, get_sales_tools, get_support_tools

logger = logging.getLogger(__name__)

# Palabras clave para routing rápido (pre-procesamiento barato antes de llamar al LLM)
SALES_KEYWORDS = {"precio", "comprar", "costo", "cuánto", "disponible", "stock", "envío", "oferta", "descuento"}
SUPPORT_KEYWORDS = {"error", "problema", "falla", "cómo", "configurar", "instalar", "no funciona", "ayuda técnica"}


def _quick_route(message: str) -> str:
    """
    Routing rápido basado en keywords para evitar una llamada al LLM en casos obvios.
    Retorna: 'VENTAS' | 'SOPORTE_TECNICO' | 'UNKNOWN'
    """
    lower = message.lower()
    sales_score = sum(1 for kw in SALES_KEYWORDS if kw in lower)
    support_score = sum(1 for kw in SUPPORT_KEYWORDS if kw in lower)

    if sales_score > support_score and sales_score > 0:
        return "VENTAS"
    if support_score > sales_score and support_score > 0:
        return "SOPORTE_TECNICO"
    return "UNKNOWN"


def _extract_final_response(qa_output: str) -> str:
    """
    Extrae la respuesta final del output del QA agent.
    Maneja los formatos: 'APROBADO: ...' y 'RECHAZADO: ... CORRECCIÓN: ...'
    """
    if "APROBADO:" in qa_output:
        return qa_output.split("APROBADO:", 1)[1].strip()

    if "CORRECCIÓN:" in qa_output:
        return qa_output.split("CORRECCIÓN:", 1)[1].strip()

    # Si el QA no siguió el formato, devolver el output completo (fallback seguro)
    logger.warning("QA no siguió el formato esperado, usando output completo")
    return qa_output.strip()


def _run_crewai_pipeline(
    user_message: str,
    history: list,
    profile_name: str,
) -> tuple[str, str]:
    """
    Ejecuta el pipeline CrewAI compartido por WhatsApp y Telegram.

    Returns:
        (intent_type, final_response) — tipo de intención detectado y respuesta final.
    """
    quick_route = _quick_route(user_message)

    # Instanciar agentes
    manager = create_manager_agent(tools=get_manager_tools())
    sales = create_sales_agent(tools=get_sales_tools())
    support = create_support_agent(tools=get_support_tools())
    qa = create_qa_agent()

    if quick_route == "VENTAS":
        intent_type = "VENTAS"
        response_task = create_sales_response_task(
            agent=sales,
            user_message=user_message,
            intent_analysis=f"Consulta de VENTAS detectada. Cliente: {profile_name}",
        )
        crew = Crew(
            agents=[sales, qa],
            tasks=[
                response_task,
                create_qa_validation_task(
                    agent=qa,
                    draft_response="{response_task_output}",
                    original_message=user_message,
                ),
            ],
            process=Process.sequential,
            verbose=True,
        )

    elif quick_route == "SOPORTE_TECNICO":
        intent_type = "SOPORTE_TECNICO"
        response_task = create_support_response_task(
            agent=support,
            user_message=user_message,
            intent_analysis=f"Consulta de SOPORTE detectada. Cliente: {profile_name}",
        )
        crew = Crew(
            agents=[support, qa],
            tasks=[
                response_task,
                create_qa_validation_task(
                    agent=qa,
                    draft_response="{response_task_output}",
                    original_message=user_message,
                ),
            ],
            process=Process.sequential,
            verbose=True,
        )

    else:
        intent_type = "CLASIFICACION_LLM"
        classify_task = create_classify_intent_task(
            agent=manager,
            user_message=user_message,
            conversation_history=history,
        )
        general_task = create_general_response_task(
            agent=manager,
            user_message=user_message,
        )
        qa_task = create_qa_validation_task(
            agent=qa,
            draft_response="{general_task_output}",
            original_message=user_message,
        )
        crew = Crew(
            agents=[manager, qa],
            tasks=[classify_task, general_task, qa_task],
            process=Process.sequential,
            verbose=True,
        )

    try:
        crew_result = crew.kickoff(inputs={
            "user_message": user_message,
            "history": history,
            "profile_name": profile_name,
        })
        raw_response = str(crew_result)
    except Exception as e:
        logger.error(f"Error en CrewAI: {e}", exc_info=True)
        raw_response = (
            "Disculpa, tuve un inconveniente técnico. "
            "¿Podrías repetir tu consulta? Estoy aquí para ayudarte."
        )

    final_response = _extract_final_response(raw_response)
    return intent_type, final_response


def process_whatsapp_message(message_data: dict[str, Any]) -> dict[str, Any]:
    """
    Función principal ejecutada por el worker RQ para mensajes de WhatsApp.

    Args:
        message_data: {from, body, message_id, timestamp, profile_name}

    Returns:
        Dict con la respuesta enviada y metadatos del procesamiento.
    """
    phone = message_data.get("from", "")
    user_message = message_data.get("body", "").strip()
    profile_name = message_data.get("profile_name", "Cliente")

    if not user_message:
        logger.warning(f"Mensaje vacío de {phone}, ignorando")
        return {"status": "ignored", "reason": "empty_message"}

    logger.info(f"[Worker/WA] Procesando mensaje de {phone}: '{user_message[:80]}...'")

    # 1. Recuperar historial de conversación (clave: número de teléfono)
    history = get_conversation_history(phone)

    # 2. Ejecutar pipeline CrewAI
    intent_type, final_response = _run_crewai_pipeline(user_message, history, profile_name)

    # 3. Enviar respuesta por WhatsApp
    try:
        from app.whatsapp import get_whatsapp_provider
        provider = get_whatsapp_provider()
        send_result = asyncio.run(provider.send_message(to=phone, body=final_response))
        logger.info(f"[Worker/WA] Respuesta enviada a {phone}")
    except Exception as e:
        logger.error(f"Error enviando WhatsApp a {phone}: {e}", exc_info=True)
        send_result = {"status": "error", "error": str(e)}

    # 4. Guardar turno en historial
    save_conversation_turn(phone, "cliente", user_message)
    save_conversation_turn(phone, "agente", final_response)

    return {
        "status": "processed",
        "channel": "whatsapp",
        "phone": phone,
        "intent_type": intent_type,
        "response_sent": final_response[:200] + "..." if len(final_response) > 200 else final_response,
        "send_result": send_result,
    }


def process_telegram_message(message_data: dict[str, Any]) -> dict[str, Any]:
    """
    Función principal ejecutada por el worker RQ para mensajes de Telegram.

    Args:
        message_data: {chat_id, text, message_id, username, first_name, last_name, timestamp}

    Returns:
        Dict con la respuesta enviada y metadatos del procesamiento.
    """
    chat_id = message_data.get("chat_id", "")
    user_message = message_data.get("text", "").strip()
    first_name = message_data.get("first_name", "")
    last_name = message_data.get("last_name", "")
    username = message_data.get("username", "")
    profile_name = (
        f"{first_name} {last_name}".strip()
        or username
        or f"Telegram_{chat_id}"
    )

    if not user_message:
        logger.warning(f"[Worker/TG] Mensaje vacío de chat_id={chat_id}, ignorando")
        return {"status": "ignored", "reason": "empty_message"}

    logger.info(f"[Worker/TG] Procesando mensaje de {chat_id} ({profile_name}): '{user_message[:80]}...'")

    # 1. Recuperar historial de conversación (clave: chat_id de Telegram)
    conv_key = str(chat_id)
    history = get_conversation_history(conv_key)

    # 2. Ejecutar pipeline CrewAI (mismo que WhatsApp)
    intent_type, final_response = _run_crewai_pipeline(user_message, history, profile_name)

    # 3. Enviar respuesta por Telegram
    try:
        from app.telegram import get_telegram_provider
        provider = get_telegram_provider()
        send_result = asyncio.run(provider.send_message(chat_id=chat_id, text=final_response))
        logger.info(f"[Worker/TG] Respuesta enviada a chat_id={chat_id}")
    except Exception as e:
        logger.error(f"Error enviando Telegram a chat_id={chat_id}: {e}", exc_info=True)
        send_result = {"status": "error", "error": str(e)}

    # 4. Guardar turno en historial
    save_conversation_turn(conv_key, "cliente", user_message)
    save_conversation_turn(conv_key, "agente", final_response)

    return {
        "status": "processed",
        "channel": "telegram",
        "chat_id": chat_id,
        "profile_name": profile_name,
        "intent_type": intent_type,
        "response_sent": final_response[:200] + "..." if len(final_response) > 200 else final_response,
        "send_result": send_result,
    }

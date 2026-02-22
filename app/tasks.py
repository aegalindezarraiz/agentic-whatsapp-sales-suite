"""
Definición de Tasks para la Agentic Sales Suite.

Flujo:
  1. classify_intent_task  → Manager clasifica intención
  2. generate_response_task → Sales o Support genera respuesta con RAG
  3. qa_validation_task     → QA valida o rechaza (patrón Reflexion)
"""

from crewai import Task
from crewai import Agent


def create_classify_intent_task(agent: Agent, user_message: str, conversation_history: str = "") -> Task:
    """
    Task 1: Clasificar la intención del cliente.
    Output estructurado: tipo de consulta + contexto relevante.
    """
    return Task(
        description=(
            f"Analiza el siguiente mensaje de WhatsApp y clasifica la intención del cliente.\n\n"
            f"HISTORIAL PREVIO DE CONVERSACIÓN:\n{conversation_history or 'Sin historial (primera interacción)'}\n\n"
            f"MENSAJE ACTUAL DEL CLIENTE:\n{user_message}\n\n"
            "Determina:\n"
            "1. TIPO DE CONSULTA: [VENTAS | SOPORTE_TECNICO | CONSULTA_GENERAL | QUEJA | SALUDO]\n"
            "2. INTENCIÓN ESPECÍFICA: qué necesita exactamente el cliente\n"
            "3. TONO DEL CLIENTE: [urgente | curioso | molesto | satisfecho | neutro]\n"
            "4. DATOS CLAVE: cualquier información relevante mencionada (producto, problema, etc.)\n"
            "5. PRIORIDAD: [ALTA | MEDIA | BAJA]\n\n"
            "Sé conciso y preciso. Este análisis guiará al especialista que responderá."
        ),
        expected_output=(
            "Un análisis estructurado con: tipo de consulta, intención específica, "
            "tono del cliente, datos clave extraídos, y prioridad de atención. "
            "Formato: texto plano bien organizado, sin JSON."
        ),
        agent=agent,
    )


def create_sales_response_task(agent: Agent, user_message: str, intent_analysis: str = "") -> Task:
    """
    Task 2a: Generar respuesta de ventas usando RAG sobre el catálogo.
    """
    return Task(
        description=(
            f"Genera una respuesta de ventas para este cliente de WhatsApp.\n\n"
            f"ANÁLISIS DE INTENCIÓN:\n{intent_analysis or 'Ver mensaje original'}\n\n"
            f"MENSAJE DEL CLIENTE:\n{user_message}\n\n"
            "INSTRUCCIONES OBLIGATORIAS:\n"
            "1. USA la herramienta search_catalog ANTES de mencionar cualquier producto, precio o disponibilidad.\n"
            "2. Si el cliente pregunta por algo no encontrado en el catálogo, dilo honestamente.\n"
            "3. Escribe como un humano amigable, NO como un bot.\n"
            "4. Adapta el mensaje para WhatsApp: párrafos cortos, emojis moderados si aplica.\n"
            "5. Incluye un call-to-action claro al final (ej: '¿Te gustaría que te enviemos más info?').\n"
            "6. Si detectas alta intención de compra, usa la herramienta update_crm para registrar el lead.\n\n"
            "PROHIBIDO: Inventar precios, plazos de entrega, descuentos o disponibilidad."
        ),
        expected_output=(
            "Un mensaje de WhatsApp listo para enviar al cliente. "
            "Debe ser empático, basado en información real del catálogo, "
            "con un call-to-action apropiado. Máximo 4 párrafos cortos."
        ),
        agent=agent,
    )


def create_support_response_task(agent: Agent, user_message: str, intent_analysis: str = "") -> Task:
    """
    Task 2b: Generar respuesta técnica usando RAG sobre documentación.
    """
    return Task(
        description=(
            f"Resuelve esta consulta técnica de un cliente de WhatsApp.\n\n"
            f"ANÁLISIS DE INTENCIÓN:\n{intent_analysis or 'Ver mensaje original'}\n\n"
            f"MENSAJE DEL CLIENTE:\n{user_message}\n\n"
            "INSTRUCCIONES OBLIGATORIAS:\n"
            "1. USA la herramienta search_docs para buscar en la base de conocimiento ANTES de responder.\n"
            "2. Si la solución requiere pasos, númeralos claramente.\n"
            "3. Si el problema NO está en la documentación, admítelo y ofrece escalar al equipo técnico.\n"
            "4. Escribe de forma clara y simple, evitando jerga técnica innecesaria.\n"
            "5. Al final, pregunta si el problema fue resuelto.\n\n"
            "PROHIBIDO: Inventar soluciones técnicas o procedimientos no documentados."
        ),
        expected_output=(
            "Un mensaje de WhatsApp con la solución técnica clara y verificada. "
            "Si son pasos, enumerados. Si no hay solución disponible, "
            "un mensaje honesto ofreciendo escalamiento. Máximo 5 párrafos."
        ),
        agent=agent,
    )


def create_qa_validation_task(agent: Agent, draft_response: str, original_message: str) -> Task:
    """
    Task 3: Validar respuesta (patrón Reflexion).
    Retorna la respuesta aprobada o rechazada con justificación.
    """
    return Task(
        description=(
            f"Audita la siguiente respuesta ANTES de enviarla al cliente.\n\n"
            f"MENSAJE ORIGINAL DEL CLIENTE:\n{original_message}\n\n"
            f"RESPUESTA GENERADA (BORRADOR):\n{draft_response}\n\n"
            "CRITERIOS DE EVALUACIÓN (responde SÍ/NO a cada uno):\n"
            "[ ] Los datos mencionados (precios, specs, plazos) parecen verificados, no inventados\n"
            "[ ] El tono es empático, cálido y humano (no robótico ni frío)\n"
            "[ ] La respuesta es apropiada para WhatsApp (no demasiado larga o formal)\n"
            "[ ] No hay promesas de descuentos, garantías o plazos no verificados\n"
            "[ ] La respuesta realmente responde lo que el cliente preguntó\n"
            "[ ] No hay información contradictoria o confusa\n\n"
            "DECISIÓN FINAL:\n"
            "- Si TODOS los criterios son SÍ: responde con 'APROBADO: [respuesta tal como está o con ajustes menores]'\n"
            "- Si ALGÚN criterio es NO: responde con 'RECHAZADO: [razón específica]'\n\n"
            "Si rechazas, incluye una versión corregida de la respuesta."
        ),
        expected_output=(
            "Una decisión clara: 'APROBADO: [respuesta final lista para enviar]' "
            "o 'RECHAZADO: [razón] + CORRECCIÓN: [versión mejorada]'. "
            "La respuesta aprobada o corregida debe estar lista para enviarse directamente al cliente."
        ),
        agent=agent,
    )


def create_general_response_task(agent: Agent, user_message: str) -> Task:
    """
    Task para consultas generales o saludos (sin RAG especializado).
    """
    return Task(
        description=(
            f"Responde a este mensaje general de WhatsApp de forma cordial.\n\n"
            f"MENSAJE: {user_message}\n\n"
            "Sé amigable, breve y ofrece las formas en que puedes ayudar "
            "(productos/servicios, soporte técnico). Invita al cliente a preguntar."
        ),
        expected_output=(
            "Un mensaje de bienvenida o respuesta general, "
            "amigable y que invite al cliente a continuar la conversación."
        ),
        agent=agent,
    )

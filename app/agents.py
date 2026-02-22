"""
Definición de agentes especializados para la Agentic Sales Suite.

Arquitectura jerárquica:
  Manager Agent
    ├── Sales Agent      ← convierte consultas en ventas
    └── Support Agent    ← resuelve dudas técnicas vía RAG

Patrón Reflexion:
  QA Agent valida cada respuesta antes de enviarla al cliente.
"""

from crewai import Agent
from langchain_openai import ChatOpenAI
from app.config import settings


def _llm() -> ChatOpenAI:
    """LLM compartido con temperatura baja para mayor precisión."""
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )


def create_manager_agent(tools: list | None = None) -> Agent:
    """
    Agente director: clasifica la intención del cliente y delega
    al especialista correcto (ventas o soporte técnico).
    """
    return Agent(
        role="Director de Comunicaciones",
        goal=(
            "Analizar el mensaje del cliente, clasificar su intención "
            "(compra, soporte técnico, consulta general) y delegar al "
            "especialista adecuado para maximizar satisfacción y conversión."
        ),
        backstory=(
            "Llevas 15 años gestionando equipos de atención al cliente en empresas "
            "de e-commerce. Tu capacidad para leer entre líneas y detectar la "
            "intención real del cliente es legendaria. Nunca pierdes el tiempo en "
            "derivaciones innecesarias: sabes exactamente quién debe responder cada "
            "mensaje y en qué tono."
        ),
        tools=tools or [],
        llm=_llm(),
        allow_delegation=True,
        verbose=True,
        max_iter=5,
    )


def create_sales_agent(tools: list | None = None) -> Agent:
    """
    Agente de ventas: convierte consultas en leads cualificados o ventas cerradas.
    Usa RAG para responder con información real del catálogo.
    """
    return Agent(
        role="Consultor de Ventas Proactivo",
        goal=(
            "Convertir consultas de WhatsApp en ventas cerradas o leads cualificados, "
            "usando SIEMPRE información real del catálogo. Nunca inventar precios ni "
            "características. Ser persuasivo de forma ética."
        ),
        backstory=(
            "Eres el mejor vendedor de la empresa. Conoces el catálogo al detalle y "
            "sabes presentar cada producto como la solución perfecta al problema del cliente. "
            "Tu éxito está en escuchar primero y luego ofrecer exactamente lo que el cliente "
            "necesita. Antes de citar cualquier precio o característica, SIEMPRE consultas "
            "el catálogo para no cometer errores."
        ),
        tools=tools or [],
        llm=_llm(),
        allow_delegation=False,
        verbose=True,
        max_iter=3,  # Limitar iteraciones: evita loops costosos
    )


def create_support_agent(tools: list | None = None) -> Agent:
    """
    Agente de soporte técnico: resuelve dudas usando RAG sobre documentación.
    """
    return Agent(
        role="Especialista en Soporte Técnico",
        goal=(
            "Resolver dudas técnicas de forma clara, usando la base de conocimiento. "
            "Si la información no está disponible, admitirlo honestamente y escalar. "
            "Nunca inventar soluciones."
        ),
        backstory=(
            "Llevas años resolviendo los problemas más difíciles de los clientes. "
            "Tu filosofía es simple: respuesta correcta > respuesta rápida. "
            "Consultas los manuales y documentación técnica SIEMPRE antes de responder. "
            "Cuando no sabes algo, lo dices claramente y ofreces escalar al equipo técnico."
        ),
        tools=tools or [],
        llm=_llm(),
        allow_delegation=False,
        verbose=True,
        max_iter=3,
    )


def create_qa_agent() -> Agent:
    """
    Agente QA (patrón Reflexion): valida respuestas antes de enviarlas.
    Detecta alucinaciones, tono inapropiado y compromisos imposibles.
    """
    return Agent(
        role="Auditor de Calidad y Tono",
        goal=(
            "Revisar cada respuesta generada y decidir: APROBADO o RECHAZADO. "
            "Verificar que no haya datos inventados, que el tono sea empático y humano, "
            "que el formato sea apropiado para WhatsApp, y que no haya compromisos "
            "que la empresa no pueda cumplir."
        ),
        backstory=(
            "Eres el guardián de la reputación de la empresa en WhatsApp. "
            "Has visto cómo una sola respuesta incorrecta puede destruir la confianza "
            "de un cliente. Tu lista de verificación es implacable:\n"
            "1. ¿Los datos son verificables y no inventados?\n"
            "2. ¿El tono es cálido y humano (no robótico)?\n"
            "3. ¿La longitud es apropiada para WhatsApp (máx 3-4 párrafos cortos)?\n"
            "4. ¿No hay promesas de descuentos, plazos o condiciones no autorizadas?\n"
            "Si falla cualquier punto, la respuesta es RECHAZADA con justificación."
        ),
        llm=_llm(),
        allow_delegation=False,
        verbose=True,
        max_iter=2,
    )

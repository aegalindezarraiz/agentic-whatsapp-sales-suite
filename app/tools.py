"""
Herramientas (Tools) para los agentes CrewAI.

Principio: Tool Choice limitado → cada agente tiene solo las herramientas
que necesita para evitar confusión y reducir latencia.

  Sales Agent  → search_catalog, update_crm
  Support Agent → search_docs, search_catalog
  Manager Agent → (sin tools, solo delegación)
  QA Agent     → (sin tools, solo análisis de texto)
"""

import json
import logging
from typing import Any

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from app.config import settings
from app.rag import get_rag

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Schemas de entrada (Pydantic v2 para validación)                   #
# ------------------------------------------------------------------ #

class CatalogSearchInput(BaseModel):
    query: str = Field(..., description="Consulta de búsqueda sobre productos, precios o disponibilidad")
    k: int = Field(default=4, ge=1, le=10, description="Número de resultados a retornar")


class DocsSearchInput(BaseModel):
    query: str = Field(..., description="Consulta técnica para buscar en la documentación de soporte")
    k: int = Field(default=4, ge=1, le=10, description="Número de resultados a retornar")


class CRMUpdateInput(BaseModel):
    phone: str = Field(..., description="Número de WhatsApp del cliente")
    name: str = Field(default="", description="Nombre del cliente si fue mencionado")
    interest: str = Field(..., description="Producto o servicio de interés del cliente")
    intent_level: str = Field(
        default="medium",
        description="Nivel de intención de compra: low | medium | high",
    )
    notes: str = Field(default="", description="Notas adicionales sobre la conversación")


# ------------------------------------------------------------------ #
# Tool: Búsqueda en Catálogo                                         #
# ------------------------------------------------------------------ #

class CatalogSearchTool(BaseTool):
    name: str = "search_catalog"
    description: str = (
        "Busca productos, precios, disponibilidad y características en el catálogo de la empresa. "
        "SIEMPRE úsala antes de mencionar cualquier producto al cliente. "
        "Input: consulta en lenguaje natural."
    )
    args_schema: type[BaseModel] = CatalogSearchInput

    def _run(self, query: str, k: int = 4) -> str:
        try:
            rag = get_rag()
            result = rag.search_catalog(query, k=k)
            logger.info("catalog_search", extra={"query": query, "found": bool(result)})
            return result
        except Exception as e:
            logger.error(f"Error en search_catalog: {e}")
            return f"Error al consultar el catálogo: {str(e)}. Informa al cliente que verificarás la información."


# ------------------------------------------------------------------ #
# Tool: Búsqueda en Documentación Técnica                            #
# ------------------------------------------------------------------ #

class DocsSearchTool(BaseTool):
    name: str = "search_docs"
    description: str = (
        "Busca en manuales, guías técnicas y documentación de soporte. "
        "SIEMPRE úsala antes de proporcionar instrucciones técnicas al cliente. "
        "Input: consulta técnica en lenguaje natural."
    )
    args_schema: type[BaseModel] = DocsSearchInput

    def _run(self, query: str, k: int = 4) -> str:
        try:
            rag = get_rag()
            result = rag.search_docs(query, k=k)
            logger.info("docs_search", extra={"query": query, "found": bool(result)})
            return result
        except Exception as e:
            logger.error(f"Error en search_docs: {e}")
            return f"Error al consultar la documentación: {str(e)}. Informa al cliente que escalará su caso."


# ------------------------------------------------------------------ #
# Tool: Actualizar CRM                                               #
# ------------------------------------------------------------------ #

class CRMUpdateTool(BaseTool):
    name: str = "update_crm"
    description: str = (
        "Registra un lead o actualiza la información del cliente en el CRM. "
        "Usar cuando el cliente muestre intención de compra (nivel medium o high), "
        "proporcione sus datos, o solicite seguimiento."
    )
    args_schema: type[BaseModel] = CRMUpdateInput

    def _run(
        self,
        phone: str,
        interest: str,
        name: str = "",
        intent_level: str = "medium",
        notes: str = "",
    ) -> str:
        lead_data = {
            "phone": phone,
            "name": name or "Desconocido",
            "interest": interest,
            "intent_level": intent_level,
            "notes": notes,
            "source": "whatsapp",
        }

        # Integración real con CRM si está configurado
        if settings.crm_api_url and settings.crm_api_key:
            try:
                response = httpx.post(
                    f"{settings.crm_api_url}/leads",
                    json=lead_data,
                    headers={"Authorization": f"Bearer {settings.crm_api_key}"},
                    timeout=5.0,
                )
                response.raise_for_status()
                logger.info(f"Lead registrado en CRM: {phone}")
                return f"Lead registrado exitosamente en CRM. ID: {response.json().get('id', 'N/A')}"
            except httpx.HTTPError as e:
                logger.error(f"Error CRM API: {e}")
                # Fallback: loguear localmente sin fallar al agente
                logger.warning(f"Lead guardado localmente (CRM no disponible): {json.dumps(lead_data)}")
                return "Lead registrado localmente (CRM temporalmente no disponible)."
        else:
            # Modo simulación / desarrollo
            logger.info(f"[CRM SIMULADO] Lead: {json.dumps(lead_data)}")
            return f"Lead registrado: {name or phone} — Interés: {interest} — Nivel: {intent_level}"


# ------------------------------------------------------------------ #
# Factory de sets de herramientas por agente                         #
# ------------------------------------------------------------------ #

def get_sales_tools() -> list[BaseTool]:
    """Herramientas para el agente de ventas."""
    return [CatalogSearchTool(), CRMUpdateTool()]


def get_support_tools() -> list[BaseTool]:
    """Herramientas para el agente de soporte técnico."""
    return [DocsSearchTool(), CatalogSearchTool()]


def get_manager_tools() -> list[BaseTool]:
    """El manager no necesita herramientas directas, solo delega."""
    return []

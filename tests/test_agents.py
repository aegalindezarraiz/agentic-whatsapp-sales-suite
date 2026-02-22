"""
Tests para la configuración y comportamiento de los agentes.
Verifica: roles, objetivos, herramientas asignadas, y parámetros de seguridad.
"""

import pytest
from unittest.mock import patch, MagicMock
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key-for-testing")
os.environ.setdefault("WHATSAPP_PROVIDER", "twilio")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACtest123")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test_auth_token")


class TestAgentConfiguration:
    """Verifica que cada agente tenga la configuración correcta."""

    def test_sales_agent_role(self):
        """El agente de ventas debe tener el rol correcto."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_sales_agent
            agent = create_sales_agent()
            assert agent.role == "Consultor de Ventas Proactivo"

    def test_sales_agent_has_tools_list(self):
        """El agente de ventas debe inicializar con lista de herramientas (vacía o con tools)."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_sales_agent
            agent = create_sales_agent()
            assert isinstance(agent.tools, list)

    def test_sales_agent_cannot_delegate(self):
        """El agente de ventas NO debe poder delegar (evitar loops)."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_sales_agent
            agent = create_sales_agent()
            assert agent.allow_delegation is False

    def test_sales_agent_max_iterations_limited(self):
        """Limitar iteraciones del agente de ventas para evitar loops costosos."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_sales_agent
            agent = create_sales_agent()
            assert agent.max_iter <= 5, "max_iter debe ser <= 5 para evitar loops costosos"

    def test_support_agent_role(self):
        """El agente de soporte debe tener el rol correcto."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_support_agent
            agent = create_support_agent()
            assert agent.role == "Especialista en Soporte Técnico"

    def test_support_agent_cannot_delegate(self):
        """El agente de soporte NO debe poder delegar."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_support_agent
            agent = create_support_agent()
            assert agent.allow_delegation is False

    def test_qa_agent_role(self):
        """El agente QA debe tener el rol correcto."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_qa_agent
            agent = create_qa_agent()
            assert agent.role == "Auditor de Calidad y Tono"

    def test_qa_agent_max_iter_minimal(self):
        """QA solo necesita pocas iteraciones: su trabajo es puntual."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_qa_agent
            agent = create_qa_agent()
            assert agent.max_iter <= 3

    def test_qa_agent_cannot_delegate(self):
        """QA nunca debe delegar."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_qa_agent
            agent = create_qa_agent()
            assert agent.allow_delegation is False

    def test_manager_agent_can_delegate(self):
        """El manager DEBE poder delegar a especialistas."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_manager_agent
            agent = create_manager_agent()
            assert agent.allow_delegation is True

    def test_manager_agent_has_higher_max_iter(self):
        """El manager puede tener más iteraciones que los especialistas."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_manager_agent
            from app.agents import create_sales_agent
            manager = create_manager_agent()
            sales = create_sales_agent()
            assert manager.max_iter >= sales.max_iter

    def test_agents_accept_tools(self):
        """Los agentes deben aceptar herramientas reales en su constructor."""
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_sales_agent, create_support_agent
            from app.tools import CatalogSearchTool, DocsSearchTool

            sales = create_sales_agent(tools=[CatalogSearchTool()])
            support = create_support_agent(tools=[DocsSearchTool()])

            assert len(sales.tools) == 1
            assert len(support.tools) == 1


class TestAgentGoalAlignment:
    """Verifica que los objetivos de los agentes sean los correctos."""

    def test_sales_goal_contains_conversion(self):
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_sales_agent
            agent = create_sales_agent()
            assert "venta" in agent.goal.lower() or "lead" in agent.goal.lower()

    def test_support_goal_contains_resolution(self):
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_support_agent
            agent = create_support_agent()
            assert "resolv" in agent.goal.lower() or "duda" in agent.goal.lower() or "técni" in agent.goal.lower()

    def test_qa_goal_contains_validation(self):
        with patch("app.agents.ChatOpenAI"):
            from app.agents import create_qa_agent
            agent = create_qa_agent()
            goal_lower = agent.goal.lower()
            assert "aprobado" in goal_lower or "rechazado" in goal_lower or "validar" in goal_lower or "revisar" in goal_lower

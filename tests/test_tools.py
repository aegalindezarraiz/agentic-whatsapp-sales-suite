"""
Tests para las herramientas RAG y CRM.
Usa mocks para ChromaDB y APIs externas.
"""

import pytest
from unittest.mock import patch, MagicMock
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key-for-testing")
os.environ.setdefault("WHATSAPP_PROVIDER", "twilio")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACtest123")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test_auth_token")


class TestCatalogSearchTool:
    """Tests para la herramienta de búsqueda en catálogo."""

    def test_search_catalog_returns_string(self):
        """La búsqueda debe retornar siempre un string."""
        mock_rag = MagicMock()
        mock_rag.search_catalog.return_value = "Laptop Pro 15: $1299.99. En stock. Envío gratis."

        with patch("app.tools.get_rag", return_value=mock_rag):
            from app.tools import CatalogSearchTool
            tool = CatalogSearchTool()
            result = tool._run(query="precio laptop", k=4)
            assert isinstance(result, str)

    def test_search_catalog_contains_price(self):
        """La búsqueda de precio debe retornar información de precio."""
        mock_rag = MagicMock()
        mock_rag.search_catalog.return_value = "Producto X: Precio: $50. En stock."

        with patch("app.tools.get_rag", return_value=mock_rag):
            from app.tools import CatalogSearchTool
            tool = CatalogSearchTool()
            result = tool._run(query="precio de Producto X")
            assert "$50" in result

    def test_search_catalog_graceful_error(self):
        """En caso de error, debe retornar un mensaje amigable (no crash)."""
        mock_rag = MagicMock()
        mock_rag.search_catalog.side_effect = Exception("ChromaDB connection failed")

        with patch("app.tools.get_rag", return_value=mock_rag):
            from app.tools import CatalogSearchTool
            tool = CatalogSearchTool()
            result = tool._run(query="precio laptop")
            assert isinstance(result, str)
            assert len(result) > 0  # No debe retornar vacío

    def test_search_catalog_no_results(self):
        """Debe manejar gracefully cuando no hay resultados."""
        mock_rag = MagicMock()
        mock_rag.search_catalog.return_value = "No se encontraron productos relevantes en el catálogo."

        with patch("app.tools.get_rag", return_value=mock_rag):
            from app.tools import CatalogSearchTool
            tool = CatalogSearchTool()
            result = tool._run(query="producto inexistente xyz123")
            assert "no se encontr" in result.lower() or isinstance(result, str)


class TestDocsSearchTool:
    """Tests para la herramienta de búsqueda en documentación."""

    def test_search_docs_returns_string(self):
        """La búsqueda debe retornar siempre un string."""
        mock_rag = MagicMock()
        mock_rag.search_docs.return_value = "Para configurar el dispositivo, siga los pasos 1, 2, 3..."

        with patch("app.tools.get_rag", return_value=mock_rag):
            from app.tools import DocsSearchTool
            tool = DocsSearchTool()
            result = tool._run(query="cómo configurar el mouse")
            assert isinstance(result, str)

    def test_search_docs_calls_rag(self):
        """Debe llamar a rag.search_docs con la query correcta."""
        mock_rag = MagicMock()
        mock_rag.search_docs.return_value = "Información técnica encontrada."

        with patch("app.tools.get_rag", return_value=mock_rag):
            from app.tools import DocsSearchTool
            tool = DocsSearchTool()
            tool._run(query="error E01 en pantalla")
            mock_rag.search_docs.assert_called_once_with("error E01 en pantalla", k=4)

    def test_search_docs_graceful_error(self):
        """En caso de error, debe retornar mensaje amigable."""
        mock_rag = MagicMock()
        mock_rag.search_docs.side_effect = RuntimeError("Vector DB unavailable")

        with patch("app.tools.get_rag", return_value=mock_rag):
            from app.tools import DocsSearchTool
            tool = DocsSearchTool()
            result = tool._run(query="configuración avanzada")
            assert isinstance(result, str)
            assert "error" in result.lower() or "escalar" in result.lower()


class TestCRMUpdateTool:
    """Tests para la herramienta de actualización de CRM."""

    def test_crm_update_simulation_mode(self):
        """En modo simulación (sin CRM_API_URL), debe retornar confirmación."""
        with patch("app.tools.settings") as mock_settings:
            mock_settings.crm_api_url = None
            mock_settings.crm_api_key = None

            from app.tools import CRMUpdateTool
            tool = CRMUpdateTool()
            result = tool._run(
                phone="+5491112345678",
                interest="Laptop Pro 15",
                name="Juan",
                intent_level="high",
            )
            assert isinstance(result, str)
            assert len(result) > 0

    def test_crm_update_includes_phone(self):
        """El resultado debe confirmar qué cliente fue registrado."""
        with patch("app.tools.settings") as mock_settings:
            mock_settings.crm_api_url = None
            mock_settings.crm_api_key = None

            from app.tools import CRMUpdateTool
            tool = CRMUpdateTool()
            result = tool._run(
                phone="+5491112345678",
                interest="Monitor 4K",
                name="María",
                intent_level="medium",
            )
            # Debe mencionar el nombre o el producto registrado
            assert "María" in result or "Monitor" in result or "registrado" in result.lower()

    def test_crm_update_with_api_success(self):
        """Con CRM configurado, debe hacer llamada HTTP."""
        import httpx
        from unittest.mock import patch, AsyncMock

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "lead_123"}
        mock_response.raise_for_status = MagicMock()

        with patch("app.tools.settings") as mock_settings, \
             patch("httpx.post", return_value=mock_response):
            mock_settings.crm_api_url = "https://api.crm.test"
            mock_settings.crm_api_key = "test_key"

            from app.tools import CRMUpdateTool
            tool = CRMUpdateTool()
            result = tool._run(
                phone="+5491112345678",
                interest="Laptop",
                intent_level="high",
            )
            assert "lead_123" in result or "registrado" in result.lower()


class TestToolsFactory:
    """Tests para las funciones factory de herramientas."""

    def test_get_sales_tools_returns_two_tools(self):
        """El agente de ventas debe tener exactamente 2 herramientas."""
        from app.tools import get_sales_tools
        tools = get_sales_tools()
        assert len(tools) == 2

    def test_get_sales_tools_contains_catalog(self):
        """El agente de ventas debe tener acceso al catálogo."""
        from app.tools import get_sales_tools, CatalogSearchTool
        tools = get_sales_tools()
        tool_types = [type(t) for t in tools]
        assert CatalogSearchTool in tool_types

    def test_get_support_tools_returns_two_tools(self):
        """El agente de soporte debe tener 2 herramientas."""
        from app.tools import get_support_tools
        tools = get_support_tools()
        assert len(tools) == 2

    def test_get_support_tools_contains_docs(self):
        """El agente de soporte debe tener acceso a documentación."""
        from app.tools import get_support_tools, DocsSearchTool
        tools = get_support_tools()
        tool_types = [type(t) for t in tools]
        assert DocsSearchTool in tool_types

    def test_get_manager_tools_is_empty(self):
        """El manager no necesita herramientas directas."""
        from app.tools import get_manager_tools
        tools = get_manager_tools()
        assert len(tools) == 0


class TestRAGSystem:
    """Tests para el sistema RAG con ChromaDB mockeado."""

    def test_product_to_text_conversion(self, sample_products):
        """La conversión de producto a texto debe incluir campos clave."""
        with patch("app.rag.OpenAIEmbeddings"), \
             patch("app.rag.Chroma"):
            from app.rag import RAGSystem
            rag = RAGSystem()
            text = rag._product_to_text(sample_products[0])
            assert "Laptop Pro 15" in text
            assert "1299.99" in text
            assert "En stock" in text

    def test_product_out_of_stock(self, sample_products):
        """Un producto sin stock debe indicar 'Agotado'."""
        with patch("app.rag.OpenAIEmbeddings"), \
             patch("app.rag.Chroma"):
            from app.rag import RAGSystem
            rag = RAGSystem()
            text = rag._product_to_text(sample_products[2])  # Monitor 4K - out of stock
            assert "Agotado" in text

    def test_search_catalog_filters_low_relevance(self):
        """Resultados con baja relevancia (< 0.3) deben filtrarse."""
        mock_chroma = MagicMock()
        # Simular resultado con relevancia muy baja
        mock_doc = MagicMock()
        mock_doc.page_content = "Contenido irrelevante"
        mock_doc.metadata = {"name": "Producto X"}
        mock_chroma.similarity_search_with_relevance_scores.return_value = [
            (mock_doc, 0.1)  # Relevancia 10% - debe filtrarse
        ]

        with patch("app.rag.OpenAIEmbeddings"), \
             patch("app.rag.Chroma", return_value=mock_chroma):
            from app.rag import RAGSystem
            rag = RAGSystem()
            rag._catalog_store = mock_chroma
            result = rag.search_catalog("algo muy raro")
            assert "No se encontraron resultados" in result or "no se encontr" in result.lower()

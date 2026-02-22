"""
Tests de integración para los endpoints del webhook FastAPI.
Verifica: routing, parsing de payloads, verificación de tokens, encolado.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key-for-testing")
os.environ.setdefault("WHATSAPP_PROVIDER", "twilio")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACtest123")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test_auth_token")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "whatsapp:+14155238886")
os.environ.setdefault("WEBHOOK_VERIFY_TOKEN", "test_verify_token")
os.environ.setdefault("VECTOR_DB_PATH", "/tmp/test_chroma")


@pytest.fixture
def client():
    """Cliente de test con mocks para servicios externos."""
    with patch("app.main.get_rag") as mock_rag, \
         patch("app.queue_handler.redis.from_url") as mock_redis:

        mock_rag.return_value.collection_stats.return_value = {"catalog": 0, "support_docs": 0}

        from fastapi.testclient import TestClient
        from app.main import app
        yield TestClient(app, raise_server_exceptions=False)


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_version(self, client):
        response = client.get("/health")
        data = response.json()
        assert "version" in data


class TestWebhookVerification:
    """Tests para la verificación del webhook (GET /webhook)."""

    def test_webhook_verification_valid_token(self, client):
        """Con token correcto debe retornar el challenge."""
        response = client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "challenge_string_123",
                "hub.verify_token": "test_verify_token",
            },
        )
        assert response.status_code == 200
        assert response.text == "challenge_string_123"

    def test_webhook_verification_invalid_token(self, client):
        """Con token incorrecto debe retornar 403."""
        response = client.get(
            "/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "challenge_123",
                "hub.verify_token": "token_incorrecto",
            },
        )
        assert response.status_code == 403

    def test_webhook_verification_missing_params(self, client):
        """Sin parámetros debe retornar 403."""
        response = client.get("/webhook")
        assert response.status_code == 403


class TestWebhookReceiveTwilio:
    """Tests para recepción de mensajes de Twilio."""

    def test_twilio_message_enqueued(self, client, twilio_webhook_payload):
        """Un mensaje válido de Twilio debe ser encolado correctamente."""
        with patch("app.main.get_whatsapp_provider") as mock_provider, \
             patch("app.main.enqueue_message", return_value="job_123") as mock_enqueue:

            mock_provider.return_value.parse_incoming.return_value = {
                "from": "+5491112345678",
                "body": "¿Cuánto cuesta la Laptop Pro 15?",
                "message_id": "SMtest123",
                "timestamp": "2024-01-15",
                "profile_name": "Juan",
            }

            response = client.post(
                "/webhook",
                data=twilio_webhook_payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "queued"
            assert data["job_id"] == "job_123"
            mock_enqueue.assert_called_once()

    def test_empty_message_ignored(self, client):
        """Un mensaje vacío debe ser ignorado sin encolar."""
        with patch("app.main.get_whatsapp_provider") as mock_provider, \
             patch("app.main.enqueue_message") as mock_enqueue:

            mock_provider.return_value.parse_incoming.return_value = {
                "from": "+5491112345678",
                "body": "",
                "message_id": "SMtest",
                "timestamp": "",
            }

            response = client.post(
                "/webhook",
                json={"empty": "payload"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ignored"
            mock_enqueue.assert_not_called()

    def test_reset_command_clears_conversation(self, client):
        """El comando 'cancelar' debe limpiar el historial y NO encolar."""
        with patch("app.main.get_whatsapp_provider") as mock_provider, \
             patch("app.main.enqueue_message") as mock_enqueue, \
             patch("app.main.clear_conversation") as mock_clear:

            mock_provider.return_value.parse_incoming.return_value = {
                "from": "+5491112345678",
                "body": "cancelar",
                "message_id": "SMtest",
                "timestamp": "",
            }
            mock_provider.return_value.send_message = AsyncMock(
                return_value={"status": "sent"}
            )

            response = client.post("/webhook", json={})

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "reset"
            mock_enqueue.assert_not_called()
            mock_clear.assert_called_once_with("+5491112345678")


class TestWebhookReceiveEvolution:
    """Tests para recepción de mensajes de Evolution API."""

    def test_evolution_message_parsed_correctly(self, evolution_webhook_payload):
        """El payload de Evolution debe parsearse correctamente."""
        # Parchamos settings en app.whatsapp (el singleton ya está creado)
        with patch("app.whatsapp.settings") as mock_settings:
            mock_settings.evolution_api_url = "http://localhost:8080"
            mock_settings.evolution_api_key = "test_key"
            mock_settings.evolution_instance = "test_instance"

            from app.whatsapp import EvolutionAPIProvider
            provider = EvolutionAPIProvider()
            parsed = provider.parse_incoming(evolution_webhook_payload)

            assert parsed["from"] == "+5491112345678"
            assert "mouse" in parsed["body"].lower()
            assert parsed["message_id"] == "evo_msg_123"
            assert parsed["profile_name"] == "María López"


class TestTwilioPayloadParsing:
    """Tests de parsing del proveedor Twilio."""

    def test_twilio_parses_phone_correctly(self):
        """Twilio debe extraer el número sin el prefijo 'whatsapp:'."""
        from app.whatsapp import TwilioProvider
        provider = TwilioProvider()

        payload = {
            "From": "whatsapp:+5491112345678",
            "Body": "Hola",
            "MessageSid": "SM123",
            "ProfileName": "Test User",
        }
        parsed = provider.parse_incoming(payload)
        assert parsed["from"] == "+5491112345678"
        assert "whatsapp:" not in parsed["from"]

    def test_twilio_parses_body_correctly(self):
        """Twilio debe extraer el cuerpo del mensaje."""
        from app.whatsapp import TwilioProvider
        provider = TwilioProvider()

        payload = {
            "From": "whatsapp:+5491112345678",
            "Body": "  ¿Cuánto cuesta?  ",
            "MessageSid": "SM123",
        }
        parsed = provider.parse_incoming(payload)
        assert parsed["body"] == "¿Cuánto cuesta?"  # Strip aplicado


class TestAdminEndpoints:
    """Tests para endpoints de administración."""

    def test_stats_endpoint(self, client):
        """El endpoint de stats debe retornar información del sistema."""
        with patch("app.main.get_queue_stats", return_value={"queued": 0}), \
             patch("app.main.get_rag") as mock_rag:
            mock_rag.return_value.collection_stats.return_value = {"catalog": 5, "support_docs": 3}

            response = client.get("/admin/stats")
            assert response.status_code == 200
            data = response.json()
            assert "queue" in data
            assert "config" in data

    def test_ingest_catalog_invalid_type(self, client):
        """Un tipo de ingesta inválido debe retornar 400."""
        response = client.post(
            "/admin/ingest",
            json={"type": "invalid_type"},
        )
        assert response.status_code == 400

    def test_ingest_catalog_missing_data(self, client):
        """Una ingesta de catálogo sin datos debe retornar 400."""
        response = client.post(
            "/admin/ingest",
            json={"type": "catalog", "data": None},
        )
        assert response.status_code == 400


class TestWorkerRouting:
    """Tests para el routing de mensajes en el worker."""

    def test_quick_route_sales_keyword(self):
        """Mensajes con keywords de ventas deben enrutarse a VENTAS."""
        from app.worker import _quick_route
        assert _quick_route("¿cuánto cuesta el producto?") == "VENTAS"
        assert _quick_route("¿está disponible en stock?") == "VENTAS"
        assert _quick_route("quiero comprar la laptop") == "VENTAS"

    def test_quick_route_support_keyword(self):
        """Mensajes con keywords técnicas deben enrutarse a SOPORTE_TECNICO."""
        from app.worker import _quick_route
        assert _quick_route("no funciona mi dispositivo") == "SOPORTE_TECNICO"
        assert _quick_route("hay un error en la pantalla") == "SOPORTE_TECNICO"
        assert _quick_route("cómo configuro el router") == "SOPORTE_TECNICO"

    def test_quick_route_ambiguous_returns_unknown(self):
        """Mensajes ambiguos deben retornar UNKNOWN para routing por LLM."""
        from app.worker import _quick_route
        assert _quick_route("hola") == "UNKNOWN"
        assert _quick_route("gracias") == "UNKNOWN"

    def test_extract_final_response_approved(self):
        """Debe extraer respuesta de output 'APROBADO: ...'."""
        from app.worker import _extract_final_response
        qa_output = "APROBADO: Hola, el precio del producto es $50."
        result = _extract_final_response(qa_output)
        assert result == "Hola, el precio del producto es $50."

    def test_extract_final_response_rejected_with_correction(self):
        """Debe extraer corrección de output 'RECHAZADO: ... CORRECCIÓN: ...'."""
        from app.worker import _extract_final_response
        qa_output = "RECHAZADO: Menciona precio no verificado. CORRECCIÓN: Por favor, consulta nuestro catálogo para el precio exacto."
        result = _extract_final_response(qa_output)
        assert "catálogo" in result or "precio" in result

    def test_extract_final_response_fallback(self):
        """Sin formato estándar, debe retornar el output completo."""
        from app.worker import _extract_final_response
        raw = "Esta es una respuesta sin formato estándar del QA."
        result = _extract_final_response(raw)
        assert result == raw.strip()

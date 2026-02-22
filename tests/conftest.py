"""
Fixtures compartidas para todos los tests.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import os


# Configurar variables de entorno ANTES de importar la app
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake-key-for-testing")
os.environ.setdefault("WHATSAPP_PROVIDER", "twilio")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "ACtest123")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test_auth_token")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "whatsapp:+14155238886")
os.environ.setdefault("WEBHOOK_VERIFY_TOKEN", "test_verify_token")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")  # DB 1 para tests
os.environ.setdefault("VECTOR_DB_PATH", "/tmp/test_chroma_db")


@pytest.fixture(scope="session")
def sample_products() -> list[dict]:
    """Catálogo de productos de prueba."""
    return [
        {
            "id": "P001",
            "name": "Laptop Pro 15",
            "description": "Laptop de alto rendimiento para profesionales. Intel Core i7, 16GB RAM, 512GB SSD.",
            "price": 1299.99,
            "category": "Computadoras",
            "features": ["Intel Core i7", "16GB RAM", "512GB SSD", "Pantalla 4K"],
            "in_stock": True,
            "shipping": "Envío gratis en 2-3 días hábiles",
        },
        {
            "id": "P002",
            "name": "Mouse Inalámbrico Ergonómico",
            "description": "Mouse ergonómico con diseño vertical para reducir fatiga. Conexión USB-C.",
            "price": 49.99,
            "category": "Periféricos",
            "features": ["Inalámbrico", "Ergonómico", "USB-C", "Batería 6 meses"],
            "in_stock": True,
            "shipping": "Envío estándar gratis",
        },
        {
            "id": "P003",
            "name": "Monitor 4K 27 pulgadas",
            "description": "Monitor UHD 4K para diseño y productividad. Panel IPS, HDR400.",
            "price": 599.99,
            "category": "Monitores",
            "features": ["4K UHD", "Panel IPS", "HDR400", "27 pulgadas"],
            "in_stock": False,
            "shipping": "Disponible en 2 semanas",
        },
    ]


@pytest.fixture(scope="session")
def app_client():
    """Cliente de test para FastAPI (sin Redis/ChromaDB reales)."""
    with patch("app.main.get_rag") as mock_rag, \
         patch("app.main.get_queue_stats") as mock_stats:
        mock_rag.return_value.collection_stats.return_value = {"catalog": 10, "support_docs": 5}
        mock_stats.return_value = {"queued": 0, "started": 0, "finished": 0, "failed": 0}

        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)
        yield client


@pytest.fixture
def twilio_webhook_payload() -> dict:
    """Payload típico de Twilio WhatsApp."""
    return {
        "MessageSid": "SMtest123456789",
        "From": "whatsapp:+5491112345678",
        "To": "whatsapp:+14155238886",
        "Body": "¿Cuánto cuesta la Laptop Pro 15?",
        "ProfileName": "Juan García",
        "DateSent": "2024-01-15T10:30:00Z",
    }


@pytest.fixture
def evolution_webhook_payload() -> dict:
    """Payload típico de Evolution API."""
    return {
        "event": "messages.upsert",
        "instance": "my_instance",
        "data": {
            "key": {
                "remoteJid": "5491112345678@s.whatsapp.net",
                "fromMe": False,
                "id": "evo_msg_123",
            },
            "message": {
                "conversation": "¿Cómo configuro el mouse inalámbrico?",
            },
            "messageTimestamp": 1705316200,
            "pushName": "María López",
        },
    }

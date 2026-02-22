"""
Abstracción del proveedor de WhatsApp.

Soporta:
  - Twilio WhatsApp Sandbox / Business API
  - Evolution API (solución self-hosted open-source)

Uso:
    provider = get_whatsapp_provider()
    await provider.send_message(to="+5491112345678", body="Hola!")
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Interfaz base                                                       #
# ------------------------------------------------------------------ #

class WhatsAppProvider(ABC):
    """Interfaz común para todos los proveedores de WhatsApp."""

    @abstractmethod
    async def send_message(self, to: str, body: str) -> dict[str, Any]:
        """
        Envía un mensaje de texto por WhatsApp.

        Args:
            to:   Número destino en formato E.164 (+5491112345678).
            body: Texto del mensaje.

        Returns:
            Dict con el resultado del proveedor (message_id, status, etc.).
        """
        ...

    @abstractmethod
    def parse_incoming(self, payload: dict[str, Any]) -> dict[str, str]:
        """
        Extrae datos estandarizados del payload entrante del webhook.

        Returns:
            Dict con: from, body, message_id, timestamp
        """
        ...


# ------------------------------------------------------------------ #
# Twilio WhatsApp                                                     #
# ------------------------------------------------------------------ #

class TwilioProvider(WhatsAppProvider):
    """
    Proveedor Twilio para WhatsApp Business.
    Documentación: https://www.twilio.com/docs/whatsapp
    """

    BASE_URL = "https://api.twilio.com/2010-04-01"

    def __init__(self) -> None:
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            raise ValueError(
                "Twilio requiere TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN en .env"
            )
        self._account_sid = settings.twilio_account_sid
        self._auth = (settings.twilio_account_sid, settings.twilio_auth_token)
        self._from_number = settings.twilio_phone_number or ""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def send_message(self, to: str, body: str) -> dict[str, Any]:
        # Twilio requiere formato whatsapp:+NUMERO
        to_formatted = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to

        url = f"{self.BASE_URL}/Accounts/{self._account_sid}/Messages.json"
        payload = {
            "From": self._from_number,
            "To": to_formatted,
            "Body": body,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, data=payload, auth=self._auth, timeout=10.0
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"[Twilio] Mensaje enviado a {to} — SID: {result.get('sid')}")
        return {"message_id": result.get("sid"), "status": result.get("status"), "provider": "twilio"}

    def parse_incoming(self, payload: dict[str, Any]) -> dict[str, str]:
        """Parsea el webhook de Twilio (application/x-www-form-urlencoded)."""
        raw_from = payload.get("From", "")
        # Twilio envía "whatsapp:+5491112345678"
        phone = raw_from.replace("whatsapp:", "").strip()
        return {
            "from": phone,
            "body": payload.get("Body", "").strip(),
            "message_id": payload.get("MessageSid", ""),
            "timestamp": payload.get("DateSent", ""),
            "profile_name": payload.get("ProfileName", ""),
        }


# ------------------------------------------------------------------ #
# Evolution API                                                       #
# ------------------------------------------------------------------ #

class EvolutionAPIProvider(WhatsAppProvider):
    """
    Proveedor Evolution API (self-hosted, open source).
    Repositorio: https://github.com/EvolutionAPI/evolution-api
    """

    def __init__(self) -> None:
        if not settings.evolution_api_url or not settings.evolution_instance:
            raise ValueError(
                "Evolution API requiere EVOLUTION_API_URL y EVOLUTION_INSTANCE en .env"
            )
        self._base_url = settings.evolution_api_url.rstrip("/")
        self._instance = settings.evolution_instance
        self._api_key = settings.evolution_api_key or ""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def send_message(self, to: str, body: str) -> dict[str, Any]:
        # Evolution API espera número sin + y con código de país
        phone = to.replace("+", "").replace(" ", "").replace("-", "")

        url = f"{self._base_url}/message/sendText/{self._instance}"
        payload = {
            "number": phone,
            "text": body,
        }
        headers = {"apikey": self._api_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            response.raise_for_status()
            result = response.json()

        logger.info(f"[Evolution] Mensaje enviado a {to}")
        return {
            "message_id": result.get("key", {}).get("id", ""),
            "status": "sent",
            "provider": "evolution",
        }

    def parse_incoming(self, payload: dict[str, Any]) -> dict[str, str]:
        """Parsea el webhook de Evolution API."""
        data = payload.get("data", {})
        key = data.get("key", {})
        message = data.get("message", {})

        # Extraer número del remitente
        remote_jid = key.get("remoteJid", "")
        phone = remote_jid.replace("@s.whatsapp.net", "").replace("@g.us", "")

        # Texto del mensaje (puede ser conversation, extendedTextMessage, etc.)
        body = (
            message.get("conversation")
            or message.get("extendedTextMessage", {}).get("text")
            or ""
        ).strip()

        return {
            "from": f"+{phone}",
            "body": body,
            "message_id": key.get("id", ""),
            "timestamp": str(data.get("messageTimestamp", "")),
            "profile_name": data.get("pushName", ""),
        }


# ------------------------------------------------------------------ #
# Factory                                                             #
# ------------------------------------------------------------------ #

_provider_instance: WhatsAppProvider | None = None


def get_whatsapp_provider() -> WhatsAppProvider:
    """
    Retorna la instancia del proveedor configurado en .env.
    Singleton para reutilizar la misma instancia en toda la app.
    """
    global _provider_instance
    if _provider_instance is None:
        provider_name = settings.whatsapp_provider.lower()
        if provider_name == "twilio":
            _provider_instance = TwilioProvider()
        elif provider_name == "evolution":
            _provider_instance = EvolutionAPIProvider()
        else:
            raise ValueError(
                f"Proveedor desconocido: '{provider_name}'. "
                "Opciones válidas: 'twilio', 'evolution'"
            )
        logger.info(f"[WhatsApp] Proveedor inicializado: {provider_name}")
    return _provider_instance

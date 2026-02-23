"""
Proveedor de Telegram para la Agentic Sales Suite.

Soporta:
- Recepción de mensajes via webhook (Bot API)
- Envío de respuestas via Bot API
- Manejo de comandos (/start, /reset, /help)

Documentación: https://core.telegram.org/bots/api
"""
import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


# ------------------------------------------------------------------ #
# Proveedor Telegram
# ------------------------------------------------------------------ #

class TelegramProvider:
    """
    Proveedor de mensajería Telegram usando la Bot API oficial.
    Recibe mensajes via webhook y envía respuestas con sendMessage.
    """

    def __init__(self) -> None:
        if not settings.telegram_bot_token:
            raise ValueError(
                "Telegram requiere TELEGRAM_BOT_TOKEN en variables de entorno"
            )
        self._token = settings.telegram_bot_token
        self._base_url = f"{TELEGRAM_API}/bot{self._token}"

    # ------------------------------------------------------------------ #
    # Envío
    # ------------------------------------------------------------------ #

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def send_message(self, chat_id: int | str, text: str) -> dict[str, Any]:
        """
        Envía un mensaje de texto a un chat de Telegram.

        Args:
            chat_id: ID del chat / usuario destino.
            text:    Texto del mensaje (soporta Markdown).

        Returns:
            Dict con el resultado de la API de Telegram.
        """
        url = f"{self._base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            result = response.json()

        if not result.get("ok"):
            raise RuntimeError(f"Telegram API error: {result.get('description')}")

        msg_id = result.get("result", {}).get("message_id")
        logger.info(f"[Telegram] Mensaje enviado — chat_id={chat_id}, msg_id={msg_id}")
        return {
            "message_id": msg_id,
            "status": "sent",
            "provider": "telegram",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def send_action(self, chat_id: int | str, action: str = "typing") -> None:
        """Envía una acción de chat (ej: 'typing') para indicar que el bot está procesando."""
        url = f"{self._base_url}/sendChatAction"
        async with httpx.AsyncClient() as client:
            await client.post(url, json={"chat_id": chat_id, "action": action}, timeout=5.0)

    # ------------------------------------------------------------------ #
    # Parseo de webhook
    # ------------------------------------------------------------------ #

    def parse_incoming(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Extrae datos estandarizados del payload del webhook de Telegram.

        El payload sigue la estructura del objeto Update de Telegram:
        https://core.telegram.org/bots/api#update

        Returns:
            Dict con: from, from_id, body, message_id, timestamp,
                      profile_name, is_command, command
        """
        # Telegram envía updates: puede ser message, edited_message, etc.
        message = (
            payload.get("message")
            or payload.get("edited_message")
            or payload.get("channel_post")
        )

        if not message:
            return {
                "from": "",
                "from_id": "",
                "body": "",
                "message_id": "",
                "timestamp": "",
                "profile_name": "",
                "is_command": False,
                "command": None,
                "provider": "telegram",
            }

        # Extraer datos del remitente
        sender = message.get("from", {}) or message.get("sender_chat", {})
        chat = message.get("chat", {})

        chat_id = str(chat.get("id", ""))
        user_id = str(sender.get("id", "") or chat_id)
        first_name = sender.get("first_name", "")
        last_name = sender.get("last_name", "")
        username = sender.get("username", "")
        profile_name = f"{first_name} {last_name}".strip() or username or "Usuario"

        # Texto del mensaje
        text = (message.get("text") or message.get("caption") or "").strip()

        # Detectar comandos (/start, /reset, /help)
        is_command = text.startswith("/")
        command = text.split()[0].lstrip("/").lower() if is_command else None

        return {
            "from": chat_id,           # usamos chat_id como identificador (equivalente al phone en WA)
            "from_id": user_id,
            "body": text,
            "message_id": str(message.get("message_id", "")),
            "timestamp": str(message.get("date", "")),
            "profile_name": profile_name,
            "username": username,
            "is_command": is_command,
            "command": command,
            "provider": "telegram",
        }

    # ------------------------------------------------------------------ #
    # Webhook management
    # ------------------------------------------------------------------ #

    async def get_webhook_info(self) -> dict[str, Any]:
        """Consulta el estado actual del webhook registrado."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._base_url}/getWebhookInfo", timeout=10.0)
            return resp.json()

    async def set_webhook(self, url: str) -> dict[str, Any]:
        """Registra o actualiza el webhook URL del bot."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/setWebhook",
                json={"url": url, "allowed_updates": ["message", "edited_message"]},
                timeout=10.0,
            )
            return resp.json()


# ------------------------------------------------------------------ #
# Singleton
# ------------------------------------------------------------------ #

_telegram_instance: TelegramProvider | None = None


def get_telegram_provider() -> TelegramProvider:
    """Retorna la instancia singleton del proveedor Telegram."""
    global _telegram_instance
    if _telegram_instance is None:
        _telegram_instance = TelegramProvider()
        logger.info("[Telegram] Proveedor inicializado")
    return _telegram_instance
—

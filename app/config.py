from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    openai_api_key: str = Field(..., description="OpenAI API Key")
    openai_model: str = Field("gpt-4o", description="Modelo LLM principal")
    openai_embedding_model: str = Field("text-embedding-3-small", description="Modelo de embeddings")

    # WhatsApp Provider
    whatsapp_provider: Literal["twilio", "evolution"] = Field("twilio")

    # Twilio
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None  # formato: whatsapp:+14155238886

    # Evolution API
    evolution_api_url: Optional[str] = None
    evolution_api_key: Optional[str] = None
    evolution_instance: Optional[str] = None

    # Webhook
    webhook_verify_token: str = Field("changeme", description="Token de verificación del webhook")

    # Vector DB
    vector_db_path: str = Field("./chroma_db")
    vector_db_collection_catalog: str = Field("product_catalog")
    vector_db_collection_docs: str = Field("support_docs")

    # Redis
    redis_url: str = Field("redis://localhost:6379/0")
    redis_queue_name: str = Field("whatsapp_messages")

    # CRM (opcional)
    crm_api_url: Optional[str] = None
    crm_api_key: Optional[str] = None

    # App
    app_env: str = Field("development")
    log_level: str = Field("INFO")
    max_queue_workers: int = Field(4)


# Singleton global
settings = Settings()

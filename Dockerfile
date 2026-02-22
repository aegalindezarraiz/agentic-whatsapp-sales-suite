# ============================================================
# Agentic Sales Suite - Dockerfile
# Base: Python 3.11-slim (imagen oficial, mínima, estable)
# ============================================================

FROM python:3.11-slim

# Metadatos
LABEL maintainer="Agentic Sales Suite"
LABEL description="Agentic WhatsApp Sales Suite - FastAPI + CrewAI"

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Directorio de trabajo
WORKDIR /app

# Dependencias del sistema (mínimas para compilar paquetes con C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias Python primero (aprovechar caché de capas Docker)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar código de la aplicación
COPY app/ ./app/

# Crear directorios necesarios
RUN mkdir -p /app/chroma_db /app/data

# Usuario no-root (seguridad)
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Puerto expuesto (Railway inyecta $PORT en runtime; 8000 es solo documentación)
EXPOSE 8000

# Health check deshabilitado aquí — Railway gestiona el suyo propio via $PORT
# (Docker HEALTHCHECK con puerto hardcodeado conflictuaba con $PORT de Railway)

# Comando por defecto: Railway lo sobreescribe con startCommand de railway.toml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

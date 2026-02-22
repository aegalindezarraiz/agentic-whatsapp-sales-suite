# ============================================================
# Dockerfile Frontend — Next.js 14 (standalone output)
# Multi-stage build: deps → builder → runner
# ============================================================

# Stage 1: Instalar dependencias
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Stage 2: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_API_URL se pasa como build arg desde Railway (env var a build-time)
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# Stage 3: Runner mínimo (standalone = no necesita node_modules completo)
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copiar output standalone + assets estáticos
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# Railway inyecta $PORT en runtime; Next.js standalone lo respeta automáticamente
EXPOSE 3000
ENV PORT=3000

CMD ["node", "server.js"]

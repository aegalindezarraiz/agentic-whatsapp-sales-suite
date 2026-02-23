'use client'

import { useEffect, useState, useCallback } from 'react'
import { fetchHealth, fetchStats, API_URL, type HealthResponse, type StatsResponse } from '@/lib/api'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }
  return (
    <button
      onClick={copy}
      className="ml-2 text-xs px-2 py-0.5 rounded border border-gray-700 text-gray-500 hover:text-gray-300 hover:border-gray-600 transition-colors"
    >
      {copied ? '✓ Copiado' : 'Copiar'}
    </button>
  )
}

function ConfigRow({ label, value }: { label: string; value?: string }) {
  if (!value) return null
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-800/50 last:border-0">
      <span className="text-xs text-gray-500">{label}</span>
      <div className="flex items-center gap-1">
        <code className="text-xs font-mono text-gray-300">{value}</code>
        <CopyButton text={value} />
      </div>
    </div>
  )
}

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block w-1.5 h-1.5 rounded-full mr-1.5 ${ok ? 'bg-green-400' : 'bg-red-400'}`}
    />
  )
}

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [h, s] = await Promise.all([fetchHealth(), fetchStats()])
      setHealth(h); setStats(s)
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const apiOk = health?.status === 'ok'
  const redisOk = !stats?.queue.error
  const ragOk = !stats?.rag.error

  const webhookUrl = `${API_URL}/webhook/whatsapp`

  return (
    <div className="max-w-2xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-white">Configuración</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Estado del sistema, variables de entorno y URL del webhook.
        </p>
      </div>

      {/* Webhook URL */}
      <section className="mb-6">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Webhook WhatsApp
        </h2>
        <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
          <p className="text-xs text-gray-500 mb-2">
            Registra esta URL en tu proveedor de WhatsApp (Meta, Twilio, etc.):
          </p>
          <div className="flex items-center gap-2 p-3 rounded-lg bg-gray-950 border border-gray-700">
            <code className="text-xs font-mono text-green-400 flex-1 truncate">{webhookUrl}</code>
            <CopyButton text={webhookUrl} />
          </div>
        </div>
      </section>

      {/* System status */}
      <section className="mb-6">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Estado del sistema
        </h2>
        {loading ? (
          <div className="text-xs text-gray-600 py-4">Cargando…</div>
        ) : (
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">
                <StatusDot ok={apiOk} />API Backend
              </span>
              <span className={apiOk ? 'text-green-400' : 'text-red-400'}>
                {apiOk ? 'Online' : 'Offline'}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">
                <StatusDot ok={redisOk} />Redis / Queue
              </span>
              <span className={redisOk ? 'text-green-400' : 'text-red-400'}>
                {redisOk ? 'Conectado' : stats?.queue.error ?? 'Error'}
              </span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">
                <StatusDot ok={ragOk} />ChromaDB (RAG)
              </span>
              <span className={ragOk ? 'text-green-400' : 'text-red-400'}>
                {ragOk ? 'Operativo' : stats?.rag.error ?? 'Error'}
              </span>
            </div>
          </div>
        )}
      </section>

      {/* Config vars */}
      <section className="mb-6">
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Variables de entorno activas
        </h2>
        <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
          <ConfigRow label="API URL" value={API_URL} />
          <ConfigRow label="Entorno" value={health?.env} />
          <ConfigRow label="Versión" value={health?.version} />
          <ConfigRow label="Proveedor WhatsApp" value={stats?.config.whatsapp_provider} />
          <ConfigRow label="Modelo LLM" value={stats?.config.llm_model} />
        </div>
      </section>

      {/* RAG stats */}
      <section>
        <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          Índices RAG
        </h2>
        <div className="grid grid-cols-2 gap-3">
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
            <p className="text-xs text-gray-500 mb-1">Catálogo de productos</p>
            <p className="text-2xl font-bold text-white tabular-nums">{stats?.rag.catalog ?? 0}</p>
            <p className="text-xs text-gray-600 mt-0.5">chunks indexados</p>
          </div>
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
            <p className="text-xs text-gray-500 mb-1">Documentos de soporte</p>
            <p className="text-2xl font-bold text-white tabular-nums">{stats?.rag.support_docs ?? 0}</p>
            <p className="text-xs text-gray-600 mt-0.5">chunks indexados</p>
          </div>
        </div>
      </section>

      <div className="mt-6">
        <button
          onClick={load}
          className="text-sm px-4 py-2 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 transition-colors"
        >
          ↻ Recargar estado
        </button>
      </div>
    </div>
  )
}

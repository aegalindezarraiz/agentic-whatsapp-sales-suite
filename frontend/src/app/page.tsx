'use client'

import { useEffect, useState, useCallback } from 'react'
import { fetchHealth, fetchStats, type HealthResponse, type StatsResponse } from '@/lib/api'

// ------------------------------------------------------------------ //
// Sub-components
// ------------------------------------------------------------------ //

function Badge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
        ok
          ? 'bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/30'
          : 'bg-red-500/15 text-red-400 ring-1 ring-red-500/30'
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-emerald-400' : 'bg-red-400'}`} />
      {label}
    </span>
  )
}

function StatCard({
  label,
  value,
  sub,
  accent = false,
  warn = false,
}: {
  label: string
  value: string | number
  sub?: string
  accent?: boolean
  warn?: boolean
}) {
  return (
    <div
      className={`rounded-xl border p-5 ${
        warn
          ? 'border-red-500/30 bg-red-500/5'
          : accent
          ? 'border-blue-500/20 bg-blue-500/5'
          : 'border-gray-800 bg-gray-900/60'
      }`}
    >
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-3xl font-bold tabular-nums ${warn ? 'text-red-400' : 'text-white'}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-gray-500 mt-1 truncate">{sub}</p>}
    </div>
  )
}

function Section({ title }: { title: string }) {
  return (
    <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3 mt-8">
      {title}
    </p>
  )
}

// ------------------------------------------------------------------ //
// Page
// ------------------------------------------------------------------ //

export default function DashboardPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const load = useCallback(async () => {
    try {
      const [h, s] = await Promise.all([fetchHealth(), fetchStats()])
      setHealth(h)
      setStats(s)
      setError(null)
      setLastRefresh(new Date())
    } catch {
      setError('No se pudo conectar al backend. Verifica NEXT_PUBLIC_API_URL.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const t = setInterval(load, 15_000)
    return () => clearInterval(t)
  }, [load])

  const apiOk = health?.status === 'ok'
  const redisOk = !stats?.queue.error
  const ragOk = !stats?.rag.error

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h1 className="text-xl font-semibold text-white">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {lastRefresh
              ? `Actualizado ${lastRefresh.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`
              : 'Cargando…'}
          </p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="text-sm px-3 py-1.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 transition-colors disabled:opacity-40"
        >
          ↻ Refrescar
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mt-4 p-3 rounded-lg border border-red-500/30 bg-red-500/5 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading && !stats ? (
        <div className="mt-12 text-center text-gray-600 text-sm">Conectando al backend…</div>
      ) : (
        <>
          {/* System status badges */}
          <div className="flex flex-wrap gap-2 mt-5 mb-2">
            <Badge ok={apiOk} label={apiOk ? 'API online' : 'API offline'} />
            <Badge ok={redisOk} label={redisOk ? 'Redis conectado' : 'Redis error'} />
            <Badge ok={ragOk} label={ragOk ? 'ChromaDB ok' : 'ChromaDB error'} />
          </div>

          {/* System */}
          <Section title="Sistema" />
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard
              label="API Status"
              value={apiOk ? 'Online' : 'Offline'}
              sub={`versión ${health?.version ?? '—'}`}
              accent={apiOk}
              warn={!apiOk}
            />
            <StatCard
              label="Entorno"
              value={health?.env ?? '—'}
              sub={stats?.config.whatsapp_provider ?? ''}
            />
            <StatCard
              label="Modelo LLM"
              value={stats?.config.llm_model ?? '—'}
            />
            <StatCard
              label="Redis"
              value={redisOk ? 'Online' : 'Error'}
              sub={stats?.queue.error ?? 'conectado'}
              accent={redisOk}
              warn={!redisOk}
            />
          </div>

          {/* Queue */}
          <Section title="Cola de mensajes" />
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <StatCard label="En cola" value={stats?.queue.queued ?? 0} />
            <StatCard label="Procesando" value={stats?.queue.started ?? 0} accent />
            <StatCard label="Completados" value={stats?.queue.finished ?? 0} accent />
            <StatCard
              label="Fallidos"
              value={stats?.queue.failed ?? 0}
              warn={(stats?.queue.failed ?? 0) > 0}
            />
            <StatCard label="Diferidos" value={stats?.queue.deferred ?? 0} />
          </div>

          {/* RAG */}
          <Section title="Base de conocimiento (RAG)" />
          <div className="grid grid-cols-2 gap-3">
            <StatCard
              label="Catálogo de productos"
              value={stats?.rag.catalog ?? 0}
              sub="chunks indexados"
              accent={(stats?.rag.catalog ?? 0) > 0}
            />
            <StatCard
              label="Documentos de soporte"
              value={stats?.rag.support_docs ?? 0}
              sub="chunks indexados"
              accent={(stats?.rag.support_docs ?? 0) > 0}
            />
          </div>

          {/* Quick links */}
          <Section title="Acciones rápidas" />
          <div className="grid grid-cols-2 gap-3">
            <a
              href="/catalog"
              className="flex flex-col gap-1 p-5 rounded-xl border border-gray-800 bg-gray-900/60 hover:border-gray-600 hover:bg-gray-800/60 transition-colors"
            >
              <span className="text-base font-medium text-white">Ingresar productos</span>
              <span className="text-xs text-gray-500">Agrega o actualiza el catálogo en el RAG</span>
            </a>
            <a
              href="/docs"
              className="flex flex-col gap-1 p-5 rounded-xl border border-gray-800 bg-gray-900/60 hover:border-gray-600 hover:bg-gray-800/60 transition-colors"
            >
              <span className="text-base font-medium text-white">Indexar documentos</span>
              <span className="text-xs text-gray-500">Sube PDFs y manuales al RAG de soporte</span>
            </a>
          </div>
        </>
      )}
    </div>
  )
}

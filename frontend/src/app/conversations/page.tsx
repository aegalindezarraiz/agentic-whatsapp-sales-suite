'use client'

import { useEffect, useState, useCallback } from 'react'
import { fetchConversations, type Conversation } from '@/lib/api'

function StatusBadge({ status }: { status: Conversation['status'] }) {
  const map = {
    active:  'bg-green-500/15 text-green-400 ring-green-500/30',
    closed:  'bg-gray-500/15 text-gray-400 ring-gray-500/30',
    pending: 'bg-yellow-500/15 text-yellow-400 ring-yellow-500/30',
  }
  return (
    <span className={`inline-flex text-xs font-medium px-2 py-0.5 rounded-full ring-1 ${map[status]}`}>
      {status}
    </span>
  )
}

export default function ConversationsPage() {
  const [items, setItems] = useState<Conversation[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (p: number) => {
    setLoading(true)
    try {
      const data = await fetchConversations(p, 20)
      setItems(data.items)
      setTotal(data.total)
      setError(null)
    } catch {
      setError('No se pudo cargar. Agrega /admin/conversations al backend.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(page) }, [load, page])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-white">Conversaciones</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} conversaciones totales</p>
        </div>
        <button
          onClick={() => load(page)}
          className="text-sm px-3 py-1.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 transition-colors"
        >
          ↻ Refrescar
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg border border-yellow-500/30 bg-yellow-500/5 text-yellow-400 text-sm">
          ⚠ {error}
        </div>
      )}

      {loading ? (
        <div className="text-center text-gray-600 text-sm py-12">Cargando…</div>
      ) : items.length === 0 ? (
        <div className="text-center text-gray-600 text-sm py-12">Sin conversaciones todavía.</div>
      ) : (
        <div className="rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/60">
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Contacto</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Teléfono</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Estado</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Mensajes</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Última actividad</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className="border-b border-gray-800/50 hover:bg-gray-900/40 transition-colors">
                  <td className="px-4 py-3 text-white">{c.contact_name ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-400 font-mono text-xs">{c.phone}</td>
                  <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                  <td className="px-4 py-3 text-gray-400">{c.messages.length}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(c.updated_at).toLocaleString('es', { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-xs text-gray-500">Página {page} de {Math.ceil(total / 20)}</p>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage(p => p - 1)}
              className="px-3 py-1.5 text-xs rounded-lg border border-gray-700 text-gray-400 hover:text-white disabled:opacity-40"
            >
              ← Anterior
            </button>
            <button
              disabled={page >= Math.ceil(total / 20)}
              onClick={() => setPage(p => p + 1)}
              className="px-3 py-1.5 text-xs rounded-lg border border-gray-700 text-gray-400 hover:text-white disabled:opacity-40"
            >
              Siguiente →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

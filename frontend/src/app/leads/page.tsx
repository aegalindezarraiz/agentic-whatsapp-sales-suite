'use client'

import { useEffect, useState, useCallback } from 'react'
import { fetchLeads, type Lead } from '@/lib/api'

const STAGE_LABELS: Record<Lead['stage'], string> = {
  new:       'Nuevo',
  contacted: 'Contactado',
  qualified: 'Calificado',
  converted: 'Convertido',
  lost:      'Perdido',
}

const STAGE_COLORS: Record<Lead['stage'], string> = {
  new:       'bg-blue-500/15 text-blue-400 ring-blue-500/30',
  contacted: 'bg-yellow-500/15 text-yellow-400 ring-yellow-500/30',
  qualified: 'bg-purple-500/15 text-purple-400 ring-purple-500/30',
  converted: 'bg-green-500/15 text-green-400 ring-green-500/30',
  lost:      'bg-red-500/15 text-red-400 ring-red-500/30',
}

function StageBadge({ stage }: { stage: Lead['stage'] }) {
  return (
    <span className={`inline-flex text-xs font-medium px-2 py-0.5 rounded-full ring-1 ${STAGE_COLORS[stage]}`}>
      {STAGE_LABELS[stage]}
    </span>
  )
}

function exportCSV(leads: Lead[]) {
  const headers = ['ID', 'Teléfono', 'Nombre', 'Email', 'Interés', 'Etapa', 'Creado', 'Notas']
  const rows = leads.map(l => [
    l.id, l.phone, l.contact_name ?? '', l.email ?? '',
    l.interest ?? '', STAGE_LABELS[l.stage],
    new Date(l.created_at).toISOString(), l.notes ?? '',
  ])
  const csv = [headers, ...rows].map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = 'leads.csv'; a.click()
  URL.revokeObjectURL(url)
}

export default function LeadsPage() {
  const [items, setItems] = useState<Lead[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (p: number) => {
    setLoading(true)
    try {
      const data = await fetchLeads(p, 50)
      setItems(data.items)
      setTotal(data.total)
      setError(null)
    } catch {
      setError('No se pudo cargar. Agrega /admin/leads al backend.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(page) }, [load, page])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-white">Leads</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} leads registrados</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => exportCSV(items)}
            disabled={items.length === 0}
            className="text-sm px-3 py-1.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 transition-colors disabled:opacity-40"
          >
            ↓ Exportar CSV
          </button>
          <button
            onClick={() => load(page)}
            className="text-sm px-3 py-1.5 rounded-lg border border-gray-700 text-gray-400 hover:text-white hover:border-gray-600 transition-colors"
          >
            ↻ Refrescar
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg border border-yellow-500/30 bg-yellow-500/5 text-yellow-400 text-sm">
          ⚠ {error}
        </div>
      )}

      {loading ? (
        <div className="text-center text-gray-600 text-sm py-12">Cargando…</div>
      ) : items.length === 0 ? (
        <div className="text-center text-gray-600 text-sm py-12">Sin leads todavía.</div>
      ) : (
        <div className="rounded-xl border border-gray-800 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/60">
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Nombre</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Teléfono</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Interés</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Etapa</th>
                <th className="text-left px-4 py-3 text-gray-500 font-medium">Creado</th>
              </tr>
            </thead>
            <tbody>
              {items.map((l) => (
                <tr key={l.id} className="border-b border-gray-800/50 hover:bg-gray-900/40 transition-colors">
                  <td className="px-4 py-3 text-white">{l.contact_name ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-400 font-mono text-xs">{l.phone}</td>
                  <td className="px-4 py-3 text-gray-400 max-w-xs truncate">{l.interest ?? '—'}</td>
                  <td className="px-4 py-3"><StageBadge stage={l.stage} /></td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(l.created_at).toLocaleString('es', { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {total > 50 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-xs text-gray-500">Página {page} de {Math.ceil(total / 50)}</p>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
              className="px-3 py-1.5 text-xs rounded-lg border border-gray-700 text-gray-400 hover:text-white disabled:opacity-40">
              ← Anterior
            </button>
            <button disabled={page >= Math.ceil(total / 50)} onClick={() => setPage(p => p + 1)}
              className="px-3 py-1.5 text-xs rounded-lg border border-gray-700 text-gray-400 hover:text-white disabled:opacity-40">
              Siguiente →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

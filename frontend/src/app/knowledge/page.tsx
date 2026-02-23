'use client'

import { useState } from 'react'
import Link from 'next/link'

type Tab = 'catalog' | 'docs'

const CATALOG_TABS = [
  { id: 'catalog' as Tab, label: 'Catálogo de Productos' },
  { id: 'docs' as Tab,    label: 'Documentos de Soporte' },
]

export default function KnowledgePage() {
  const [tab, setTab] = useState<Tab>('catalog')

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-white">Base de Conocimiento</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Gestiona el catálogo RAG de productos y los documentos de soporte indexados.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-800 mb-6">
        {CATALOG_TABS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === id
                ? 'border-green-500 text-green-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'catalog' && (
        <div className="space-y-4">
          <div className="p-5 rounded-xl border border-gray-800 bg-gray-900/60">
            <h2 className="text-sm font-semibold text-white mb-1">Catálogo de Productos</h2>
            <p className="text-xs text-gray-500 mb-4">
              Indexa productos en ChromaDB (colección <code className="font-mono text-green-400">catalog</code>).
              Accede a la página de catálogo para agregar o actualizar productos.
            </p>
            <Link
              href="/catalog"
              className="inline-flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-green-500/10 text-green-400 border border-green-500/20 hover:bg-green-500/20 transition-colors"
            >
              Ir a Catálogo →
            </Link>
          </div>

          <div className="p-5 rounded-xl border border-gray-800 bg-gray-900/60">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Formato esperado (JSON)
            </h3>
            <pre className="text-xs text-gray-400 bg-gray-950 rounded-lg p-4 overflow-x-auto">
{JSON.stringify([
  {
    "name": "Producto Ejemplo",
    "price": 99.99,
    "description": "Descripción del producto",
    "category": "Electrónica",
    "sku": "SKU-001"
  }
], null, 2)}
            </pre>
          </div>
        </div>
      )}

      {tab === 'docs' && (
        <div className="space-y-4">
          <div className="p-5 rounded-xl border border-gray-800 bg-gray-900/60">
            <h2 className="text-sm font-semibold text-white mb-1">Documentos de Soporte</h2>
            <p className="text-xs text-gray-500 mb-4">
              Indexa PDFs y manuales en ChromaDB (colección <code className="font-mono text-green-400">support_docs</code>).
              Accede a la página de documentos para subir nuevos archivos.
            </p>
            <Link
              href="/docs"
              className="inline-flex items-center gap-2 text-sm px-4 py-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20 transition-colors"
            >
              Ir a Documentos →
            </Link>
          </div>

          <div className="p-5 rounded-xl border border-gray-800 bg-gray-900/60">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Formatos soportados
            </h3>
            <ul className="text-xs text-gray-400 space-y-1">
              <li>• <code className="font-mono text-blue-400">.pdf</code> — Documentos PDF</li>
              <li>• <code className="font-mono text-blue-400">.txt</code> — Texto plano</li>
              <li>• <code className="font-mono text-blue-400">.md</code>  — Markdown</li>
            </ul>
          </div>

          <div className="p-5 rounded-xl border border-gray-800 bg-gray-900/60">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Cómo funciona el RAG
            </h3>
            <p className="text-xs text-gray-400 leading-relaxed">
              Los documentos se dividen en chunks, se generan embeddings con OpenAI y se almacenan
              en ChromaDB. Cuando un cliente hace una pregunta, el agente recupera los chunks más
              relevantes como contexto antes de responder.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

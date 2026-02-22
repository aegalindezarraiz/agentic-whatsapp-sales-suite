'use client'

import { useState } from 'react'
import { ingestCatalog, type IngestResponse } from '@/lib/api'

const EXAMPLE_JSON = `[
  {
    "name": "Auriculares Bluetooth Pro",
    "price": 79.99,
    "category": "Electrónica",
    "description": "Auriculares inalámbricos con cancelación de ruido activa, batería de 30h.",
    "sku": "ABT-001",
    "stock": 150,
    "features": ["ANC", "Bluetooth 5.3", "USB-C", "Plegables"]
  },
  {
    "name": "Teclado mecánico RGB",
    "price": 54.99,
    "category": "Accesorios",
    "description": "Teclado compacto TKL con switches rojos, retroiluminación RGB por tecla.",
    "sku": "TEC-002",
    "stock": 80
  }
]`

export default function CatalogPage() {
  const [json, setJson] = useState(EXAMPLE_JSON)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<IngestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [jsonError, setJsonError] = useState<string | null>(null)

  function handleJsonChange(value: string) {
    setJson(value)
    setJsonError(null)
    try {
      JSON.parse(value)
    } catch (e) {
      setJsonError(e instanceof Error ? e.message : 'JSON inválido')
    }
  }

  async function handleIngest() {
    setJsonError(null)
    let products: object[]
    try {
      products = JSON.parse(json)
      if (!Array.isArray(products)) throw new Error('El JSON debe ser un array de productos')
    } catch (e) {
      setJsonError(e instanceof Error ? e.message : 'JSON inválido')
      return
    }

    setLoading(true)
    setResult(null)
    setError(null)

    try {
      const r = await ingestCatalog(products)
      setResult(r)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  const isValid = !jsonError && json.trim().length > 0

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-white">Catálogo de productos</h1>
        <p className="text-sm text-gray-500 mt-1">
          Ingesta productos en formato JSON. Los agentes usarán esta información para responder
          consultas de clientes sobre precios, disponibilidad y características.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Editor */}
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">Productos (JSON Array)</label>
            {jsonError && (
              <span className="text-xs text-red-400">{jsonError}</span>
            )}
          </div>
          <textarea
            value={json}
            onChange={e => handleJsonChange(e.target.value)}
            rows={22}
            spellCheck={false}
            className={`w-full rounded-xl border font-mono text-sm p-4 bg-gray-900 text-gray-100 focus:outline-none resize-none transition-colors ${
              jsonError ? 'border-red-500/50 focus:border-red-500' : 'border-gray-700 focus:border-blue-500'
            }`}
          />
          <button
            onClick={handleIngest}
            disabled={loading || !isValid}
            className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 font-medium text-sm transition-colors"
          >
            {loading ? 'Indexando…' : 'Ingresar al catálogo'}
          </button>
        </div>

        {/* Info & result */}
        <div className="flex flex-col gap-4">
          {result && (
            <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5">
              <p className="font-medium text-emerald-400 text-sm">Ingesta exitosa</p>
              <p className="text-gray-300 text-sm mt-1">
                <span className="font-bold text-white">{result.chunks_indexed}</span> chunks indexados
                en la colección{' '}
                <code className="text-blue-400 text-xs">{result.collection}</code>
              </p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl border border-red-500/30 bg-red-500/5">
              <p className="font-medium text-red-400 text-sm">Error</p>
              <p className="text-gray-300 text-sm mt-1">{error}</p>
            </div>
          )}

          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Campos reconocidos
            </p>
            <table className="w-full text-xs">
              <tbody className="divide-y divide-gray-800">
                {[
                  ['name', 'Nombre del producto', true],
                  ['price', 'Precio (número)', false],
                  ['category', 'Categoría', false],
                  ['description', 'Descripción detallada', false],
                  ['sku', 'Código de inventario', false],
                  ['stock', 'Unidades disponibles', false],
                  ['features', 'Lista de características []', false],
                ].map(([field, desc, req]) => (
                  <tr key={String(field)}>
                    <td className="py-1.5 pr-3">
                      <code className="text-blue-400">{field}</code>
                      {req && <span className="ml-1 text-red-400">*</span>}
                    </td>
                    <td className="py-1.5 text-gray-500">{String(desc)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-gray-600 text-xs mt-2">* Requerido. Los demás campos son opcionales.</p>
          </div>

          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Nota</p>
            <p className="text-xs text-gray-500">
              Cada ingesta <span className="text-white">reemplaza o agrega</span> los documentos
              existentes con el mismo SKU. Para actualizar un producto, edita su JSON y reingrésalo.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

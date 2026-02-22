'use client'

import { useState } from 'react'
import { ingestDocument, type IngestResponse } from '@/lib/api'

const TAGS = ['manual', 'faq', 'politicas', 'garantia', 'soporte', 'catalogo']

export default function DocsPage() {
  const [filePath, setFilePath] = useState('')
  const [sourceTag, setSourceTag] = useState('manual')
  const [customTag, setCustomTag] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<IngestResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const activeTag = sourceTag === '__custom' ? customTag : sourceTag

  async function handleIngest() {
    if (!filePath.trim() || !activeTag.trim()) return
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const r = await ingestDocument(filePath.trim(), activeTag.trim())
      setResult(r)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  const canSubmit = filePath.trim().length > 0 && activeTag.trim().length > 0 && !loading

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-white">Documentos de soporte</h1>
        <p className="text-sm text-gray-500 mt-1">
          Indexa archivos PDF o TXT en el RAG de soporte. Los agentes consultarán estos documentos
          para resolver preguntas técnicas, políticas y garantías.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Form */}
        <div className="flex flex-col gap-5">
          {/* File path */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Ruta del archivo en el servidor
            </label>
            <input
              type="text"
              value={filePath}
              onChange={e => setFilePath(e.target.value)}
              placeholder="/app/data/manual_usuario.pdf"
              className="w-full rounded-lg border border-gray-700 bg-gray-900 text-gray-100 text-sm px-4 py-2.5 focus:outline-none focus:border-blue-500 transition-colors font-mono"
            />
            <p className="text-xs text-gray-600 mt-1">
              Debe ser una ruta accesible dentro del contenedor del API.
              Coloca tus archivos en <code>/app/data/</code> (volume de Railway).
            </p>
          </div>

          {/* Tag selector */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">
              Etiqueta de fuente
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {TAGS.map(tag => (
                <button
                  key={tag}
                  onClick={() => setSourceTag(tag)}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                    sourceTag === tag
                      ? 'bg-blue-600 border-blue-500 text-white'
                      : 'border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-200'
                  }`}
                >
                  {tag}
                </button>
              ))}
              <button
                onClick={() => setSourceTag('__custom')}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  sourceTag === '__custom'
                    ? 'bg-blue-600 border-blue-500 text-white'
                    : 'border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-200'
                }`}
              >
                personalizado
              </button>
            </div>
            {sourceTag === '__custom' && (
              <input
                type="text"
                value={customTag}
                onChange={e => setCustomTag(e.target.value)}
                placeholder="mi-etiqueta"
                className="w-full rounded-lg border border-gray-700 bg-gray-900 text-gray-100 text-sm px-4 py-2 focus:outline-none focus:border-blue-500 transition-colors"
              />
            )}
          </div>

          <button
            onClick={handleIngest}
            disabled={!canSubmit}
            className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 font-medium text-sm transition-colors"
          >
            {loading ? 'Indexando…' : 'Indexar documento'}
          </button>

          {result && (
            <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5">
              <p className="font-medium text-emerald-400 text-sm">Indexado correctamente</p>
              <p className="text-gray-300 text-sm mt-1">
                <span className="font-bold text-white">{result.chunks_indexed}</span> chunks en{' '}
                <code className="text-blue-400 text-xs">{result.collection}</code>{' '}
                con tag <code className="text-yellow-400 text-xs">{activeTag}</code>
              </p>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl border border-red-500/30 bg-red-500/5">
              <p className="font-medium text-red-400 text-sm">Error</p>
              <p className="text-gray-300 text-sm mt-1">{error}</p>
            </div>
          )}
        </div>

        {/* Guidance */}
        <div className="flex flex-col gap-4">
          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Formatos soportados
            </p>
            <ul className="space-y-2 text-sm">
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-0.5">PDF</span>
                <span className="text-gray-500">
                  Manuales, catálogos, políticas, garantías. Se extrae texto automáticamente.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-400 mt-0.5">TXT</span>
                <span className="text-gray-500">
                  FAQs en texto plano, scripts de soporte, base de conocimiento.
                </span>
              </li>
            </ul>
          </div>

          <div className="p-4 rounded-xl border border-gray-800 bg-gray-900/60">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Cómo subir archivos al servidor
            </p>
            <ol className="space-y-2 text-xs text-gray-500 list-decimal list-inside">
              <li>En Railway, agrega un <span className="text-white">Volume</span> al servicio API con mount path <code className="text-blue-400">/app/data</code></li>
              <li>Usa <code className="text-blue-400">railway run</code> para copiar archivos al volumen</li>
              <li>
                O agrega los archivos via el <span className="text-white">Dockerfile</span> en tiempo de build:{' '}
                <code className="text-blue-400 block mt-1">COPY data/ /app/data/</code>
              </li>
            </ol>
          </div>

          <div className="p-4 rounded-xl border border-yellow-500/20 bg-yellow-500/5">
            <p className="text-xs font-semibold text-yellow-400 uppercase tracking-wider mb-2">
              Consejo
            </p>
            <p className="text-xs text-gray-500">
              Usa etiquetas descriptivas (<code className="text-yellow-300">garantia</code>,{' '}
              <code className="text-yellow-300">faq</code>) para que los agentes puedan filtrar
              documentos por tipo al responder consultas específicas.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

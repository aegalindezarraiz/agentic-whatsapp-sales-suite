// Base URL del backend — se inyecta en build time por Railway como env var
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'http://localhost:8000'

export interface HealthResponse {
  status: 'ok' | 'error'
  version: string
  env: string
}

export interface StatsResponse {
  queue: {
    queued: number
    started: number
    finished: number
    failed: number
    deferred: number
    error?: string
  }
  rag: {
    catalog: number
    support_docs: number
    error?: string
  }
  config: {
    whatsapp_provider: string
    llm_model: string
    env: string
  }
}

export interface IngestResponse {
  status: string
  chunks_indexed: number
  collection: string
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_URL}/health`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`Health check falló: ${res.status}`)
  return res.json()
}

export async function fetchStats(): Promise<StatsResponse> {
  const res = await fetch(`${API_URL}/admin/stats`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`Stats falló: ${res.status}`)
  return res.json()
}

export async function ingestCatalog(products: object[]): Promise<IngestResponse> {
  const res = await fetch(`${API_URL}/admin/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: 'catalog', data: products }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export async function ingestDocument(
  filePath: string,
  sourceTag: string,
): Promise<IngestResponse> {
  const res = await fetch(`${API_URL}/admin/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type: 'document', file_path: filePath, source_tag: sourceTag }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  return res.json()
}

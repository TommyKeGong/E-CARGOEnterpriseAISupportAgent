import type {
  AgentAskResponse,
  AskResponse,
  DocumentChunkPage,
  DocumentDetail,
  DocumentListResponse,
  PageContext,
} from './types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init)
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body: unknown = await response.json()
      if (typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string') {
        message = body.detail
      }
    } catch {
      // The API may return an empty proxy or network error body.
    }
    throw new ApiError(message, response.status)
  }
  return response.json() as Promise<T>
}

export const api = {
  ask(question: string, mode: 'rag' | 'agent'): Promise<AskResponse | AgentAskResponse> {
    return request<AskResponse | AgentAskResponse>(
      mode === 'agent' ? '/api/v1/agent/ask' : '/api/v1/ask',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(
          mode === 'agent'
            ? { question, max_tool_calls: 5, debug_trace: true }
            : { question, top_k: 5, debug_retrieval: false },
        ),
      },
    )
  },
  listDocuments(offset = 0, limit = 20): Promise<DocumentListResponse> {
    return request(`/api/v1/documents?offset=${offset}&limit=${limit}`)
  },
  getDocument(documentId: string): Promise<DocumentDetail> {
    return request(`/api/v1/documents/${encodeURIComponent(documentId)}`)
  },
  getChunks(documentId: string, offset = 0, limit = 20, page?: number): Promise<DocumentChunkPage> {
    const params = new URLSearchParams({ offset: String(offset), limit: String(limit) })
    if (page !== undefined) params.set('pdf_page_number', String(page))
    return request(`/api/v1/documents/${encodeURIComponent(documentId)}/chunks?${params}`)
  },
  getPageContext(documentId: string, page: number): Promise<PageContext> {
    return request(`/api/v1/documents/${encodeURIComponent(documentId)}/pages/${page}/context`)
  },
  async uploadDocument(file: File): Promise<DocumentDetail> {
    const form = new FormData()
    form.append('file', file)
    return request('/api/v1/documents', { method: 'POST', body: form })
  },
  deleteDocument(documentId: string): Promise<{ document_id: string; status: 'deleted' }> {
    return request(`/api/v1/documents/${encodeURIComponent(documentId)}`, { method: 'DELETE' })
  },
}

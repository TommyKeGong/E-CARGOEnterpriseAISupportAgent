import { useEffect, useState } from 'react'
import { ApiError, api } from './api'
import type {
  AgentAskResponse,
  AgentTraceEntry,
  AskResponse,
  Citation,
  DocumentChunk,
  DocumentDetail,
  DocumentListItem,
  Evidence,
  PageContext,
} from './types'

type View = 'chat' | 'library' | 'sources'
type Mode = 'rag' | 'agent'
type ResearchResponse = AskResponse | AgentAskResponse

interface SourceTarget {
  documentId: string
  page: number
}

function isAgentResponse(response: ResearchResponse): response is AgentAskResponse {
  return 'tool_call_count' in response
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : 'Unexpected local API error.'
}

function statusLabel(status: ResearchResponse['status']): string {
  return status.replaceAll('_', ' ')
}

export default function App() {
  const [view, setView] = useState<View>('chat')
  const [sourceTarget, setSourceTarget] = useState<SourceTarget | null>(null)

  function openSource(documentId: string, page: number) {
    setSourceTarget({ documentId, page })
    setView('sources')
  }

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-4 py-6 sm:px-8">
      <header className="mb-8 flex flex-col justify-between gap-5 border-b border-ink/10 pb-6 md:flex-row md:items-end">
        <div>
          <p className="eyebrow">Local-first academic research</p>
          <h1 className="mt-1 font-serif text-3xl font-semibold tracking-tight">E-CARGO Knowledge Agent</h1>
          <p className="mt-2 max-w-2xl text-sm text-ink/70">
            Evidence-grounded answers, inspectable source chunks, and bounded local research tools.
          </p>
        </div>
        <nav className="flex gap-2" aria-label="Main navigation">
          {(['chat', 'library', 'sources'] as const).map((item) => (
            <button
              className={view === item ? 'button-primary' : 'button-quiet'}
              key={item}
              onClick={() => setView(item)}
              type="button"
            >
              {item[0].toUpperCase() + item.slice(1)}
            </button>
          ))}
        </nav>
      </header>
      {view === 'chat' && <ChatView onOpenSource={openSource} />}
      {view === 'library' && <LibraryView onOpenSource={openSource} />}
      {view === 'sources' && <SourcesView target={sourceTarget} onOpenSource={openSource} />}
    </main>
  )
}

function ChatView({ onOpenSource }: { onOpenSource: (documentId: string, page: number) => void }) {
  const [mode, setMode] = useState<Mode>('rag')
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<ResearchResponse[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = question.trim()
    if (!trimmed || loading) return
    setLoading(true)
    setError(null)
    try {
      const response = await api.ask(trimmed, mode)
      setHistory((items) => [...items, response])
      setQuestion('')
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_17rem]">
      <div className="panel min-h-[38rem] p-5 sm:p-7">
        <div className="mb-6 flex items-center justify-between gap-3">
          <div>
            <p className="eyebrow">Research conversation</p>
            <h2 className="text-xl font-semibold">Ask from the indexed literature</h2>
          </div>
          <span className="rounded-full bg-signal/10 px-3 py-1 text-xs font-medium text-signal">Private/local API</span>
        </div>
        {history.length === 0 ? (
          <div className="rounded-xl border border-dashed border-ink/20 p-6 text-sm text-ink/65">
            Submit a question to retrieve evidence. Answers and citations are rendered only from the API response.
          </div>
        ) : (
          <div className="space-y-5">
            {history.map((response, index) => (
              <ConversationItem key={`${response.question}-${index}`} response={response} onOpenSource={onOpenSource} />
            ))}
          </div>
        )}
        <form className="mt-8 border-t border-ink/10 pt-5" onSubmit={submit}>
          <label className="mb-2 block text-sm font-medium" htmlFor="question">Research question</label>
          <textarea
            className="control min-h-28 w-full resize-y"
            id="question"
            maxLength={500}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about the authorised E-CARGO literature…"
            value={question}
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex rounded-lg border border-ink/15 p-1" role="group" aria-label="Answer mode">
              {(['rag', 'agent'] as const).map((candidate) => (
                <button
                  className={`rounded-md px-3 py-1.5 text-sm ${mode === candidate ? 'bg-ink text-white' : 'text-ink/70'}`}
                  key={candidate}
                  onClick={() => setMode(candidate)}
                  type="button"
                >
                  {candidate === 'rag' ? 'RAG' : 'Agent'}
                </button>
              ))}
            </div>
            <button className="button-primary" disabled={loading || question.trim().length === 0} type="submit">
              {loading ? 'Retrieving evidence…' : 'Ask question'}
            </button>
          </div>
          {error && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}
        </form>
      </div>
      <aside className="panel h-fit p-5 text-sm text-ink/70">
        <p className="eyebrow">Mode guide</p>
        <h2 className="mt-1 font-semibold text-ink">Bounded by design</h2>
        <p className="mt-3">RAG calls the direct evidence workflow. Agent mode may use only the backend’s fixed read-only research tools.</p>
        <p className="mt-4 text-xs">Citation IDs are structurally validated by the backend, but that check alone does not prove every generated claim is semantically supported.</p>
      </aside>
    </section>
  )
}

function ConversationItem({
  response,
  onOpenSource,
}: {
  response: ResearchResponse
  onOpenSource: (documentId: string, page: number) => void
}) {
  return (
    <article className="rounded-xl border border-ink/10 bg-paper/50 p-4">
      <p className="text-sm font-medium">{response.question}</p>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className="rounded-full bg-ink/8 px-2 py-1 capitalize">{statusLabel(response.status)}</span>
        <span className="text-ink/55">Provider: {response.provider}</span>
        {isAgentResponse(response) && <span className="text-ink/55">{response.tool_call_count} tool call(s) · {response.execution_time_ms} ms</span>}
      </div>
      <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-ink/85">
        {response.answer ?? 'No generated answer was returned. Review the retrieved evidence or refine the question.'}
      </p>
      {response.invalid_citation_count > 0 && <p className="mt-3 text-sm text-amber">{response.invalid_citation_count} citation(s) were rejected by validation.</p>}
      <CitationList citations={response.citations} onOpenSource={onOpenSource} />
      <EvidenceList evidence={response.evidence} onOpenSource={onOpenSource} />
      {isAgentResponse(response) && response.debug_trace && <AgentTrace trace={response.debug_trace} />}
    </article>
  )
}

function CitationList({ citations, onOpenSource }: { citations: Citation[]; onOpenSource: (documentId: string, page: number) => void }) {
  if (!citations.length) return null
  return (
    <div className="mt-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink/55">Citations</p>
      <ul className="mt-2 flex flex-wrap gap-2">
        {citations.map((citation) => (
          <li key={`${citation.document_id}-${citation.chunk_id}`}>
            <button className="rounded-md bg-signal/10 px-2 py-1 text-xs text-signal hover:bg-signal/20" onClick={() => onOpenSource(citation.document_id, citation.pdf_page_number)} type="button">
              {citation.source_filename} · p. {citation.pdf_page_number}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function EvidenceList({ evidence, onOpenSource }: { evidence: Evidence[]; onOpenSource: (documentId: string, page: number) => void }) {
  if (!evidence.length) return null
  return (
    <details className="mt-4 rounded-lg border border-ink/10 bg-white p-3">
      <summary className="cursor-pointer text-sm font-medium">Evidence ({evidence.length})</summary>
      <div className="mt-3 space-y-3">
        {evidence.map((item) => (
          <article className="border-l-2 border-signal/50 pl-3" key={item.chunk_id}>
            <button className="text-left text-xs font-semibold text-signal hover:underline" onClick={() => onOpenSource(item.document_id, item.pdf_page_number)} type="button">
              {item.source_filename} · page {item.pdf_page_number} · {item.chunk_id}
            </button>
            {item.similarity_score !== null && <span className="ml-2 text-xs text-ink/45">score {item.similarity_score.toFixed(3)}</span>}
            <p className="mt-1 line-clamp-5 whitespace-pre-wrap text-xs leading-5 text-ink/75">{item.text}</p>
          </article>
        ))}
      </div>
    </details>
  )
}

function AgentTrace({ trace }: { trace: AgentTraceEntry[] }) {
  return (
    <details className="mt-4 text-xs text-ink/65">
      <summary className="cursor-pointer font-medium">Agent execution details</summary>
      <ol className="mt-2 space-y-1 border-l border-ink/15 pl-3">
        {trace.map((item) => <li key={`${item.step}-${item.event}`}>Step {item.step}: {item.event}{item.tool_name ? ` · ${item.tool_name}` : ''}{item.result_item_count !== null ? ` · ${item.result_item_count} evidence item(s)` : ''}{item.message ? ` · ${item.message}` : ''}</li>)}
      </ol>
    </details>
  )
}

function LibraryView({ onOpenSource }: { onOpenSource: (documentId: string, page: number) => void }) {
  const [documents, setDocuments] = useState<DocumentListItem[]>([])
  const [selected, setSelected] = useState<DocumentDetail | null>(null)
  const [chunks, setChunks] = useState<DocumentChunk[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)

  async function loadDocuments() {
    setLoading(true)
    setError(null)
    try {
      const response = await api.listDocuments()
      setDocuments(response.items)
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadDocuments() }, [])

  async function selectDocument(documentId: string) {
    setError(null)
    try {
      const [detail, page] = await Promise.all([api.getDocument(documentId), api.getChunks(documentId)])
      setSelected(detail)
      setChunks(page.items)
    } catch (requestError) {
      setError(errorMessage(requestError))
    }
  }

  async function upload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      await api.uploadDocument(file)
      await loadDocuments()
    } catch (requestError) {
      setError(errorMessage(requestError))
    } finally {
      setUploading(false)
    }
  }

  async function deleteSelected() {
    if (!selected || !window.confirm(`Delete ${selected.source_filename} and its indexed chunks? This cannot restore the uploaded original.`)) return
    try {
      await api.deleteDocument(selected.document_id)
      setSelected(null)
      setChunks([])
      await loadDocuments()
    } catch (requestError) {
      setError(errorMessage(requestError))
    }
  }

  return (
    <section className="grid gap-5 lg:grid-cols-[22rem_minmax(0,1fr)]">
      <aside className="panel p-5">
        <div className="flex items-center justify-between gap-2"><div><p className="eyebrow">Library</p><h2 className="font-semibold">Indexed documents</h2></div><button className="button-quiet text-sm" onClick={() => void loadDocuments()} type="button">Refresh</button></div>
        <label className="button-primary mt-5 block cursor-pointer text-center text-sm">
          {uploading ? 'Uploading…' : 'Upload PDF'}
          <input accept="application/pdf,.pdf" className="sr-only" disabled={uploading} onChange={(event) => void upload(event)} type="file" />
        </label>
        <p className="mt-2 text-xs text-ink/55">The API validates PDF content and its configured size limit.</p>
        <div className="mt-5 space-y-2">
          {loading && <p className="text-sm text-ink/60">Loading local index…</p>}
          {!loading && documents.length === 0 && <p className="text-sm text-ink/60">No documents are indexed.</p>}
          {documents.map((document) => <button className={`w-full rounded-lg border p-3 text-left text-sm ${selected?.document_id === document.document_id ? 'border-signal bg-signal/5' : 'border-ink/10 hover:bg-ink/5'}`} key={document.document_id} onClick={() => void selectDocument(document.document_id)} type="button"><span className="block truncate font-medium">{document.title ?? document.source_filename}</span><span className="mt-1 block text-xs text-ink/55">{document.page_count} pages · {document.chunk_count} chunks</span></button>)}
        </div>
      </aside>
      <div className="panel min-h-[32rem] p-5 sm:p-7">
        {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}
        {!selected ? <div className="text-sm text-ink/60">Select an indexed document to inspect its safe metadata and persisted chunks.</div> : <><div className="flex flex-wrap justify-between gap-4"><div><p className="eyebrow">Document detail</p><h2 className="text-xl font-semibold">{selected.title ?? selected.source_filename}</h2><p className="mt-1 text-sm text-ink/60">{selected.document_id} · {selected.indexing_status} · {selected.embedding_count} embeddings</p></div><button className="button border border-red-200 text-sm text-red-700 hover:bg-red-50" onClick={() => void deleteSelected()} type="button">Delete document</button></div><dl className="mt-6 grid gap-4 text-sm sm:grid-cols-3"><Fact label="Pages" value={selected.page_count} /><Fact label="Chunks" value={selected.chunk_count} /><Fact label="Rights" value={selected.rights_status} /><Fact label="Authors" value={selected.authors?.join(', ') ?? 'Not indexed'} /><Fact label="Venue" value={selected.publication_venue ?? 'Not indexed'} /><Fact label="DOI" value={selected.doi ?? 'Not indexed'} /></dl><div className="mt-7"><p className="eyebrow">Persisted chunks</p><div className="mt-3 space-y-3">{chunks.map((chunk) => <article className="rounded-lg border border-ink/10 p-3" key={chunk.chunk_id}><button className="text-xs font-semibold text-signal hover:underline" onClick={() => onOpenSource(selected.document_id, chunk.pdf_page_number)} type="button">Page {chunk.pdf_page_number} · {chunk.chunk_id}</button><p className="mt-1 line-clamp-4 whitespace-pre-wrap text-sm leading-6 text-ink/75">{chunk.chunk_text}</p></article>)}</div></div></>}
      </div>
    </section>
  )
}

function Fact({ label, value }: { label: string; value: string | number }) { return <div><dt className="text-xs uppercase tracking-wide text-ink/50">{label}</dt><dd className="mt-1 break-words text-ink/80">{value}</dd></div> }

function SourcesView({ target, onOpenSource }: { target: SourceTarget | null; onOpenSource: (documentId: string, page: number) => void }) {
  const [documentId, setDocumentId] = useState(target?.documentId ?? '')
  const [page, setPage] = useState(String(target?.page ?? ''))
  const [context, setContext] = useState<PageContext | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (target) { setDocumentId(target.documentId); setPage(String(target.page)) }
  }, [target])

  async function inspect(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const pageNumber = Number(page)
    if (!documentId.trim() || !Number.isInteger(pageNumber) || pageNumber < 1) { setError('Enter a document ID and a positive physical PDF page number.'); return }
    setLoading(true); setError(null)
    try { setContext(await api.getPageContext(documentId.trim(), pageNumber)) } catch (requestError) { setContext(null); setError(errorMessage(requestError)) } finally { setLoading(false) }
  }

  return <section className="grid gap-5 lg:grid-cols-[21rem_minmax(0,1fr)]"><aside className="panel h-fit p-5"><p className="eyebrow">Evidence inspector</p><h2 className="mt-1 font-semibold">Indexed page context</h2><p className="mt-3 text-sm text-ink/65">Inspect persisted chunks only. This does not reconstruct the original PDF page.</p><form className="mt-5 space-y-3" onSubmit={inspect}><label className="block text-sm font-medium">Document ID<input className="control mt-1 w-full" onChange={(event) => setDocumentId(event.target.value)} value={documentId} /></label><label className="block text-sm font-medium">PDF page number<input className="control mt-1 w-full" inputMode="numeric" min="1" onChange={(event) => setPage(event.target.value)} type="number" value={page} /></label><button className="button-primary w-full" disabled={loading} type="submit">{loading ? 'Loading…' : 'Inspect context'}</button></form></aside><div className="panel min-h-[32rem] p-5 sm:p-7">{error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-800" role="alert">{error}</p>}{!context && !error && <p className="text-sm text-ink/60">Choose a citation from chat or enter a document ID and page.</p>}{context && <><p className="eyebrow">{context.document_id} · physical page {context.pdf_page_number}</p><h2 className="mt-1 text-xl font-semibold">Available indexed text</h2><p className="mt-3 rounded-lg bg-amber/10 p-3 text-sm text-ink/75">{context.context_note}</p>{!context.indexed_text_available ? <p className="mt-5 text-sm text-ink/60">No indexed text is available for this physical page.</p> : <div className="mt-5 space-y-4">{context.chunks.map((chunk) => <article className="rounded-lg border border-ink/10 p-4" key={chunk.chunk_id}><button className="text-xs font-semibold text-signal hover:underline" onClick={() => onOpenSource(chunk.document_id, chunk.pdf_page_number)} type="button">{chunk.source_filename} · {chunk.chunk_id}</button><p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-ink/80">{chunk.chunk_text}</p></article>)}</div>}</>}</div></section>
}

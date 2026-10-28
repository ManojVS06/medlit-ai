import { useEffect, useState } from 'react'
import { summarizeAbstract, checkHealth } from './services/api'
import type { SummarizeResponse } from './services/api'
import SummaryDisplay from './components/SummaryDisplay'

/**
 * MedLit AI — Main Application
 *
 * Milestone 2: First Vertical Slice
 * - User pastes an abstract into a text area
 * - Clicks "Summarize"
 * - Frontend sends POST /api/summaries to the backend
 * - Backend runs mock summarization and returns structured JSON
 * - Frontend renders the 13-field summary
 *
 * This demonstrates the complete request lifecycle:
 * Browser → HTTP POST → FastAPI → Pydantic validation → Service → Response → React render
 */

// Sample abstract for demonstration (from a real published study)
const SAMPLE_ABSTRACT = `OBJECTIVE: To evaluate the effects of supervised exercise programs on glycemic control in adults with type 2 diabetes. METHODS: A systematic review and meta-analysis of randomized controlled trials was conducted. We searched PubMed, EMBASE, and the Cochrane Library for studies published through 2019. Eligible studies included adults with type 2 diabetes randomized to supervised exercise versus a control group. The primary outcome was change in HbA1c. RESULTS: Twenty-two trials with 1,245 participants were included. Supervised exercise was associated with a significant reduction in HbA1c compared with control (mean difference -0.67%, 95% CI -0.84 to -0.49, p < 0.001). Both aerobic and resistance training showed significant improvements. CONCLUSIONS: Supervised exercise programs significantly improve glycemic control in adults with type 2 diabetes. These findings support current guidelines recommending regular physical activity for diabetes management. Limitations include heterogeneity in exercise protocols and short follow-up durations.`

interface HealthStatus {
  status: string
  service: string
  version: string
  llm_provider: string
}

function App() {
  // --- State ---
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)

  const [abstractText, setAbstractText] = useState('')
  const [title, setTitle] = useState('')
  const [pmid, setPmid] = useState('')

  const [summaryResult, setSummaryResult] = useState<SummarizeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // --- Health check on mount ---
  useEffect(() => {
    checkHealth()
      .then(data => { setHealth(data); setHealthError(null) })
      .catch(err => { setHealthError(err.message); setHealth(null) })
  }, [])

  // --- Handlers ---
  const handleSummarize = async () => {
    if (abstractText.trim().length < 50) {
      setError('Abstract must be at least 50 characters.')
      return
    }

    setLoading(true)
    setError(null)
    setSummaryResult(null)

    try {
      const result = await summarizeAbstract({
        abstract_text: abstractText.trim(),
        title: title.trim() || undefined,
        pmid: pmid.trim() || undefined,
      })
      setSummaryResult(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Summarization failed')
    } finally {
      setLoading(false)
    }
  }

  const handleLoadSample = () => {
    setAbstractText(SAMPLE_ABSTRACT)
    setTitle('Effects of Supervised Exercise on Glycemic Control in Type 2 Diabetes')
    setPmid('31532808')
    setError(null)
    setSummaryResult(null)
  }

  const handleClear = () => {
    setAbstractText('')
    setTitle('')
    setPmid('')
    setError(null)
    setSummaryResult(null)
  }

  return (
    <div className="min-h-screen bg-surface-900 text-white font-sans flex flex-col">
      {/* Header */}
      <header className="border-b border-surface-700 sticky top-0 bg-surface-900/95 backdrop-blur-sm z-10">
        <div className="max-w-5xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700
                          flex items-center justify-center font-bold text-xs shadow-lg shadow-primary-900/30">
              ML
            </div>
            <h1 className="text-lg font-semibold tracking-tight">
              MedLit <span className="text-primary-400">AI</span>
            </h1>
          </div>
          <div className="flex items-center gap-3">
            {/* Backend status indicator */}
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${
                health ? 'bg-accent-emerald' : healthError ? 'bg-accent-rose' : 'bg-accent-amber animate-pulse'
              }`} />
              <span className="text-xs text-surface-500">
                {health ? 'Connected' : healthError ? 'Offline' : 'Connecting...'}
              </span>
            </div>
            <span className="text-xs text-surface-500 font-mono">v0.1.0</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-8 flex-1 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

          {/* Left: Input Form */}
          <div className="space-y-4">
            <div>
              <h2 className="text-xl font-semibold mb-1">Summarize Abstract</h2>
              <p className="text-sm text-surface-500">
                Paste a research abstract below to generate a structured summary.
              </p>
            </div>

            {/* Title (optional) */}
            <div>
              <label htmlFor="article-title" className="block text-xs font-medium text-surface-500 mb-1.5">
                Article Title <span className="text-surface-600">(optional)</span>
              </label>
              <input
                id="article-title"
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                placeholder="e.g., Effects of Exercise on Glycemic Control..."
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2
                          text-sm text-white placeholder-surface-600
                          focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent
                          transition-all"
              />
            </div>

            {/* PMID (optional) */}
            <div>
              <label htmlFor="pmid" className="block text-xs font-medium text-surface-500 mb-1.5">
                PubMed ID <span className="text-surface-600">(optional)</span>
              </label>
              <input
                id="pmid"
                type="text"
                value={pmid}
                onChange={e => setPmid(e.target.value)}
                placeholder="e.g., 31532808"
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2
                          text-sm text-white placeholder-surface-600
                          focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent
                          transition-all"
              />
            </div>

            {/* Abstract text */}
            <div>
              <label htmlFor="abstract-text" className="block text-xs font-medium text-surface-500 mb-1.5">
                Abstract Text <span className="text-accent-rose">*</span>
              </label>
              <textarea
                id="abstract-text"
                value={abstractText}
                onChange={e => setAbstractText(e.target.value)}
                placeholder="Paste the research abstract here (minimum 50 characters)..."
                rows={12}
                className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2.5
                          text-sm text-white placeholder-surface-600 leading-relaxed resize-y
                          focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent
                          transition-all"
              />
              <div className="flex justify-between mt-1">
                <span className={`text-xs ${
                  abstractText.length > 0 && abstractText.length < 50
                    ? 'text-accent-rose' : 'text-surface-600'
                }`}>
                  {abstractText.length > 0 && abstractText.length < 50
                    ? `${50 - abstractText.length} more characters needed`
                    : `${abstractText.length.toLocaleString()} characters`
                  }
                </span>
                <span className="text-xs text-surface-600">Min: 50 / Max: 15,000</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleSummarize}
                disabled={loading || abstractText.trim().length < 50}
                className="flex-1 bg-primary-600 hover:bg-primary-500 disabled:bg-surface-700
                         disabled:text-surface-500 text-white font-medium text-sm
                         px-4 py-2.5 rounded-lg transition-all duration-200
                         focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
                         focus:ring-offset-surface-900 cursor-pointer disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Summarizing...
                  </span>
                ) : (
                  'Summarize'
                )}
              </button>

              <button
                onClick={handleLoadSample}
                disabled={loading}
                className="bg-surface-700 hover:bg-surface-600 text-surface-500 hover:text-white
                         text-sm px-4 py-2.5 rounded-lg transition-all duration-200
                         focus:outline-none focus:ring-2 focus:ring-surface-500 cursor-pointer"
              >
                Load Sample
              </button>

              <button
                onClick={handleClear}
                disabled={loading}
                className="bg-surface-700 hover:bg-surface-600 text-surface-500 hover:text-white
                         text-sm px-4 py-2.5 rounded-lg transition-all duration-200
                         focus:outline-none focus:ring-2 focus:ring-surface-500 cursor-pointer"
              >
                Clear
              </button>
            </div>

            {/* Error display */}
            {error && (
              <div className="bg-accent-rose/10 border border-accent-rose/20 rounded-lg px-4 py-3
                            flex items-start gap-2">
                <span className="text-accent-rose shrink-0">✕</span>
                <p className="text-sm text-red-200">{error}</p>
              </div>
            )}
          </div>

          {/* Right: Summary Display */}
          <div>
            {!summaryResult && !loading && (
              <div className="h-full flex items-center justify-center">
                <div className="text-center py-16">
                  <div className="text-4xl mb-4 opacity-30">📄</div>
                  <p className="text-surface-500 text-sm">
                    Paste an abstract and click <strong className="text-surface-500">Summarize</strong> to see
                    the structured summary here.
                  </p>
                  <p className="text-surface-600 text-xs mt-2">
                    Or click <strong>Load Sample</strong> to try a demo abstract.
                  </p>
                </div>
              </div>
            )}

            {loading && (
              <div className="h-full flex items-center justify-center">
                <div className="text-center py-16">
                  <svg className="animate-spin h-8 w-8 text-primary-500 mx-auto mb-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <p className="text-surface-500 text-sm">Analyzing abstract...</p>
                </div>
              </div>
            )}

            {summaryResult && <SummaryDisplay data={summaryResult} />}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-700 mt-auto">
        <div className="max-w-5xl mx-auto px-6 py-3 text-center text-xs text-surface-600">
          MedLit AI — A student engineering project for research assistance.
          AI-generated content requires expert verification.
        </div>
      </footer>
    </div>
  )
}

export default App

/**
 * API service layer — all backend communication goes through here.
 *
 * WHY:
 * Centralizing API calls in one place means:
 * 1. If the backend URL changes, we update ONE file.
 * 2. Error handling is consistent.
 * 3. TypeScript types are applied at the boundary.
 * 4. Components don't need to know about fetch() details.
 */

const API_BASE = 'http://localhost:8000'

/**
 * Structured summary with 13 fields extracted from a research abstract.
 */
export interface StructuredSummary {
  research_objective: string
  study_design: string
  population: string
  intervention: string
  comparator: string
  outcomes: string
  main_findings: string
  statistical_results: string
  authors_conclusion: string
  limitations: string
  not_reported: string
  plain_language_summary: string
  source_references: string
}

/**
 * Full response from the summarization endpoint.
 */
export interface SummarizeResponse {
  summary: StructuredSummary
  provider: string
  disclaimer: string
  source_pmid: string | null
  source_title: string | null
}

/**
 * Request body for the summarization endpoint.
 */
export interface SummarizeRequest {
  abstract_text: string
  title?: string
  pmid?: string
}

/**
 * Submit an abstract for structured summarization.
 *
 * @param request - The abstract text and optional metadata
 * @returns The structured summary response
 * @throws Error if the request fails
 */
export async function summarizeAbstract(
  request: SummarizeRequest
): Promise<SummarizeResponse> {
  const response = await fetch(`${API_BASE}/api/summaries`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    // Try to extract error details from the response
    let detail = `HTTP ${response.status}`
    try {
      const errorData = await response.json()
      detail = errorData.detail?.message || errorData.detail || detail
    } catch {
      // Response wasn't JSON — use status text
      detail = `${response.status}: ${response.statusText}`
    }
    throw new Error(detail)
  }

  return response.json()
}

/**
 * Check backend health status.
 */
export async function checkHealth(): Promise<{
  status: string
  service: string
  version: string
  llm_provider: string
}> {
  const response = await fetch(`${API_BASE}/health`)
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`)
  }
  return response.json()
}

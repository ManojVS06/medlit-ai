import type { SummarizeResponse } from '../services/api'

/**
 * Displays a structured 13-field summary of a research abstract.
 *
 * Design decisions:
 * - Fields are grouped into logical sections (Objective, Methods, Results, etc.)
 * - "Not reported" values are visually dimmed so the user can quickly
 *   distinguish extracted data from missing data.
 * - The disclaimer is always visible and prominently styled.
 * - Source references link back to the original paper.
 */

// Human-readable labels for each field, organized by section
const FIELD_SECTIONS = [
  {
    title: 'Study Overview',
    icon: '🔬',
    fields: [
      { key: 'research_objective', label: 'Research Objective' },
      { key: 'study_design', label: 'Study Design' },
      { key: 'population', label: 'Population & Sample' },
    ],
  },
  {
    title: 'Intervention & Comparison',
    icon: '💊',
    fields: [
      { key: 'intervention', label: 'Intervention / Exposure' },
      { key: 'comparator', label: 'Comparator / Control' },
      { key: 'outcomes', label: 'Outcomes Measured' },
    ],
  },
  {
    title: 'Results',
    icon: '📊',
    fields: [
      { key: 'main_findings', label: 'Main Findings' },
      { key: 'statistical_results', label: 'Statistical Results' },
    ],
  },
  {
    title: 'Interpretation',
    icon: '📝',
    fields: [
      { key: 'authors_conclusion', label: "Authors' Conclusion" },
      { key: 'limitations', label: 'Limitations' },
      { key: 'not_reported', label: 'Information Not Reported' },
    ],
  },
  {
    title: 'Summary',
    icon: '📋',
    fields: [
      { key: 'plain_language_summary', label: 'Plain Language Summary' },
      { key: 'source_references', label: 'Source References' },
    ],
  },
] as const

const NOT_REPORTED = 'Not reported in the provided abstract'

interface Props {
  data: SummarizeResponse
}

export default function SummaryDisplay({ data }: Props) {
  const { summary, provider, disclaimer, source_pmid, source_title } = data

  return (
    <div className="space-y-6">
      {/* Header with metadata */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        {source_title && (
          <h3 className="text-lg font-semibold text-white leading-snug max-w-xl">
            {source_title}
          </h3>
        )}
        <div className="flex items-center gap-2">
          {source_pmid && (
            <a
              href={`https://pubmed.ncbi.nlm.nih.gov/${source_pmid}/`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-primary-900/50 text-primary-300 px-2.5 py-1 rounded-full
                         hover:bg-primary-800/50 transition-colors"
            >
              PMID: {source_pmid} ↗
            </a>
          )}
          <span className="text-xs bg-surface-700 text-surface-500 px-2.5 py-1 rounded-full">
            Provider: {provider}
          </span>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-accent-amber/10 border border-accent-amber/20 rounded-lg px-4 py-3
                      flex items-start gap-2.5">
        <span className="text-accent-amber text-sm mt-0.5 shrink-0">⚠️</span>
        <p className="text-xs text-amber-200/80 leading-relaxed">{disclaimer}</p>
      </div>

      {/* Structured summary sections */}
      {FIELD_SECTIONS.map((section) => (
        <div key={section.title} className="bg-surface-800 border border-surface-700 rounded-xl overflow-hidden">
          <div className="px-4 py-3 bg-surface-700/50 border-b border-surface-700">
            <h4 className="text-sm font-medium text-surface-500 uppercase tracking-wider flex items-center gap-2">
              <span>{section.icon}</span>
              {section.title}
            </h4>
          </div>
          <div className="divide-y divide-surface-700/50">
            {section.fields.map(({ key, label }) => {
              const value = summary[key as keyof typeof summary]
              const isNotReported = value === NOT_REPORTED
              return (
                <div key={key} className="px-4 py-3">
                  <dt className="text-xs font-medium text-primary-400 mb-1.5">{label}</dt>
                  <dd
                    className={`text-sm leading-relaxed ${
                      isNotReported
                        ? 'text-surface-500 italic'
                        : 'text-gray-200'
                    }`}
                  >
                    {value}
                  </dd>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}

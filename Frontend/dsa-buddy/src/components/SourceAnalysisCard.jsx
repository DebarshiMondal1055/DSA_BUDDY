import React, { useState } from 'react'
import { BrainIcon, KeyIcon, ChevronDownIcon, SparklesIcon } from './Icons'

export default function SourceAnalysisCard({ source }) {
  const [activeTab, setActiveTab] = useState('concept')
  const [isExpanded, setIsExpanded] = useState(true)

  if (!source) return null

  const { title, platform, concept, method, method_from } = source
  const hasConcept = !!concept
  const hasMethod = !!method

  return (
    <div className="source-card">
      <div className="source-header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="source-header-left">
          <div className="source-badge-row">
            <span className="source-tag">Source Problem Analyzed</span>
            {platform && (
              <span className={`platform-badge ${platform.toLowerCase()}`}>
                {platform}
              </span>
            )}
            <span className="method-origin-badge">
              Method: {method_from || 'Inferred'}
            </span>
          </div>
          <h2 className="source-title">{title || 'Queried Problem'}</h2>
        </div>

        <div className="source-header-right">
          <button
            type="button"
            className="collapse-toggle-btn"
            title={isExpanded ? 'Collapse analysis' : 'Expand analysis'}
          >
            <ChevronDownIcon
              size={16}
              className={`chevron-icon transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            />
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="source-body">
          {/* Tabs for Concept vs Method */}
          <div className="source-tabs">
            {hasConcept && (
              <button
                type="button"
                className={`source-tab-btn ${activeTab === 'concept' ? 'active' : ''}`}
                onClick={() => setActiveTab('concept')}
              >
                <BrainIcon className="w-4 h-4" />
                <span>Concept Card (Abstract Structure)</span>
              </button>
            )}
            {hasMethod && (
              <button
                type="button"
                className={`source-tab-btn ${activeTab === 'method' ? 'active' : ''}`}
                onClick={() => setActiveTab('method')}
              >
                <KeyIcon className="w-4 h-4" />
                <span>Method Card (Mechanics & State)</span>
              </button>
            )}
          </div>

          {/* Concept Card Content */}
          {activeTab === 'concept' && hasConcept && (
            <div className="concept-view">
              <div className="concept-grid">
                <div className="concept-cell highlight-cell">
                  <span className="cell-label">Core Technique</span>
                  <span className="cell-value-emphasis text-accent">
                    {concept.core_technique || 'N/A'}
                  </span>
                </div>

                <div className="concept-cell">
                  <span className="cell-label">Complexity & Limits</span>
                  <div className="cell-flex-row">
                    {concept.complexity && (
                      <span className="code-pill font-mono">{concept.complexity}</span>
                    )}
                    {concept.constraint_regime && (
                      <span className="constraint-text">{concept.constraint_regime}</span>
                    )}
                  </div>
                </div>

                <div className="concept-cell full-width">
                  <span className="cell-label">Problem Reduction (Abstracted from story)</span>
                  <p className="reduction-text">{concept.reduction || 'N/A'}</p>
                </div>

                {concept.key_insight && (
                  <div className="concept-cell full-width insight-cell">
                    <span className="cell-label flex-row">
                      <SparklesIcon className="w-3.5 h-3.5 text-amber" />
                      Key Insight
                    </span>
                    <p className="insight-text">{concept.key_insight}</p>
                  </div>
                )}

                {concept.canonical_tags?.length > 0 && (
                  <div className="concept-cell full-width">
                    <span className="cell-label">Canonical Tags</span>
                    <div className="tags-flex">
                      {concept.canonical_tags.map((tag, idx) => (
                        <span key={idx} className="tag-chip">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {concept.data_structures?.length > 0 && (
                  <div className="concept-cell">
                    <span className="cell-label">Data Structures</span>
                    <div className="tags-flex">
                      {concept.data_structures.map((ds, idx) => (
                        <span key={idx} className="ds-chip font-mono">
                          {ds}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {concept.pitfalls?.length > 0 && (
                  <div className="concept-cell">
                    <span className="cell-label">Common Pitfalls</span>
                    <ul className="pitfalls-list">
                      {concept.pitfalls.map((pit, idx) => (
                        <li key={idx}>{pit}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Method Card Content */}
          {activeTab === 'method' && hasMethod && (
            <div className="method-view">
              <div className="method-grid">
                <div className="method-cell full-width">
                  <span className="cell-label">Method Keys</span>
                  <div className="tags-flex">
                    {(method.method_keys || []).map((mk, idx) => (
                      <span key={idx} className="method-key-chip">
                        {mk}
                      </span>
                    ))}
                  </div>
                </div>

                {method.state_signature && (
                  <div className="method-cell full-width">
                    <span className="cell-label">State Signature / Recurrence</span>
                    <code className="state-signature-block font-mono">
                      {method.state_signature}
                    </code>
                  </div>
                )}

                {method.primitives?.length > 0 && (
                  <div className="method-cell full-width">
                    <span className="cell-label">Algorithmic Primitives</span>
                    <div className="tags-flex">
                      {method.primitives.map((prim, idx) => (
                        <span key={idx} className="primitive-chip font-mono">
                          {prim}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {method.steps && (
                  <div className="method-cell full-width">
                    <span className="cell-label">Implementation Steps</span>
                    <div className="steps-container">
                      {Array.isArray(method.steps) ? (
                        <ol className="steps-list">
                          {method.steps.map((st, idx) => (
                            <li key={idx}>{st}</li>
                          ))}
                        </ol>
                      ) : (
                        <p className="steps-text">{method.steps}</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

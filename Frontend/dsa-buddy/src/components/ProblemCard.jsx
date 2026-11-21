import React, { useState } from 'react'
import { ExternalLinkIcon, SparklesIcon, CheckIcon, KeyIcon } from './Icons'

export default function ProblemCard({ problem, rank, onSelectMethod }) {
  const [copied, setCopied] = useState(false)

  const {
    problem_id,
    title,
    platform,
    url,
    difficulty,
    method_keys = [],
    concept_tags = [],
    primitives = [],
    shared_method_keys = [],
    state_signature,
    why,
  } = problem

  const handleCopy = (e) => {
    e.stopPropagation()
    if (!url) return
    navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Format difficulty display
  const formatDifficulty = () => {
    if (difficulty === null || difficulty === undefined) return 'Unrated'
    if (platform === 'leetcode') {
      if (difficulty <= 1) return 'Easy'
      if (difficulty <= 2) return 'Medium'
      return 'Hard'
    }
    return difficulty
  }

  const platLower = (platform || 'unknown').toLowerCase()
  const displayMethods = shared_method_keys.length > 0 ? shared_method_keys : method_keys

  return (
    <div className={`problem-card ${platLower}-border`}>
      {/* Top Header */}
      <div className="card-top-bar">
        <div className="card-top-left">
          <span className="rank-indicator">#{rank}</span>
          <span className={`platform-badge ${platLower}`}>
            {platform || 'Problem'}
          </span>
          <span className="problem-id-tag font-mono">{problem_id}</span>
        </div>

        <div className="card-top-right">
          <span className={`difficulty-badge ${platLower}-diff`}>
            {formatDifficulty()}
          </span>
        </div>
      </div>

      {/* Problem Title & Link */}
      <div className="card-title-row">
        <h3 className="problem-card-title">
          {url ? (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="problem-link"
            >
              <span>{title}</span>
              <ExternalLinkIcon className="link-icon" />
            </a>
          ) : (
            <span>{title}</span>
          )}
        </h3>

        {url && (
          <button
            type="button"
            className="copy-link-btn"
            onClick={handleCopy}
            title="Copy problem URL"
          >
            {copied ? <CheckIcon className="w-3.5 h-3.5 text-emerald" /> : 'Copy'}
          </button>
        )}
      </div>

      {/* AI Explanation ('Why this problem?') */}
      {why && (
        <div className="why-box">
          <div className="why-header">
            <SparklesIcon className="w-3.5 h-3.5 text-accent" />
            <span className="why-title">Why this problem</span>
          </div>
          <p className="why-text">{why}</p>
        </div>
      )}

      {/* Methods (Shared or Primary) */}
      {displayMethods.length > 0 && (
        <div className="card-section">
          <span className="section-label">
            {shared_method_keys.length > 0 ? 'Shared Machinery:' : 'Techniques:'}
          </span>
          <div className="chips-row">
            {displayMethods.map((mk, idx) => (
              <button
                key={idx}
                type="button"
                className="shared-method-chip"
                onClick={() => onSelectMethod && onSelectMethod(mk)}
                title={`Click to explore ladder for ${mk}`}
              >
                <KeyIcon className="w-3 h-3" />
                <span>{mk}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* State Signature if available */}
      {state_signature && (
        <div className="card-section">
          <span className="section-label">State:</span>
          <code className="mini-state-sig font-mono">{state_signature}</code>
        </div>
      )}

      {/* Tags & Primitives */}
      <div className="card-footer-tags">
        {concept_tags.slice(0, 4).map((tag, idx) => (
          <span key={idx} className="concept-tag-pill">
            #{tag}
          </span>
        ))}
        {primitives.slice(0, 3).map((prim, idx) => (
          <span key={idx} className="primitive-tag-pill font-mono">
            {prim}
          </span>
        ))}
      </div>
    </div>
  )
}

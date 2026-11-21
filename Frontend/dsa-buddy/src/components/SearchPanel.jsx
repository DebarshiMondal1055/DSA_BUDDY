import React, { useState } from 'react'
import {
  SearchIcon,
  CodeIcon,
  SparklesIcon,
  ChevronDownIcon,
  BrainIcon,
  KeyIcon,
} from './Icons'

const PRESETS = [
  {
    label: 'LeetCode: Two Sum',
    query: 'https://leetcode.com/problems/two-sum/',
    platform: 'leetcode',
    mode: 'both',
  },
  {
    label: 'Codeforces: 1850A',
    query: 'https://codeforces.com/problemset/problem/1850/A',
    platform: 'codeforces',
    mode: 'both',
  },
  {
    label: 'AtCoder: abc222_f',
    query: 'https://atcoder.jp/contests/abc222/tasks/abc222_f',
    platform: 'atcoder',
    mode: 'both',
  },
  {
    label: 'Natural Language Query',
    query: 'Find the maximum subarray sum in an array using Kadane algorithm or divide and conquer',
    platform: 'leetcode',
    mode: 'concept',
  },
]

export default function SearchPanel({ onSearch, isLoading }) {
  const [query, setQuery] = useState('')
  const [solutionCode, setSolutionCode] = useState('')
  const [showCodeInput, setShowCodeInput] = useState(false)
  const [mode, setMode] = useState('both')
  const [platform, setPlatform] = useState('')
  const [k, setK] = useState(12)
  const [perPlatformMin, setPerPlatformMin] = useState(3)
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Auto-detect platform when typing known URLs if user hasn't explicitly locked one
  const handleQueryChange = (val) => {
    setQuery(val)
    if (!platform) {
      if (val.includes('leetcode.com') || val.startsWith('lc:')) {
        setPlatform('leetcode')
      } else if (val.includes('codeforces.com') || val.startsWith('cf:')) {
        setPlatform('codeforces')
      } else if (val.includes('atcoder.jp') || val.startsWith('ac:')) {
        setPlatform('atcoder')
      }
    }
  }

  const handleSubmit = (e) => {
    if (e) e.preventDefault()
    if (!query.trim() || isLoading) return

    onSearch({
      query: query.trim(),
      solution_code: showCodeInput && solutionCode.trim() ? solutionCode.trim() : null,
      mode,
      k: Number(k) || 12,
      per_platform_min: Number(perPlatformMin) || 3,
      platform: platform || null,
    })
  }

  const applyPreset = (preset) => {
    setQuery(preset.query)
    if (preset.mode) setMode(preset.mode)
    if (preset.platform !== undefined) setPlatform(preset.platform || '')
  }

  return (
    <div className="search-panel-card">
      <form onSubmit={handleSubmit}>
        {/* Top bar with mode selector */}
        <div className="search-mode-tabs">
          <button
            type="button"
            className={`mode-tab ${mode === 'both' ? 'active' : ''}`}
            onClick={() => setMode('both')}
            title="Combines abstract problem reduction and concrete implementation methods"
          >
            <SparklesIcon size={16} />
            <span>Hybrid Match (Concept + Method)</span>
            <span className="tab-pill">Recommended</span>
          </button>
          <button
            type="button"
            className={`mode-tab ${mode === 'concept' ? 'active' : ''}`}
            onClick={() => setMode('concept')}
            title="Matches based on the pure abstract mathematical structure and reduction"
          >
            <BrainIcon size={16} />
            <span>Concept Only</span>
          </button>
          <button
            type="button"
            className={`mode-tab ${mode === 'method' ? 'active' : ''}`}
            onClick={() => setMode('method')}
            title="Matches based on exact algorithmic techniques, DP state signatures & primitives"
          >
            <KeyIcon size={16} />
            <span>Method Only</span>
          </button>
        </div>

        {/* Dedicated Platform Input */}
        <div className="platform-input-section">
          <div className="platform-input-header">
            <label className="input-label">
              Platform Selection
            </label>
            <span className="platform-input-hint">
              Target a specific platform contest style or problem source
            </span>
          </div>
          <div className="platform-button-group">
            <button
              type="button"
              className={`platform-btn-pill ${platform === '' ? 'active auto' : ''}`}
              onClick={() => setPlatform('')}
            >
              <span className="platform-dot auto-dot" />
              <span>All / Auto-Detect</span>
            </button>
            <button
              type="button"
              className={`platform-btn-pill ${platform === 'leetcode' ? 'active leetcode' : ''}`}
              onClick={() => setPlatform('leetcode')}
            >
              <span className="platform-dot lc-dot" />
              <span>LeetCode</span>
            </button>
            <button
              type="button"
              className={`platform-btn-pill ${platform === 'codeforces' ? 'active codeforces' : ''}`}
              onClick={() => setPlatform('codeforces')}
            >
              <span className="platform-dot cf-dot" />
              <span>Codeforces</span>
            </button>
            <button
              type="button"
              className={`platform-btn-pill ${platform === 'atcoder' ? 'active atcoder' : ''}`}
              onClick={() => setPlatform('atcoder')}
            >
              <span className="platform-dot ac-dot" />
              <span>AtCoder</span>
            </button>
          </div>
        </div>

        {/* Main query input */}
        <div className="query-input-section">
          <label htmlFor="problem-query" className="input-label">
            Problem Identifier, URL, or Statement
          </label>
          <div className="query-textarea-wrapper">
            <textarea
              id="problem-query"
              rows={6}
              className="query-textarea"
              placeholder="e.g. https://leetcode.com/problems/course-schedule-ii/  or  cf:1388/D&#10;or paste the full problem statement text..."
              value={query}
              onChange={(e) => handleQueryChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
                  handleSubmit(e)
                }
              }}
            />
          </div>
          <div className="input-helper-row">
            <span className="helper-hint">
              Supports LeetCode, Codeforces, AtCoder URLs, IDs, or raw text statements. Press <kbd>Ctrl+Enter</kbd> to search.
            </span>
            {query && (
              <button
                type="button"
                className="clear-btn"
                onClick={() => setQuery('')}
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Presets Row */}
        <div className="presets-row">
          <span className="presets-label">Quick Presets:</span>
          <div className="preset-buttons">
            {PRESETS.map((p, idx) => (
              <button
                key={idx}
                type="button"
                className="preset-btn"
                onClick={() => applyPreset(p)}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Optional AC Code Toggle */}
        <div className="code-toggle-section">
          <button
            type="button"
            className={`code-toggle-btn ${showCodeInput ? 'active' : ''}`}
            onClick={() => setShowCodeInput(!showCodeInput)}
          >
            <CodeIcon size={16} />
            <span>
              {showCodeInput
                ? 'Hide Accepted Solution Code'
                : '+ Add Accepted Solution Code (Exact Method Extraction)'}
            </span>
          </button>

          {showCodeInput && (
            <div className="code-input-wrapper">
              <div className="code-input-header">
                <span className="code-input-title">Your Accepted (AC) Code</span>
                <span className="code-input-tag">
                  Extracts exact state transitions & primitives from your implementation
                </span>
              </div>
              <textarea
                rows={12}
                className="code-textarea font-mono"
                placeholder="// Paste your C++, Python, or Java solution here...&#10;def solve():&#10;    # DP, Graph, or data structure implementation"
                value={solutionCode}
                onChange={(e) => setSolutionCode(e.target.value)}
              />
            </div>
          )}
        </div>

        {/* Advanced Filters Accordion - Icon removed as requested */}
        <div className="advanced-section">
          <button
            type="button"
            className="advanced-toggle"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <span className="advanced-toggle-title">Advanced Retrieval Parameters</span>
            <ChevronDownIcon
              size={16}
              className={`chevron-icon transition-transform ${showAdvanced ? 'rotate-180' : ''}`}
            />
          </button>

          {showAdvanced && (
            <div className="advanced-grid">
              <div className="field-group">
                <label className="field-label">
                  Total Results (<span className="text-accent">{k}</span>)
                </label>
                <input
                  type="range"
                  min="3"
                  max="30"
                  step="3"
                  value={k}
                  onChange={(e) => setK(Number(e.target.value))}
                  className="range-slider"
                />
                <div className="range-marks">
                  <span>6</span>
                  <span>12</span>
                  <span>18</span>
                  <span>24</span>
                  <span>30</span>
                </div>
              </div>

              <div className="field-group">
                <label className="field-label">
                  Min per Platform (<span className="text-accent">{perPlatformMin}</span>)
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  step="1"
                  value={perPlatformMin}
                  onChange={(e) => setPerPlatformMin(Number(e.target.value))}
                  className="range-slider"
                />
                <span className="field-subtext">
                  Ensures balanced practice across LeetCode, CF & AtCoder
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Action Button */}
        <div className="search-action-row">
          <button
            type="submit"
            className={`search-submit-btn ${isLoading ? 'loading' : ''}`}
            disabled={!query.trim() || isLoading}
          >
            {isLoading ? (
              <>
                <span className="spinner" />
                <span>Distilling & Matching Problems...</span>
              </>
            ) : (
              <>
                <SearchIcon size={18} className="search-btn-icon" />
                <span>
                  Find Similar Problems {platform ? `on ${platform.toUpperCase()}` : '(All Platforms)'}
                </span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

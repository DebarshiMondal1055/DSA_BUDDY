import React, { useState, useMemo } from 'react'
import { ExternalLinkIcon, KeyIcon, SearchIcon, FilterIcon } from './Icons'

export default function PracticeLadderView({ ladder, methodKey, onSearchSimilar }) {
  const [platformFilter, setPlatformFilter] = useState('all')
  const [searchFilter, setSearchFilter] = useState('')

  // Calculate platform counts & difficulty range
  const { counts, minDiff, maxDiff } = useMemo(() => {
    const c = { leetcode: 0, codeforces: 0, atcoder: 0 }
    let minD = Infinity
    let maxD = -Infinity

    if (ladder) {
      ladder.forEach((p) => {
        const plat = (p.platform || '').toLowerCase()
        if (c[plat] !== undefined) c[plat]++
        const diff = p.difficulty
        if (diff !== null && diff !== undefined && diff >= 0) {
          if (diff < minD) minD = diff
          if (diff > maxD) maxD = diff
        }
      })
    }

    return {
      counts: c,
      minDiff: minD === Infinity ? 'N/A' : minD,
      maxDiff: maxD === -Infinity ? 'N/A' : maxD,
    }
  }, [ladder])

  // Filtered list
  const filteredList = useMemo(() => {
    if (!ladder) return []
    return ladder.filter((p) => {
      if (platformFilter !== 'all' && (p.platform || '').toLowerCase() !== platformFilter) {
        return false
      }
      if (searchFilter.trim()) {
        const query = searchFilter.toLowerCase()
        const titleMatch = (p.title || '').toLowerCase().includes(query)
        const idMatch = (p.problem_id || '').toLowerCase().includes(query)
        const methodMatch = (p.method_keys || []).some((m) => m.toLowerCase().includes(query))
        if (!titleMatch && !idMatch && !methodMatch) return false
      }
      return true
    })
  }, [ladder, platformFilter, searchFilter])

  if (!ladder || ladder.length === 0) {
    return (
      <div className="empty-results-box">
        <h3>No practice problems found</h3>
        <p>No indexed problems found matching method key <code>{methodKey}</code>. Try another technique or widen the difficulty range.</p>
      </div>
    )
  }

  return (
    <div className="ladder-view-container">
      {/* Ladder Header */}
      <div className="ladder-header-card">
        <div className="ladder-header-info">
          <div className="ladder-tag-row">
            <span className="ladder-badge">
              <KeyIcon className="w-3.5 h-3.5" />
              Practice Ladder
            </span>
            <span className="ladder-method-name font-mono">{methodKey}</span>
          </div>
          <h2 className="ladder-title">
            Difficulty-Ranked Skill Ladder
          </h2>
          <p className="ladder-desc">
            Hand-curated practice progression from easiest to hardest to build muscle memory for <strong>{methodKey}</strong>.
          </p>

          <div className="ladder-stats-row">
            <span className="ladder-stat-item">
              Difficulty Spread: <strong>{minDiff} &rarr; {maxDiff}</strong>
            </span>
            <span className="ladder-stat-item">
              Total Problems: <strong>{ladder.length}</strong>
            </span>
            <div className="ladder-platform-breakdown">
              <span className="stat-chip lc">LC: {counts.leetcode}</span>
              <span className="stat-chip cf">CF: {counts.codeforces}</span>
              <span className="stat-chip ac">AC: {counts.atcoder}</span>
            </div>
          </div>
        </div>

        {/* Filter controls */}
        <div className="ladder-filter-bar">
          <div className="filter-input-wrapper">
            <SearchIcon size={14} className="filter-search-icon" />
            <input
              type="text"
              placeholder="Filter ladder problems..."
              className="filter-search-input"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
            />
          </div>

          <div className="select-wrapper">
            <FilterIcon size={14} className="select-icon" />
            <select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
              className="filter-select"
            >
              <option value="all">All Platforms ({ladder.length})</option>
              <option value="leetcode">LeetCode ({counts.leetcode})</option>
              <option value="codeforces">Codeforces ({counts.codeforces})</option>
              <option value="atcoder">AtCoder ({counts.atcoder})</option>
            </select>
          </div>
        </div>
      </div>

      {/* Problems List */}
      <div className="ladder-problems-list">
        {filteredList.map((p, idx) => {
          const plat = (p.platform || 'unknown').toLowerCase()
          return (
            <div key={p.problem_id || idx} className={`ladder-row-card ${plat}-border`}>
              <div className="ladder-row-step">
                <span className="step-num">#{idx + 1}</span>
                <span className={`platform-badge ${plat}`}>{p.platform}</span>
                <span className="problem-id-tag font-mono">{p.problem_id}</span>
              </div>

              <div className="ladder-row-main">
                <h4 className="ladder-problem-title">
                  {p.url ? (
                    <a
                      href={p.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="problem-link"
                    >
                      <span>{p.title}</span>
                      <ExternalLinkIcon className="link-icon" />
                    </a>
                  ) : (
                    <span>{p.title}</span>
                  )}
                </h4>

                <div className="ladder-method-keys">
                  {(p.method_keys || []).map((mk, kIdx) => (
                    <span key={kIdx} className="mini-method-tag font-mono">
                      {mk}
                    </span>
                  ))}
                </div>
              </div>

              <div className="ladder-row-right">
                <div className="difficulty-pill-box">
                  <span className="diff-label">Difficulty</span>
                  <span className={`diff-value ${plat}-diff font-mono`}>
                    {p.difficulty !== null && p.difficulty !== undefined && p.difficulty >= 0
                      ? p.difficulty
                      : 'Unrated'}
                  </span>
                </div>

                <div className="ladder-action-buttons">
                  {p.url && (
                    <a
                      href={p.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ladder-primary-btn"
                    >
                      <span>Solve</span>
                      <ExternalLinkIcon size={12} />
                    </a>
                  )}

                  {onSearchSimilar && (
                    <button
                      type="button"
                      className="ladder-secondary-btn"
                      onClick={() => onSearchSimilar(p.url || p.title, p.platform)}
                      title="Search for twins and similar problems to this one"
                    >
                      <SearchIcon size={12} />
                      <span>Twins</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

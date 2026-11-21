import React, { useState, useMemo } from 'react'
import ProblemCard from './ProblemCard'
import { FilterIcon, SearchIcon } from './Icons'

export default function ResultsList({ results, onSelectMethod }) {
  const [platformFilter, setPlatformFilter] = useState('all')
  const [sortOrder, setSortOrder] = useState('relevance')
  const [searchFilter, setSearchFilter] = useState('')

  // Compute platform distribution
  const platformCounts = useMemo(() => {
    const counts = { leetcode: 0, codeforces: 0, atcoder: 0, total: results?.length || 0 }
    if (!results) return counts
    results.forEach((r) => {
      const p = (r.platform || '').toLowerCase()
      if (counts[p] !== undefined) counts[p]++
    })
    return counts
  }, [results])

  // Filter and sort problems
  const filteredProblems = useMemo(() => {
    if (!results) return []

    let list = results.filter((p) => {
      // Platform filter
      if (platformFilter !== 'all' && (p.platform || '').toLowerCase() !== platformFilter) {
        return false
      }
      // Text search filter
      if (searchFilter.trim()) {
        const query = searchFilter.toLowerCase()
        const titleMatch = (p.title || '').toLowerCase().includes(query)
        const idMatch = (p.problem_id || '').toLowerCase().includes(query)
        const whyMatch = (p.why || '').toLowerCase().includes(query)
        const methodMatch = (p.method_keys || []).some((m) => m.toLowerCase().includes(query))
        const tagMatch = (p.concept_tags || []).some((t) => t.toLowerCase().includes(query))
        if (!titleMatch && !idMatch && !whyMatch && !methodMatch && !tagMatch) {
          return false
        }
      }
      return true
    })

    // Sorting
    if (sortOrder === 'diff-asc') {
      list = [...list].sort((a, b) => (a.difficulty ?? 99999) - (b.difficulty ?? 99999))
    } else if (sortOrder === 'diff-desc') {
      list = [...list].sort((a, b) => (b.difficulty ?? -1) - (a.difficulty ?? -1))
    }

    return list
  }, [results, platformFilter, searchFilter, sortOrder])

  if (!results || results.length === 0) {
    return (
      <div className="empty-results-box">
        <h3>No similar problems found</h3>
        <p>Try searching with another problem URL or pasting the complete problem statement.</p>
      </div>
    )
  }

  return (
    <div className="results-container">
      {/* Results Header & Summary */}
      <div className="results-header-bar">
        <div className="results-summary">
          <h2 className="results-title">
            Recommended Problem Matches{' '}
            <span className="results-count-pill">{filteredProblems.length} of {results.length}</span>
          </h2>
          <div className="platform-stats-row">
            <span className="stat-chip lc">LeetCode: {platformCounts.leetcode}</span>
            <span className="stat-chip cf">Codeforces: {platformCounts.codeforces}</span>
            <span className="stat-chip ac">AtCoder: {platformCounts.atcoder}</span>
          </div>
        </div>

        {/* Filter & Sort Controls */}
        <div className="results-controls">
          <div className="filter-input-wrapper">
            <SearchIcon size={14} className="filter-search-icon" />
            <input
              type="text"
              placeholder="Filter by keyword, tag, or method..."
              className="filter-search-input"
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
            />
            {searchFilter && (
              <button
                type="button"
                className="clear-search-btn"
                onClick={() => setSearchFilter('')}
              >
                ✕
              </button>
            )}
          </div>

          <div className="dropdowns-group">
            <div className="select-wrapper">
              <FilterIcon className="select-icon" />
              <select
                value={platformFilter}
                onChange={(e) => setPlatformFilter(e.target.value)}
                className="filter-select"
              >
                <option value="all">All Platforms ({results.length})</option>
                <option value="leetcode">LeetCode ({platformCounts.leetcode})</option>
                <option value="codeforces">Codeforces ({platformCounts.codeforces})</option>
                <option value="atcoder">AtCoder ({platformCounts.atcoder})</option>
              </select>
            </div>

            <div className="select-wrapper">
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value)}
                className="filter-select"
              >
                <option value="relevance">Sort: Similarity / Rerank</option>
                <option value="diff-asc">Difficulty: Low to High</option>
                <option value="diff-desc">Difficulty: High to Low</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Grid of Problem Cards */}
      {filteredProblems.length === 0 ? (
        <div className="no-matches-box">
          <p>No problems match your current filters. Try resetting the filters or search term.</p>
          <button
            type="button"
            className="reset-filters-btn"
            onClick={() => {
              setPlatformFilter('all')
              setSearchFilter('')
            }}
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="problems-grid">
          {filteredProblems.map((problem, index) => (
            <ProblemCard
              key={problem.problem_id || index}
              rank={index + 1}
              problem={problem}
              onSelectMethod={onSelectMethod}
            />
          ))}
        </div>
      )}
    </div>
  )
}

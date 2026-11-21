import React, { useState, useEffect } from 'react'
import { fetchLadder } from '../services/api'
import { ExternalLinkIcon, KeyIcon } from './Icons'

export default function LadderModal({ methodKey, onClose }) {
  const [ladder, setLadder] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!methodKey) return
    let ignore = false

    fetchLadder(methodKey, null, 15)
      .then((data) => {
        if (!ignore) {
          setLadder(Array.isArray(data) ? data : data?.data || [])
        }
      })
      .catch((err) => {
        if (!ignore) {
          console.error('Failed to load ladder:', err)
          setError(err.message || 'Failed to load practice ladder.')
        }
      })
      .finally(() => {
        if (!ignore) {
          setLoading(false)
        }
      })

    return () => {
      ignore = true
    }
  }, [methodKey])

  if (!methodKey) return null

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-header-left">
            <KeyIcon className="w-5 h-5 text-accent" />
            <div>
              <h3 className="modal-title">Practice Ladder: {methodKey}</h3>
              <p className="modal-subtitle">
                Problems sorted easiest-first across platforms to master this technique
              </p>
            </div>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="modal-loading">
              <span className="spinner" />
              <span>Fetching ladder problems for {methodKey}...</span>
            </div>
          ) : error ? (
            <div className="modal-error">
              <p>{error}</p>
            </div>
          ) : ladder.length === 0 ? (
            <div className="modal-empty">
              <p>No indexed problems found for method key: <code>{methodKey}</code></p>
            </div>
          ) : (
            <div className="ladder-table-wrapper">
              <table className="ladder-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Platform</th>
                    <th>Problem</th>
                    <th>Difficulty</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {ladder.map((p, idx) => (
                    <tr key={p.problem_id || idx}>
                      <td className="font-mono text-muted">{idx + 1}</td>
                      <td>
                        <span className={`platform-badge ${(p.platform || '').toLowerCase()}`}>
                          {p.platform}
                        </span>
                      </td>
                      <td className="font-semibold">{p.title || p.problem_id}</td>
                      <td className="font-mono">{p.difficulty ?? 'N/A'}</td>
                      <td>
                        {p.url && (
                          <a
                            href={p.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="ladder-solve-btn"
                          >
                            <span>Solve</span>
                            <ExternalLinkIcon className="w-3 h-3" />
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

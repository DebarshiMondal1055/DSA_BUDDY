import React from 'react'
import { BrainIcon, RefreshIcon } from './Icons'

export default function Navbar({ backendOnline, checkingHealth, onCheckHealth }) {
  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="brand">
          <div className="brand-icon-wrapper">
            <BrainIcon className="brand-icon" />
          </div>
          <div className="brand-text">
            <div className="brand-title-row">
              <h1 className="brand-title">DSA Buddy</h1>
              <span className="badge-pill v2-badge">v2.0 Neural</span>
            </div>
            <p className="brand-subtitle">
              Semantic & Algorithmic Problem Recommender across <span className="highlight-lc">LeetCode</span>, <span className="highlight-cf">Codeforces</span> & <span className="highlight-ac">AtCoder</span>
            </p>
          </div>
        </div>

        <div className="navbar-actions">
          <div className={`status-pill ${backendOnline ? 'online' : 'offline'}`}>
            <span className={`status-dot ${backendOnline ? 'pulse' : ''}`} />
            <span className="status-label">
              {backendOnline ? 'Backend Online (Port 8000)' : 'Backend Offline'}
            </span>
            <button
              type="button"
              className="refresh-status-btn"
              onClick={onCheckHealth}
              disabled={checkingHealth}
              title="Ping backend health (/health)"
            >
              <RefreshIcon className={`w-3.5 h-3.5 ${checkingHealth ? 'spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}

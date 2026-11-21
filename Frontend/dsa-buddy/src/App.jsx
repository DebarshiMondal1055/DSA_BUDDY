import React, { useState, useEffect, useCallback } from 'react'
import Navbar from './components/Navbar'
import SearchPanel from './components/SearchPanel'
import SourceAnalysisCard from './components/SourceAnalysisCard'
import ResultsList from './components/ResultsList'
import LoadingState from './components/LoadingState'
import LadderModal from './components/LadderModal'
import { checkHealth, searchSimilar } from './services/api'
import { AlertCircleIcon } from './components/Icons'
import './App.css'

export default function App() {
  const [backendOnline, setBackendOnline] = useState(false)
  const [checkingHealth, setCheckingHealth] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [ladderMethodKey, setLadderMethodKey] = useState(null)

  // Check health on mount and provide refresh capability
  const handleCheckHealth = useCallback(async () => {
    setCheckingHealth(true)
    try {
      const ok = await checkHealth()
      setBackendOnline(ok)
    } finally {
      setCheckingHealth(false)
    }
  }, [])

  useEffect(() => {
    let ignore = false
    checkHealth().then((ok) => {
      if (!ignore) setBackendOnline(ok)
    })
    const interval = setInterval(() => {
      checkHealth().then((ok) => {
        if (!ignore) setBackendOnline(ok)
      })
    }, 30000)
    return () => {
      ignore = true
      clearInterval(interval)
    }
  }, [])

  // Handle Search Submission
  const handleSearch = async (queryPayload) => {
    setIsLoading(true)
    setError(null)

    try {
      const res = await searchSimilar(queryPayload)
      setData(res)
    } catch (err) {
      console.error('Search error:', err)
      setError(
        err.message ||
          'Failed to retrieve similar problems. Ensure your backend is running at http://localhost:8000.'
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="app-layout">
      {/* Navbar with Backend Health Indicator */}
      <Navbar
        backendOnline={backendOnline}
        checkingHealth={checkingHealth}
        onCheckHealth={handleCheckHealth}
      />

      <main className="main-content">
        {/* Backend offline warning banner if unreachable */}
        {!backendOnline && (
          <div className="backend-offline-banner">
            <AlertCircleIcon className="w-5 h-5 text-amber" />
            <div className="offline-text">
              <strong>Backend connection not detected at http://localhost:8000</strong>
              <span>
                Run <code>uvicorn app:app --reload --port 8000</code> in your terminal to start the FastAPI server.
              </span>
            </div>
            <button
              type="button"
              className="retry-health-btn"
              onClick={handleCheckHealth}
              disabled={checkingHealth}
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Hero Banner */}
        <div className="hero-section">
          <h2 className="hero-headline">
            Find the <span className="gradient-text">Algorithmic Twin</span> to Any Problem
          </h2>
          <p className="hero-description">
            Never get stuck again. Enter any LeetCode, Codeforces, or AtCoder problem (or paste your statement and AC code) to discover identically structured problems across competitive programming platforms.
          </p>
        </div>

        {/* Search & Query Input Panel */}
        <SearchPanel onSearch={handleSearch} isLoading={isLoading} />

        {/* Error Notification */}
        {error && (
          <div className="error-alert">
            <AlertCircleIcon className="w-5 h-5 flex-shrink-0" />
            <div className="error-content">
              <h4>Retrieval Failed</h4>
              <p>{error}</p>
            </div>
            <button
              type="button"
              className="error-dismiss-btn"
              onClick={() => setError(null)}
            >
              ✕
            </button>
          </div>
        )}

        {/* Loading Progress State */}
        {isLoading && <LoadingState />}

        {/* Results Section */}
        {!isLoading && data && (
          <div className="results-wrapper">
            {/* Analyzed Source Problem Details (Concept + Method Cards) */}
            {data.source && <SourceAnalysisCard source={data.source} />}

            {/* List of Recommended Similar Problems */}
            <ResultsList
              results={data.results}
              onSelectMethod={(methodKey) => setLadderMethodKey(methodKey)}
            />
          </div>
        )}

        {/* Practice Ladder Modal */}
        {ladderMethodKey && (
          <LadderModal
            methodKey={ladderMethodKey}
            onClose={() => setLadderMethodKey(null)}
          />
        )}
      </main>

      <footer className="footer">
        <div className="footer-content">
          <p>
            <strong>DSA Buddy</strong> &bull; Powered by Qdrant, BM25, Sentence-Transformers & LLM Distillation
          </p>
          <div className="footer-links">
            <span className="dot-sep">&bull;</span>
            <span>Covering LeetCode, Codeforces & AtCoder</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

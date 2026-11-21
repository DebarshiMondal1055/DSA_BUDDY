import React, { useState, useEffect } from 'react'
import { SparklesIcon, BrainIcon, KeyIcon, LayersIcon } from './Icons'

const PIPELINE_STEPS = [
  { icon: BrainIcon, label: 'Resolving problem & statement...' },
  { icon: SparklesIcon, label: 'Distilling Concept & Method Cards...' },
  { icon: LayersIcon, label: 'Dense Vector & BM25 Reciprocal Rank Fusion...' },
  { icon: KeyIcon, label: 'Cross-Encoder (BAAI/bge-reranker) reranking...' },
  { icon: SparklesIcon, label: 'Synthesizing comparative AI explanations...' },
]

export default function LoadingState() {
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStep((prev) => (prev < PIPELINE_STEPS.length - 1 ? prev + 1 : prev))
    }, 2500)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="loading-card">
      <div className="loading-spinner-wrapper">
        <div className="pulsing-halo" />
        <div className="inner-spinner" />
      </div>

      <h3 className="loading-title">Finding Similar Algorithmic Problems</h3>
      <p className="loading-subtitle">
        Analyzing problem invariants, state structures, and indexing across platforms...
      </p>

      <div className="pipeline-steps">
        {PIPELINE_STEPS.map((step, idx) => {
          const StepIcon = step.icon
          const isDone = idx < currentStep
          const isCurrent = idx === currentStep
          return (
            <div
              key={idx}
              className={`pipeline-step ${isDone ? 'done' : ''} ${isCurrent ? 'active' : ''}`}
            >
              <div className="step-indicator">
                {isDone ? '✓' : <StepIcon className="w-3 h-3" />}
              </div>
              <span className="step-label">{step.label}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

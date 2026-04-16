import React, { useState, useEffect, useRef } from 'react'
import InputCard from './components/InputCard'
import ScoreRing from './components/ScoreRing'
import DimensionCard from './components/DimensionCard'
import FlagsPanel from './components/FlagsPanel'
import ExportButton from './components/ExportButton'

const API_BASE = ''  // proxied via Vite to http://localhost:8004

const SCAN_STEPS = [
  'Fetching manifest…',
  'Resolving domains…',
  'Checking threat intelligence…',
  'Analyzing with Gemini AI…',
  'Calculating trust score…',
  'Finalizing report…',
]

const DIMENSION_ORDER = [
  'identity',
  'permission_sprawl',
  'network_behavior',
  'code_transparency',
  'version_drift',
  'community_signal',
]

function getRatingColor(rating) {
  if (rating === 'High') return 'text-success border-success/30 bg-success/10'
  if (rating === 'Medium') return 'text-warning border-warning/30 bg-warning/10'
  if (rating === 'Low') return 'text-orange-400 border-orange-500/30 bg-orange-500/10'
  return 'text-danger border-danger/30 bg-danger/10'
}

function getRatingDot(rating) {
  if (rating === 'High') return 'bg-success'
  if (rating === 'Medium') return 'bg-warning'
  if (rating === 'Low') return 'bg-orange-400'
  return 'bg-danger'
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit', timeZoneName: 'short',
    })
  } catch {
    return iso
  }
}

// Progress bar component
function ScanProgress({ step, total }) {
  const pct = Math.round(((step + 1) / total) * 100)
  return (
    <div className="w-full h-1 bg-surface rounded-full overflow-hidden">
      <div
        className="h-full bg-accent rounded-full transition-all duration-700 ease-out"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

// ── KOI SHARED NAV HEADER ────────────────────────────────────────────────────
function KoiHeader() {
  const navLinks = [
    { label: 'Blast Radius', href: '#', active: false },
    { label: 'Behavior Baseline', href: '#', active: false },
    { label: 'Code Provenance', href: '#', active: false },
    { label: 'MCP Scorecard', href: '#', active: true },
  ]

  return (
    <header
      className="w-full border-b"
      style={{ background: '#0D1220', borderColor: '#1F2937' }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
        {/* Left: Koi branding */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-lg leading-none select-none">🐟</span>
          <span className="text-xs font-500 text-muted whitespace-nowrap tracking-wide">
            Koi Security Extensions
          </span>
        </div>

        {/* Center: Current app name */}
        <div className="hidden sm:flex items-center">
          <span className="text-sm font-600 text-white tracking-wide">
            MCP Trust Scorecard
          </span>
        </div>

        {/* Right: nav links */}
        <nav className="flex items-center gap-1 sm:gap-2">
          {navLinks.map((link) => (
            <a
              key={link.label}
              href={link.href}
              className={`px-2 sm:px-3 py-1.5 rounded-lg text-xs font-500 transition-all duration-200 whitespace-nowrap
                ${link.active
                  ? 'bg-accent/15 text-accent border border-accent/30'
                  : 'text-muted hover:text-white hover:bg-surface'
                }`}
            >
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  )
}

export default function App() {
  const [phase, setPhase] = useState('idle') // idle | scanning | results | error
  const [stepIndex, setStepIndex] = useState(0)
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)
  const stepTimer = useRef(null)

  // Cycle through scan steps during loading
  useEffect(() => {
    if (phase !== 'scanning') {
      clearInterval(stepTimer.current)
      return
    }
    setStepIndex(0)
    stepTimer.current = setInterval(() => {
      setStepIndex((i) => Math.min(i + 1, SCAN_STEPS.length - 1))
    }, 900)
    return () => clearInterval(stepTimer.current)
  }, [phase])

  const handleScan = async (url, manifest) => {
    setError(null)
    setPhase('scanning')
    setStepIndex(0)

    try {
      const body = {}
      if (url) body.url = url
      if (manifest) body.manifest = manifest

      const res = await fetch(`${API_BASE}/scan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `Server error ${res.status}`)
      }

      const data = await res.json()
      setResults(data)
      setPhase('results')
    } catch (err) {
      setError(err.message || 'Scan failed. Is the backend running?')
      setPhase('idle')
    }
  }

  const handleReset = () => {
    setPhase('idle')
    setResults(null)
    setError(null)
  }

  // ── IDLE ────────────────────────────────────────────────────────────────────
  if (phase === 'idle') {
    return (
      <div className="min-h-screen flex flex-col">
        <KoiHeader />
        <div className="flex-1 flex flex-col items-center justify-center px-4 py-16">
          <InputCard onScan={handleScan} error={error} />
          <p className="mt-8 text-xs text-muted text-center max-w-sm">
            Integrates with{' '}
            <span className="text-accent">Palo Alto Networks Prisma AIRS</span> and{' '}
            <span className="text-accent">Cortex XDR</span>
          </p>
        </div>
      </div>
    )
  }

  // ── SCANNING ────────────────────────────────────────────────────────────────
  if (phase === 'scanning') {
    return (
      <div className="min-h-screen flex flex-col">
        <KoiHeader />
        <div className="flex-1 flex flex-col items-center justify-center px-4">
          <div className="w-full max-w-sm flex flex-col items-center gap-8">
            {/* Animated shield */}
            <div className="relative">
              <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
                <path d="M40 10L65 22V42C65 56 54 68 40 72C26 68 15 56 15 42V22L40 10Z"
                  fill="#00D4FF" fillOpacity="0.08" stroke="#00D4FF" strokeWidth="1.5"/>
                <path d="M40 20L58 29.5V43C58 52.5 50 61 40 64C30 61 22 52.5 22 43V29.5L40 20Z"
                  fill="#00D4FF" fillOpacity="0.05" stroke="#00D4FF" strokeWidth="1" strokeOpacity="0.5"/>
                <circle cx="40" cy="43" r="8" stroke="#00D4FF" strokeWidth="1.5" strokeDasharray="3 3">
                  <animateTransform attributeName="transform" attributeType="XML" type="rotate"
                    from="0 40 43" to="360 40 43" dur="3s" repeatCount="indefinite"/>
                </circle>
                <path d="M36 43L39 46L44 40" stroke="#00FF9C" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <animate attributeName="opacity" values="0.3;1;0.3" dur="1.5s" repeatCount="indefinite"/>
                </path>
              </svg>
            </div>

            <div className="w-full flex flex-col gap-3">
              <ScanProgress step={stepIndex} total={SCAN_STEPS.length} />
              <p className="text-sm font-500 text-center text-accent animate-pulse-slow">
                {SCAN_STEPS[stepIndex]}
              </p>
            </div>

            <div className="flex flex-col gap-2 w-full">
              {SCAN_STEPS.map((step, i) => (
                <div key={i} className={`flex items-center gap-2.5 text-xs transition-all duration-300
                  ${i < stepIndex ? 'text-muted' : i === stepIndex ? 'text-white' : 'text-border'}`}>
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 transition-all duration-300
                    ${i < stepIndex ? 'bg-success' : i === stepIndex ? 'bg-accent animate-pulse' : 'bg-border'}`}/>
                  {step}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── RESULTS ─────────────────────────────────────────────────────────────────
  if (phase === 'results' && results) {
    const ratingClass = getRatingColor(results.trust_rating)
    const dotClass = getRatingDot(results.trust_rating)

    return (
      <div className="min-h-screen flex flex-col">
        <KoiHeader />
        <div className="flex-1 px-4 py-10">
          <div className="max-w-3xl mx-auto flex flex-col gap-6" id="results-view">

            {/* Header */}
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex items-center gap-3">
                <svg width="32" height="32" viewBox="0 0 40 40" fill="none">
                  <rect width="40" height="40" rx="10" fill="#00D4FF" fillOpacity="0.12"/>
                  <path d="M20 8L32 14.5V25.5L20 32L8 25.5V14.5L20 8Z" stroke="#00D4FF" strokeWidth="1.5" fill="none"/>
                  <path d="M17 20L19.5 22.5L23.5 18" stroke="#00FF9C" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                <div>
                  <h1 className="text-base font-700 text-white">MCP Trust Scorecard</h1>
                  {results.source_url && (
                    <p className="text-xs text-muted truncate max-w-xs">{results.source_url}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <ExportButton targetId="results-view" />
                <button
                  onClick={handleReset}
                  className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg bg-surface border border-border text-sm font-500 text-muted hover:text-white hover:border-accent/50 transition-all duration-200"
                >
                  <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                    <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd"/>
                  </svg>
                  New Scan
                </button>
              </div>
            </div>

            {/* Score Hero */}
            <div className="bg-card card-border rounded-2xl p-8 flex flex-col sm:flex-row items-center gap-8">
              <ScoreRing score={results.overall_score} />
              <div className="flex flex-col gap-4 flex-1 text-center sm:text-left">
                <div>
                  <p className="text-xs text-muted uppercase tracking-widest mb-2">Trust Rating</p>
                  <div className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full border text-lg font-700 ${ratingClass}`}>
                    <div className={`w-2 h-2 rounded-full ${dotClass}`} />
                    {results.trust_rating}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3 text-left">
                  <div className="bg-surface rounded-lg px-3 py-2.5">
                    <p className="text-xs text-muted mb-0.5">Overall Score</p>
                    <p className="text-lg font-700 text-white">{results.overall_score}<span className="text-sm text-muted font-400">/100</span></p>
                  </div>
                  <div className="bg-surface rounded-lg px-3 py-2.5">
                    <p className="text-xs text-muted mb-0.5">AI Suspicion</p>
                    <p className="text-lg font-700 text-white">{results.suspicion_score ?? '—'}<span className="text-sm text-muted font-400">/100</span></p>
                  </div>
                </div>
                <p className="text-xs text-muted">
                  Scanned {formatDate(results.scanned_at)}
                </p>
              </div>
            </div>

            {/* Dimension Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {DIMENSION_ORDER.map((dim, i) =>
                results.dimensions?.[dim] ? (
                  <DimensionCard
                    key={dim}
                    dimension={dim}
                    data={results.dimensions[dim]}
                    index={i}
                  />
                ) : null
              )}
            </div>

            {/* Flags */}
            <FlagsPanel flags={results.flags || []} />

            {/* Gemini Summary */}
            {results.gemini_summary && (
              <div className="bg-card card-border rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-accent flex-shrink-0">
                    <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
                  </svg>
                  <h3 className="text-sm font-600 text-white tracking-wide">Gemini AI Analysis</h3>
                </div>
                <p className="text-sm text-muted leading-relaxed">{results.gemini_summary}</p>
                {results.permission_analysis && (
                  <div className="mt-3 pt-3 border-t border-border">
                    <p className="text-xs text-muted font-500 mb-1 uppercase tracking-wide">Permission Analysis</p>
                    <p className="text-xs text-muted leading-relaxed">{results.permission_analysis}</p>
                  </div>
                )}
              </div>
            )}

            {/* Footer note */}
            <p className="text-xs text-muted text-center pb-4">
              Designed to integrate with{' '}
              <span className="text-accent">Palo Alto Networks Prisma AIRS</span> and{' '}
              <span className="text-accent">Cortex XDR</span>
            </p>
          </div>
        </div>
      </div>
    )
  }

  return null
}

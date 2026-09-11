import React, { useState, useCallback } from 'react'
import AgentInput from './components/AgentInput.jsx'
import BlastMap from './components/BlastMap.jsx'
import NodePanel from './components/NodePanel.jsx'
import RiskLegend from './components/RiskLegend.jsx'
import ExportButton from './components/ExportButton.jsx'
import RiskSummary from './components/RiskSummary.jsx'

// ─── Shared Header ────────────────────────────────────────────────────────────

function Header() {
  const navItems = [
    { label: 'Blast Radius', href: '#', current: true },
    { label: 'Behavior Baseline', href: '#', current: false },
    { label: 'Code Provenance', href: '#', current: false },
    { label: 'MCP Scorecard', href: '#', current: false },
  ]

  return (
    <header className="relative z-50 flex items-center justify-between px-6 h-14 border-b border-border bg-card/80 backdrop-blur-md shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2.5 min-w-0">
        <span className="text-xl leading-none select-none">🐠</span>
        <span className="text-sm font-semibold text-white whitespace-nowrap">
          Agent Trust Platform
        </span>
      </div>

      {/* App name — centered */}
      <div className="absolute left-1/2 -translate-x-1/2 flex flex-col items-center">
        <span className="text-sm font-bold tracking-wide text-accent text-glow-accent">
          Blast Radius Visualizer
        </span>
      </div>

      {/* Nav */}
      <nav className="flex items-center gap-1">
        {navItems.map((item) => (
          <a
            key={item.label}
            href={item.href}
            className={[
              'px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 whitespace-nowrap',
              item.current
                ? 'text-accent border border-accent/40 bg-accent/5 glow-accent-sm'
                : 'text-muted hover:text-white hover:bg-surface',
            ].join(' ')}
          >
            {item.label}
          </a>
        ))}
      </nav>
    </header>
  )
}

// ─── Scanning State ────────────────────────────────────────────────────────────

function AnalyzingState({ agentName }) {
  const steps = [
    'Mapping permission surface...',
    'Traversing integration graph...',
    'Calculating lateral movement paths...',
    'Scoring blast radius...',
    'Generating attack narrative...',
  ]

  const [step, setStep] = React.useState(0)

  React.useEffect(() => {
    const interval = setInterval(() => {
      setStep((s) => (s + 1) % steps.length)
    }, 900)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex flex-col items-center justify-center flex-1 gap-10 py-20">
      {/* Pulsing ring stack */}
      <div className="relative flex items-center justify-center">
        {/* Outer rings */}
        <div
          className="absolute rounded-full border border-accent/10"
          style={{ width: 240, height: 240, animation: 'scan-pulse 2.4s ease-in-out infinite 0.4s' }}
        />
        <div
          className="absolute rounded-full border border-accent/20"
          style={{ width: 180, height: 180, animation: 'scan-pulse 2s ease-in-out infinite 0.2s' }}
        />
        <div
          className="absolute rounded-full border border-accent/30"
          style={{ width: 130, height: 130, animation: 'scan-pulse 1.8s ease-in-out infinite' }}
        />
        {/* Core */}
        <div className="relative z-10 w-20 h-20 rounded-full border-2 border-accent glow-accent flex items-center justify-center">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <circle cx="14" cy="14" r="5" fill="#00D4FF" />
            <circle cx="14" cy="14" r="10" stroke="#00D4FF" strokeWidth="1.5" strokeDasharray="3 2" />
          </svg>
        </div>
      </div>

      {/* Status text */}
      <div className="flex flex-col items-center gap-2 text-center">
        <p className="text-lg font-semibold text-white">
          Analyzing <span className="text-accent">{agentName || 'Agent'}</span>
        </p>
        <p
          key={step}
          className="text-sm text-muted animate-fade-in"
          style={{ minHeight: '1.5rem' }}
        >
          {steps[step]}
        </p>
      </div>
    </div>
  )
}

// ─── Results Layout ────────────────────────────────────────────────────────────

function ResultsLayout({ data, onReset }) {
  const [selectedNode, setSelectedNode] = useState(null)

  return (
    <div id="blast-results" className="flex flex-col flex-1 min-h-0 relative">
      {/* Top bar with reset + export */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={onReset}
            className="text-xs text-muted hover:text-white transition-colors flex items-center gap-1.5"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 7C2 4.24 4.24 2 7 2c1.52 0 2.88.65 3.84 1.68L9.5 5H13V1.5L11.7 2.8C10.47 1.06 8.37 0 7 0 3.13 0 0 3.13 0 7h2zm10 0c0 2.76-2.24 5-5 5-1.52 0-2.88-.65-3.84-1.68L4.5 9H1v3.5l1.3-1.3C3.53 12.94 5.63 14 7 14c3.87 0 7-3.13 7-7h-2z" fill="#6B7A99" />
            </svg>
            New Analysis
          </button>
          <div className="w-px h-4 bg-border" />
          <span className="text-xs text-muted">
            Agent: <span className="text-white font-medium">{data.agent_name || 'Unknown'}</span>
          </span>
        </div>
        <ExportButton />
      </div>

      {/* Main content: graph + sidebar */}
      <div className="flex flex-1 min-h-0 relative">
        {/* Graph area */}
        <div className="flex-1 min-w-0 relative">
          <BlastMap
            nodes={data.nodes || []}
            edges={data.edges || []}
            onNodeClick={setSelectedNode}
          />
          <RiskLegend
            blastRating={data.blast_rating}
            overallScore={data.overall_score}
          />
        </div>

        {/* Right sidebar: Risk Summary */}
        <div className="w-80 shrink-0 border-l border-border overflow-y-auto bg-card/60 backdrop-blur-sm">
          <RiskSummary data={data} />
        </div>
      </div>

      {/* Node detail panel */}
      <NodePanel
        node={selectedNode}
        allNodes={data.nodes || []}
        edges={data.edges || []}
        narrative={data.attack_narrative || ''}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  )
}

// ─── App Root ──────────────────────────────────────────────────────────────────

export default function App() {
  const [state, setState] = useState('idle') // 'idle' | 'analyzing' | 'results'
  const [analysisData, setAnalysisData] = useState(null)
  const [error, setError] = useState(null)
  const [agentName, setAgentName] = useState('')

  const handleAnalyze = useCallback(async (formData) => {
    setError(null)
    setAgentName(formData.agent_name || 'Agent')
    setState('analyzing')

    try {
      const response = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })

      if (!response.ok) {
        let msg = `Server error (${response.status})`
        try {
          const errData = await response.json()
          if (errData.detail) msg = errData.detail
          else if (errData.message) msg = errData.message
        } catch {}
        throw new Error(msg)
      }

      const data = await response.json()
      setAnalysisData(data)
      setState('results')
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        setError('Cannot reach the backend server. Make sure the API is running on port 8001.')
      } else {
        setError(err.message || 'An unexpected error occurred.')
      }
      setState('idle')
    }
  }, [])

  const handleReset = useCallback(() => {
    setState('idle')
    setAnalysisData(null)
    setError(null)
  }, [])

  return (
    <div className="flex flex-col h-screen bg-bg font-sans overflow-hidden">
      <Header />

      {/* Grid pattern overlay */}
      {state !== 'results' && (
        <div className="fixed inset-0 grid-bg pointer-events-none opacity-60" />
      )}

      {/* Content */}
      {state === 'idle' && (
        <main className="flex flex-1 flex-col items-center justify-center px-4 py-10 relative z-10 overflow-y-auto">
          <div className="w-full max-w-xl animate-fade-in">
            {/* Hero heading */}
            <div className="mb-8 text-center">
              <div className="inline-flex items-center gap-2 mb-4 px-3 py-1.5 rounded-full border border-accent/20 bg-accent/5">
                <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                <span className="text-xs font-medium text-accent tracking-wide">AGENTIC RISK ANALYSIS</span>
              </div>
              <h1 className="text-3xl font-bold text-white mb-2">
                Blast Radius Visualizer
              </h1>
              <p className="text-sm text-muted leading-relaxed">
                Map the attack surface of AI agents — permissions, integrations, lateral movement paths, and compromise scenarios.
              </p>
            </div>

            {/* Error banner */}
            {error && (
              <div className="mb-4 p-4 rounded-lg border border-danger/30 bg-danger/10 text-danger text-sm flex items-start gap-2">
                <svg className="shrink-0 mt-0.5" width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                  <path d="M8 5v4M8 11v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                </svg>
                <span>{error}</span>
              </div>
            )}

            <AgentInput onSubmit={handleAnalyze} />
          </div>
        </main>
      )}

      {state === 'analyzing' && (
        <main className="flex flex-1 relative z-10">
          <AnalyzingState agentName={agentName} />
        </main>
      )}

      {state === 'results' && analysisData && (
        <main className="flex flex-1 min-h-0 relative z-10">
          <ResultsLayout data={analysisData} onReset={handleReset} />
        </main>
      )}
    </div>
  )
}

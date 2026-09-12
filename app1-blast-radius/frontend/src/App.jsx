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
    { label: 'Agent access', href: '#', current: true },
    { label: 'Behavior', href: '#', current: false },
    { label: 'Artifacts', href: '#', current: false },
    { label: 'Connectors', href: '#', current: false },
  ]

  return (
    <header className="relative z-50 flex items-center justify-between gap-5 px-5 sm:px-8 h-[4.25rem] border-b border-white/5 bg-bg/75 backdrop-blur-xl shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center justify-center w-9 h-9 rounded-xl border border-accent/30 bg-accent/10 shadow-[0_0_24px_rgba(0,212,255,0.14)]">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M10 2.25 16 4.5v4.64c0 3.78-2.46 6.78-6 8.61-3.54-1.83-6-4.83-6-8.61V4.5l6-2.25Z" stroke="currentColor" strokeWidth="1.35" className="text-accent" />
            <circle cx="10" cy="9" r="2" fill="currentColor" className="text-accent" />
            <path d="M10 11v2.4M7.7 9H6.2M13.8 9h-1.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" className="text-accent" />
          </svg>
        </div>
        <div className="min-w-0">
          <span className="block text-sm font-semibold text-white whitespace-nowrap tracking-tight">
            Agent Trust Platform
          </span>
          <span className="hidden sm:block text-[10px] uppercase tracking-[0.2em] text-muted/80">
            Local security workspace
          </span>
        </div>
      </div>

      {/* App name — centered */}
      <div className="hidden md:flex absolute left-1/2 -translate-x-1/2 flex-col items-center">
        <span className="text-[10px] uppercase tracking-[0.22em] text-muted/80">
          Workspace 02
        </span>
        <span className="text-sm font-semibold tracking-wide text-white">
          Agent Access / Blast Radius
        </span>
      </div>

      {/* Nav */}
      <nav className="flex items-center gap-1 overflow-x-auto max-w-[52%] sm:max-w-none scrollbar-none" aria-label="Security workspaces">
        {navItems.map((item) => (
          <a
            key={item.label}
            href={item.href}
            className={[
              'px-2.5 sm:px-3 py-1.5 rounded-lg text-[11px] sm:text-xs font-medium transition-all duration-150 whitespace-nowrap',
              item.current
                ? 'text-accent border border-accent/30 bg-accent/10 shadow-[0_0_18px_rgba(0,212,255,0.1)]'
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
        <main className="flex flex-1 items-center px-5 sm:px-8 py-10 relative z-10 overflow-y-auto">
          <div className="w-full max-w-6xl mx-auto animate-fade-in">
            <div className="grid lg:grid-cols-[0.9fr_1.1fr] gap-10 lg:gap-16 items-center">
              {/* Hero heading */}
              <section className="max-w-xl">
                <div className="inline-flex items-center gap-2 mb-5 px-3 py-1.5 rounded-full border border-accent/20 bg-accent/5">
                  <span className="relative flex w-2 h-2">
                    <span className="absolute inline-flex w-full h-full rounded-full bg-accent opacity-60 animate-ping" />
                    <span className="relative inline-flex w-2 h-2 rounded-full bg-accent" />
                  </span>
                  <span className="text-[11px] font-semibold text-accent tracking-[0.16em]">ASSESSMENT WORKSPACE</span>
                </div>
                <h1 className="text-4xl sm:text-5xl font-semibold tracking-[-0.04em] text-white leading-[1.05] mb-5">
                  See how far an agent can reach.
                </h1>
                <p className="text-base text-muted leading-relaxed max-w-lg">
                  Build a permission and integration graph, surface lateral movement paths, and review deterministic blast-radius findings before they become surprises.
                </p>

                <div className="flex flex-wrap gap-2 mt-7">
                  {['Permission-aware', 'Rules-first', 'Local by default'].map((label) => (
                    <span key={label} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-white/10 bg-white/[0.03] text-xs text-slate-300">
                      <span className="w-1.5 h-1.5 rounded-full bg-success" />
                      {label}
                    </span>
                  ))}
                </div>

                <div className="grid grid-cols-3 gap-3 mt-10 max-w-md">
                  <div className="border-l border-accent/40 pl-3">
                    <p className="text-lg font-semibold text-white">01</p>
                    <p className="text-[11px] text-muted mt-0.5">Map access</p>
                  </div>
                  <div className="border-l border-warning/40 pl-3">
                    <p className="text-lg font-semibold text-white">02</p>
                    <p className="text-[11px] text-muted mt-0.5">Score exposure</p>
                  </div>
                  <div className="border-l border-success/40 pl-3">
                    <p className="text-lg font-semibold text-white">03</p>
                    <p className="text-[11px] text-muted mt-0.5">Review paths</p>
                  </div>
                </div>
              </section>

              <section>
                {/* Error banner */}
                {error && (
                  <div className="mb-4 p-4 rounded-xl border border-danger/30 bg-danger/10 text-danger text-sm flex items-start gap-2">
                    <svg className="shrink-0 mt-0.5" width="16" height="16" viewBox="0 0 16 16" fill="none">
                      <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                      <path d="M8 5v4M8 11v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                    </svg>
                    <span>{error}</span>
                  </div>
                )}

                <div className="mb-3 flex items-center justify-between px-1">
                  <div>
                    <p className="text-sm font-semibold text-white">Start an assessment</p>
                    <p className="text-xs text-muted mt-1">Describe the agent’s declared access surface.</p>
                  </div>
                  <span className="hidden sm:inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-muted/70">
                    <span className="w-1.5 h-1.5 rounded-full bg-success" />
                    No key required
                  </span>
                </div>
                <AgentInput onSubmit={handleAnalyze} />
              </section>
            </div>
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

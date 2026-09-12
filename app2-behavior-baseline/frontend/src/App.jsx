import React, { useState, useEffect, useCallback } from 'react';
import AgentSelector from './components/AgentSelector.jsx';
import BaselineChart from './components/BaselineChart.jsx';
import AnomalyFeed from './components/AnomalyFeed.jsx';
import BehaviorTimeline from './components/BehaviorTimeline.jsx';
import AlertPanel from './components/AlertPanel.jsx';

export default function App() {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [baseline, setBaseline] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [summary, setSummary] = useState(null);
  const [agentData, setAgentData] = useState(null);
  const [alertDismissed, setAlertDismissed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch agents on mount
  useEffect(() => {
    async function loadAgents() {
      try {
        const res = await fetch('/agents');
        if (!res.ok) throw new Error(`Backend unavailable (${res.status})`);
        const data = await res.json();
        const agents = data.agents.map(a => ({...a, anomalyCount: a.anomaly_count, highestSeverity: a.critical_anomalies ? 'critical' : a.high_anomalies ? 'high' : null}));
        setAgents(agents);
        if (data.agents?.length || data.length) {
          setSelectedAgent(agents[0]);
        }
      } catch (err) {
        setError(err.message);
      }
      setLoading(false);
    }
    loadAgents();
  }, []);

  // Fetch agent-specific data when selection changes
  useEffect(() => {
    if (!selectedAgent) return;
    setAlertDismissed(false);

    let cancelled = false;
    async function loadAgentData() {
      setError(null);
      setBaseline(null); setAgentData(null); setSummary(null); setAnomalies([]);
      try {
        const id = encodeURIComponent(selectedAgent.id);
        const responses = await Promise.all(
          ['baseline', 'anomalies', 'summary', 'agent-data'].map(route => fetch(`/${route}/${id}`))
        );
        if (responses.some(r => !r.ok)) throw new Error('Backend unavailable — no substitute telemetry is shown.');
        const [bl, an, sm, ad] = await Promise.all(responses.map(r => r.json()));
        if (cancelled) return;
        const chart = Object.fromEntries(Object.entries(bl.metrics).map(([metric, stats]) =>
          [metric, ad.records.map((r, i) => ({ day: i + 1, value: r[metric], mean: stats.mean, std: stats.std_dev }))]));
        setBaseline(chart);
        setAnomalies(an.anomalies);
        setSummary({...sm, confidence: sm.confidence / 100, recommendedAction: sm.recommended_action});
        setAgentData(ad.records.slice(-7).map(r => Array.from({length: 24}, (_, h) => r.active_hours.includes(h) ? 1 : 0)));
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }
    loadAgentData();
    return () => { cancelled = true; };
  }, [selectedAgent]);

  const handleAgentSelect = useCallback((agent) => {
    setSelectedAgent(agent);
  }, []);

  const hasCritical = summary !== null && !alertDismissed;

  return (
    <div className="flex flex-col h-screen bg-bg text-white overflow-hidden">
      {/* ── Header ── */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-border bg-card flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🐠</span>
          <span className="text-sm font-semibold text-muted tracking-widest uppercase">
            Agent Trust Platform
          </span>
        </div>

        <div className="text-center">
          <h1 className="text-base font-semibold text-white tracking-tight">
            Behavior Baseline Monitor
          </h1>
          <p className="text-[10px] uppercase tracking-wider text-amber-300">
            Demo mode · seeded examples
          </p>
        </div>

        <nav className="flex items-center gap-1 text-xs font-medium">
          <a
            href="#"
            className="px-3 py-1.5 rounded text-muted hover:text-white transition-colors"
          >
            Blast Radius
          </a>
          <span className="text-border">|</span>
          <a
            href="#"
            className="px-3 py-1.5 rounded text-accent border border-accent/30 bg-accent/5"
          >
            Behavior Baseline
          </a>
          <span className="text-border">|</span>
          <a
            href="#"
            className="px-3 py-1.5 rounded text-muted hover:text-white transition-colors"
          >
            Code Provenance
          </a>
          <span className="text-border">|</span>
          <a
            href="#"
            className="px-3 py-1.5 rounded text-muted hover:text-white transition-colors"
          >
            MCP Scorecard
          </a>
        </nav>
      </header>

      {/* ── Body ── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <aside className="w-64 border-r border-border bg-card flex-shrink-0 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            </div>
          ) : (
            <AgentSelector
              agents={agents}
              selectedAgent={selectedAgent}
              onSelect={handleAgentSelect}
            />
          )}
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto bg-bg p-4 space-y-4">
          {error && <p role="alert">{error}</p>}
          {summary && <p role="note">Analysis source: {summary.source}; hosted provider unavailable unless explicitly configured. Confidence is a heuristic, not a calibrated probability.</p>}
          {/* Alert panel */}
          {hasCritical && summary && (
            <AlertPanel
              summary={summary}
              onDismiss={() => setAlertDismissed(true)}
            />
          )}

          {/* Top row: chart + anomaly feed */}
          <div className="grid grid-cols-3 gap-4">
            <div className="col-span-2">
              <BaselineChart baseline={baseline} anomalies={anomalies} agentId={selectedAgent?.id} />
            </div>
            <div className="col-span-1">
              <AnomalyFeed anomalies={anomalies} />
            </div>
          </div>

          {/* Bottom row: behavior timeline */}
          <div>
            <BehaviorTimeline agentData={agentData} agentId={selectedAgent?.id} />
          </div>
        </main>
      </div>
    </div>
  );
}

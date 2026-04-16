import React, { useState, useEffect, useCallback, useRef } from 'react';
import AgentSelector from './components/AgentSelector.jsx';
import BaselineChart from './components/BaselineChart.jsx';
import AnomalyFeed from './components/AnomalyFeed.jsx';
import BehaviorTimeline from './components/BehaviorTimeline.jsx';
import AlertPanel from './components/AlertPanel.jsx';

/* ─── Mock data generators ─────────────────────────────────────── */
function generateMockAgents() {
  return [
    { id: 'agent-001', name: 'CodeGen Assistant', type: 'code', anomalyCount: 3, highestSeverity: 'critical' },
    { id: 'agent-002', name: 'Data Pipeline Bot', type: 'data', anomalyCount: 1, highestSeverity: 'high' },
    { id: 'agent-003', name: 'Auth Service Agent', type: 'auth', anomalyCount: 0, highestSeverity: null },
    { id: 'agent-004', name: 'ML Inference Runner', type: 'ml', anomalyCount: 2, highestSeverity: 'medium' },
    { id: 'agent-005', name: 'Document Indexer', type: 'index', anomalyCount: 0, highestSeverity: null },
  ];
}

function generateMockBaseline(agentId) {
  const metrics = {
    api_call_rate: { mean: 45, std: 8 },
    file_access_count: { mean: 120, std: 20 },
    execution_time_ms: { mean: 350, std: 60 },
    credential_accesses: { mean: 5, std: 2 },
  };
  const days = Array.from({ length: 30 }, (_, i) => i + 1);
  const data = {};
  for (const [metric, { mean, std }] of Object.entries(metrics)) {
    data[metric] = days.map((day) => {
      const noise = (Math.random() - 0.5) * std * 2;
      let value = mean + noise;
      // Simulate anomalies in last 3 days for agents with issues
      if (day >= 28 && (agentId === 'agent-001' || agentId === 'agent-002')) {
        value = mean + std * (2 + Math.random() * 2);
      }
      return { day, value: Math.max(0, value), mean, std };
    });
  }
  return data;
}

function generateMockAnomalies(agentId) {
  if (agentId === 'agent-001') {
    return [
      {
        id: `${agentId}-a1`,
        severity: 'critical',
        type: 'DataExfiltration',
        description: 'Credential access rate 4.2σ above baseline — possible exfiltration pattern',
        timestamp: new Date(Date.now() - 120000).toISOString(),
        metric: 'credential_accesses',
        delta: '+312%',
      },
      {
        id: `${agentId}-a2`,
        severity: 'high',
        type: 'AbnormalAPIPattern',
        description: 'API call burst to /export endpoints detected outside working hours',
        timestamp: new Date(Date.now() - 480000).toISOString(),
        metric: 'api_call_rate',
        delta: '+187%',
      },
      {
        id: `${agentId}-a3`,
        severity: 'medium',
        type: 'FileAccessSpike',
        description: 'Unusual file access pattern across /config directories',
        timestamp: new Date(Date.now() - 3600000).toISOString(),
        metric: 'file_access_count',
        delta: '+95%',
      },
    ];
  } else if (agentId === 'agent-002') {
    return [
      {
        id: `${agentId}-a1`,
        severity: 'high',
        type: 'LateralMovement',
        description: 'Cross-service authentication attempts detected from agent context',
        timestamp: new Date(Date.now() - 900000).toISOString(),
        metric: 'api_call_rate',
        delta: '+240%',
      },
    ];
  } else if (agentId === 'agent-004') {
    return [
      {
        id: `${agentId}-a1`,
        severity: 'medium',
        type: 'PerformanceDrift',
        description: 'Execution time gradually increasing — possible resource exhaustion',
        timestamp: new Date(Date.now() - 7200000).toISOString(),
        metric: 'execution_time_ms',
        delta: '+68%',
      },
      {
        id: `${agentId}-a2`,
        severity: 'low',
        type: 'BenignDrift',
        description: 'Slight increase in API usage consistent with model warm-up',
        timestamp: new Date(Date.now() - 18000000).toISOString(),
        metric: 'api_call_rate',
        delta: '+22%',
      },
    ];
  }
  return [];
}

function generateMockSummary(agentId) {
  if (agentId === 'agent-001') {
    return {
      classification: 'DataExfiltration',
      confidence: 0.91,
      recommended_action: 'Isolate agent and rotate credentials immediately',
      explanation:
        'Agent is exhibiting a classic data exfiltration pattern: credential access spike followed by high-volume API calls to export endpoints during off-hours. This combination has a 91% match to known exfiltration TTPs.',
    };
  } else if (agentId === 'agent-002') {
    return {
      classification: 'LateralMovement',
      confidence: 0.78,
      recommended_action: 'Restrict cross-service permissions and audit recent auth logs',
      explanation:
        'Cross-service authentication attempts suggest the agent is attempting to access resources outside its authorized scope. Pattern is consistent with lateral movement post-compromise.',
    };
  }
  return null;
}

function generateMockAgentData(agentId) {
  // Heatmap data: 7 days x 24 hours
  const data = Array.from({ length: 7 }, (_, dayIdx) =>
    Array.from({ length: 24 }, (_, hour) => {
      const isWorkHour = hour >= 8 && hour < 20;
      const isBadAgent = agentId === 'agent-001' || agentId === 'agent-002';
      if (!isWorkHour && isBadAgent && Math.random() < 0.3) {
        return Math.floor(Math.random() * 3) + 2; // medium to high during off-hours
      }
      if (isWorkHour) {
        return Math.floor(Math.random() * 3) + 1; // low to high
      }
      return Math.random() < 0.1 ? 1 : 0; // mostly inactive off-hours
    })
  );
  return data;
}

/* ─── Simulated new anomaly generator ──────────────────────────── */
let anomalyCounter = 100;
function generateLiveAnomaly(agentId) {
  const types = ['APIBurst', 'FileAccessSpike', 'CredentialProbe', 'AbnormalTiming'];
  const severities = ['low', 'medium', 'high'];
  const deltas = ['+18%', '+34%', '+67%', '+112%'];
  anomalyCounter++;
  return {
    id: `live-${agentId}-${anomalyCounter}`,
    severity: severities[Math.floor(Math.random() * severities.length)],
    type: types[Math.floor(Math.random() * types.length)],
    description: 'Live telemetry anomaly detected in behavioral stream',
    timestamp: new Date().toISOString(),
    metric: 'api_call_rate',
    delta: deltas[Math.floor(Math.random() * deltas.length)],
    isNew: true,
  };
}

/* ─── App ───────────────────────────────────────────────────────── */
export default function App() {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [baseline, setBaseline] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [summary, setSummary] = useState(null);
  const [agentData, setAgentData] = useState(null);
  const [alertDismissed, setAlertDismissed] = useState(false);
  const [loading, setLoading] = useState(true);
  const liveIntervalRef = useRef(null);

  // Fetch agents on mount
  useEffect(() => {
    async function loadAgents() {
      try {
        const res = await fetch('/agents');
        if (!res.ok) throw new Error('mock');
        const data = await res.json();
        setAgents(data.agents || data);
        if (data.agents?.length || data.length) {
          setSelectedAgent((data.agents || data)[0]);
        }
      } catch {
        const mock = generateMockAgents();
        setAgents(mock);
        setSelectedAgent(mock[0]);
      }
      setLoading(false);
    }
    loadAgents();
  }, []);

  // Fetch agent-specific data when selection changes
  useEffect(() => {
    if (!selectedAgent) return;
    setAlertDismissed(false);

    async function loadAgentData() {
      try {
        const [baselineRes, anomaliesRes, summaryRes, dataRes] = await Promise.allSettled([
          fetch(`/baseline?agent_id=${selectedAgent.id}`),
          fetch(`/anomalies?agent_id=${selectedAgent.id}`),
          fetch(`/summary?agent_id=${selectedAgent.id}`),
          fetch(`/agent-data?agent_id=${selectedAgent.id}`),
        ]);

        const bl =
          baselineRes.status === 'fulfilled' && baselineRes.value.ok
            ? await baselineRes.value.json()
            : generateMockBaseline(selectedAgent.id);

        const an =
          anomaliesRes.status === 'fulfilled' && anomaliesRes.value.ok
            ? await anomaliesRes.value.json()
            : generateMockAnomalies(selectedAgent.id);

        const sm =
          summaryRes.status === 'fulfilled' && summaryRes.value.ok
            ? await summaryRes.value.json()
            : generateMockSummary(selectedAgent.id);

        const ad =
          dataRes.status === 'fulfilled' && dataRes.value.ok
            ? await dataRes.value.json()
            : generateMockAgentData(selectedAgent.id);

        setBaseline(bl);
        setAnomalies(Array.isArray(an) ? an : an.anomalies || []);
        setSummary(sm);
        setAgentData(ad);
      } catch {
        setBaseline(generateMockBaseline(selectedAgent.id));
        setAnomalies(generateMockAnomalies(selectedAgent.id));
        setSummary(generateMockSummary(selectedAgent.id));
        setAgentData(generateMockAgentData(selectedAgent.id));
      }
    }
    loadAgentData();
  }, [selectedAgent]);

  // Live anomaly simulation every 5 seconds
  useEffect(() => {
    if (liveIntervalRef.current) clearInterval(liveIntervalRef.current);
    if (!selectedAgent) return;

    liveIntervalRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/anomalies?agent_id=${selectedAgent.id}&live=true`);
        if (!res.ok) throw new Error('mock');
        const data = await res.json();
        const newItems = (Array.isArray(data) ? data : data.anomalies || []).map((a) => ({
          ...a,
          isNew: true,
        }));
        if (newItems.length > 0) {
          setAnomalies((prev) => [...newItems, ...prev.map((a) => ({ ...a, isNew: false }))]);
        }
      } catch {
        // Only inject a simulated anomaly occasionally
        if (Math.random() < 0.3) {
          const live = generateLiveAnomaly(selectedAgent.id);
          setAnomalies((prev) => [live, ...prev.map((a) => ({ ...a, isNew: false }))]);
        }
      }
    }, 5000);

    return () => clearInterval(liveIntervalRef.current);
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
            Koi Security Extensions
          </span>
        </div>

        <div className="text-center">
          <h1 className="text-base font-semibold text-white tracking-tight">
            Behavior Baseline Monitor
          </h1>
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

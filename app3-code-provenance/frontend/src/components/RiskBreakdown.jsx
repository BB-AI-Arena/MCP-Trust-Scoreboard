import React, { useEffect, useState } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';

const RISK_CONFIG = [
  { key: 'safe',     label: 'Safe',     color: '#00FF9C' },
  { key: 'low',      label: 'Low',      color: '#00AA66' },
  { key: 'medium',   label: 'Medium',   color: '#FFB800' },
  { key: 'high',     label: 'High',     color: '#FF4444' },
  { key: 'critical', label: 'Critical', color: '#FF0066' },
];

function buildChartData(files) {
  const counts = { safe: 0, low: 0, medium: 0, high: 0, critical: 0 };
  (files || []).forEach((f) => {
    const risk = (f.risk_level || 'low').toLowerCase();
    if (risk in counts) counts[risk]++;
    else counts.low++;
  });
  return RISK_CONFIG
    .map((r) => ({ ...r, value: counts[r.key] }))
    .filter((r) => r.value > 0);
}

function getMostCommonModel(files) {
  const tally = {};
  (files || []).forEach((f) => {
    const m = f.provenance?.model || 'Unknown';
    tally[m] = (tally[m] || 0) + 1;
  });
  return Object.entries(tally).sort((a, b) => b[1] - a[1])[0]?.[0] || '—';
}

function getHighestRiskFile(files) {
  const order = { critical: 0, high: 1, medium: 2, low: 3, safe: 4 };
  const sorted = [...(files || [])].sort(
    (a, b) => (order[a.risk_level] ?? 5) - (order[b.risk_level] ?? 5)
  );
  return sorted[0]?.filename?.split('/').pop() || '—';
}

function countAiGenerated(files) {
  const ai = (files || []).filter(
    (f) => f.provenance?.model && f.provenance.model !== 'Human'
  ).length;
  return files?.length ? Math.round((ai / files.length) * 100) : 0;
}

// Custom donut label
function renderCustomLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent, name }) {
  if (percent < 0.05) return null;
  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text
      x={x}
      y={y}
      fill="rgba(255,255,255,0.8)"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={10}
      fontFamily="Inter, sans-serif"
      fontWeight="600"
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
}

// Custom tooltip
function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { label, value, color } = payload[0].payload;
  return (
    <div className="bg-surface border border-border rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full" style={{ background: color }} />
        <span className="text-white font-medium">{label}</span>
        <span className="text-muted ml-1">{value} file{value !== 1 ? 's' : ''}</span>
      </div>
    </div>
  );
}

export default function RiskBreakdown({ results }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 100);
    return () => clearTimeout(t);
  }, []);

  const files = results?.files || (results && [results]) || [];
  const chartData = buildChartData(files);
  const totalFiles = files.length;
  const aiPct = countAiGenerated(files);
  const topModel = getMostCommonModel(files);
  const highestRiskFile = getHighestRiskFile(files);

  const statsCards = [
    { label: 'Total Files', value: String(totalFiles), color: '#00D4FF' },
    { label: 'AI-Generated', value: `${aiPct}%`, color: '#7C3AED' },
    { label: 'Top Model', value: topModel, color: '#F59E0B', small: true },
    { label: 'Highest Risk File', value: highestRiskFile, color: '#FF4444', small: true },
  ];

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-border">
        <h2 className="font-semibold text-sm text-white">Risk Distribution</h2>
      </div>

      <div className="flex-1 p-5 flex flex-col gap-5">
        {/* Donut chart */}
        {chartData.length > 0 ? (
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={2}
                  dataKey="value"
                  labelLine={false}
                  label={renderCustomLabel}
                  isAnimationActive={mounted}
                  animationBegin={0}
                  animationDuration={800}
                >
                  {chartData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} stroke="transparent" />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex items-center justify-center h-[180px] text-muted text-sm">
            No risk data
          </div>
        )}

        {/* Legend pills */}
        <div className="flex flex-wrap gap-2 justify-center">
          {RISK_CONFIG.map(({ key, label, color }) => {
            const d = chartData.find((c) => c.key === key);
            if (!d) return null;
            return (
              <div
                key={key}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs"
                style={{ background: `${color}18`, border: `1px solid ${color}30` }}
              >
                <span className="w-2 h-2 rounded-full" style={{ background: color }} />
                <span style={{ color }}>{label}</span>
                <span className="text-white/60 ml-0.5">{d.value}</span>
              </div>
            );
          })}
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 gap-3">
          {statsCards.map(({ label, value, color, small }) => (
            <div
              key={label}
              className="bg-surface rounded-lg px-3 py-3 border border-border/50"
            >
              <div className="text-xs text-muted mb-1">{label}</div>
              <div
                className={`font-bold leading-tight ${small ? 'text-sm' : 'text-xl'} truncate`}
                style={{ color }}
              >
                {value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

import React, { useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ReferenceArea,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Legend,
  ComposedChart,
  Area,
} from 'recharts';

const METRICS = [
  { key: 'api_call_rate', label: 'API Call Rate', unit: 'calls/min' },
  { key: 'file_access_count', label: 'File Access Count', unit: 'files' },
  { key: 'execution_time_ms', label: 'Execution Time', unit: 'ms' },
  { key: 'credential_accesses', label: 'Credential Accesses', unit: 'ops' },
];

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;

  const d = payload[0]?.payload;
  if (!d) return null;

  const deviation = d.mean > 0 ? (((d.value - d.mean) / d.mean) * 100).toFixed(1) : 0;
  const isAnomaly = d.value > d.mean + d.std * 2;

  return (
    <div
      className="rounded-lg border p-3 text-xs shadow-xl"
      style={{ backgroundColor: '#111827', borderColor: '#1F2937', minWidth: 160 }}
    >
      <div className="font-semibold text-white mb-2">Day {label}</div>
      <div className="space-y-1">
        <div className="flex justify-between gap-4">
          <span style={{ color: '#6B7A99' }}>Current</span>
          <span style={{ color: isAnomaly ? '#FF4444' : '#00D4FF' }} className="font-mono font-bold">
            {d.value?.toFixed(1)}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span style={{ color: '#6B7A99' }}>Baseline</span>
          <span className="font-mono text-gray-300">{d.mean?.toFixed(1)}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span style={{ color: '#6B7A99' }}>Deviation</span>
          <span
            className="font-mono font-semibold"
            style={{ color: deviation > 0 ? '#FF4444' : '#00FF9C' }}
          >
            {deviation > 0 ? '+' : ''}{deviation}%
          </span>
        </div>
      </div>
      {isAnomaly && (
        <div
          className="mt-2 pt-2 border-t text-xs font-semibold"
          style={{ borderColor: '#1F2937', color: '#FF4444' }}
        >
          ⚠ Exceeds 2σ threshold
        </div>
      )}
    </div>
  );
}

function CustomLegend() {
  return (
    <div className="flex items-center gap-4 justify-center mt-2 text-xs">
      <div className="flex items-center gap-1.5">
        <span className="w-6 h-0.5 inline-block" style={{ backgroundColor: '#00D4FF' }} />
        <span style={{ color: '#6B7A99' }}>Current behavior</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span
          className="w-4 h-3 inline-block rounded-sm"
          style={{ backgroundColor: 'rgba(0,255,156,0.15)', border: '1px solid rgba(0,255,156,0.3)' }}
        />
        <span style={{ color: '#6B7A99' }}>Baseline ±1σ</span>
      </div>
      <div className="flex items-center gap-1.5">
        <span
          className="w-2 h-2 rounded-full inline-block"
          style={{ backgroundColor: '#FF4444' }}
        />
        <span style={{ color: '#6B7A99' }}>Anomaly point</span>
      </div>
    </div>
  );
}

export default function BaselineChart({ baseline, anomalies, agentId }) {
  const [selectedMetric, setSelectedMetric] = useState('api_call_rate');

  const chartData = useMemo(() => {
    if (!baseline || !baseline[selectedMetric]) return [];
    return baseline[selectedMetric];
  }, [baseline, selectedMetric]);

  const anomalyDays = useMemo(() => {
    if (!anomalies) return new Set();
    const days = new Set();
    // Map anomalies to days 28-30 for visualization
    anomalies.forEach((_, i) => {
      if (i < 3) days.add(28 + i);
    });
    return days;
  }, [anomalies]);

  const { yMin, yMax } = useMemo(() => {
    if (!chartData.length) return { yMin: 0, yMax: 100 };
    const vals = chartData.map((d) => d.value);
    const mean = chartData[0]?.mean || 0;
    const std = chartData[0]?.std || 0;
    const min = Math.min(...vals, mean - std * 2);
    const max = Math.max(...vals, mean + std * 2);
    const pad = (max - min) * 0.1;
    return { yMin: Math.max(0, min - pad), yMax: max + pad };
  }, [chartData]);

  const mean = chartData[0]?.mean || 0;
  const std = chartData[0]?.std || 0;
  const unitLabel = METRICS.find((m) => m.key === selectedMetric)?.unit || '';

  if (!baseline) {
    return (
      <div
        className="rounded-xl border p-6 flex items-center justify-center h-[600px]"
        style={{ backgroundColor: '#111827', borderColor: '#1F2937' }}
      >
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-3" style={{ borderColor: '#00D4FF', borderTopColor: 'transparent' }} />
          <p className="text-sm" style={{ color: '#6B7A99' }}>Loading baseline data…</p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl border p-4"
      style={{ backgroundColor: '#111827', borderColor: '#1F2937' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-semibold text-white">Behavior Baseline</h2>
          <p className="text-xs mt-0.5" style={{ color: '#6B7A99' }}>30-day behavioral profile</p>
        </div>

        {/* Metric selector */}
        <select
          value={selectedMetric}
          onChange={(e) => setSelectedMetric(e.target.value)}
          className="text-xs rounded-lg px-3 py-1.5 border appearance-none cursor-pointer"
          style={{
            backgroundColor: '#1A2235',
            borderColor: '#1F2937',
            color: '#E2E8F0',
            outline: 'none',
          }}
        >
          {METRICS.map((m) => (
            <option key={m.key} value={m.key}>
              {m.label}
            </option>
          ))}
        </select>
      </div>

      {/* Chart */}
      <div style={{ height: 480 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
            <defs>
              <linearGradient id="baselineBand" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00FF9C" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#00FF9C" stopOpacity={0.05} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="rgba(31,41,55,0.8)" />

            <XAxis
              dataKey="day"
              tickFormatter={(v) => `D${v}`}
              tick={{ fill: '#6B7A99', fontSize: 11 }}
              axisLine={{ stroke: '#1F2937' }}
              tickLine={false}
              interval={4}
            />

            <YAxis
              domain={[yMin, yMax]}
              tickFormatter={(v) => v.toFixed(0)}
              tick={{ fill: '#6B7A99', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              label={{
                value: unitLabel,
                angle: -90,
                position: 'insideLeft',
                fill: '#6B7A99',
                fontSize: 10,
                offset: 10,
              }}
            />

            <Tooltip
              content={<CustomTooltip />}
              cursor={{ stroke: 'rgba(0,212,255,0.3)', strokeWidth: 1 }}
            />

            {/* Baseline band: mean ± 1std */}
            <ReferenceArea
              y1={Math.max(0, mean - std)}
              y2={mean + std}
              fill="url(#baselineBand)"
              stroke="rgba(0,255,156,0.3)"
              strokeWidth={1}
              strokeDasharray="4 2"
            />

            {/* Mean reference line */}
            <ReferenceLine
              y={mean}
              stroke="rgba(0,255,156,0.5)"
              strokeDasharray="6 3"
              strokeWidth={1}
              label={{
                value: `μ ${mean.toFixed(0)}`,
                position: 'right',
                fill: 'rgba(0,255,156,0.7)',
                fontSize: 10,
              }}
            />

            {/* Current behavior line */}
            <Line
              type="monotone"
              dataKey="value"
              stroke="#00D4FF"
              strokeWidth={2}
              dot={(props) => {
                const { cx, cy, payload } = props;
                if (anomalyDays.has(payload.day)) {
                  return (
                    <circle
                      key={`dot-${payload.day}`}
                      cx={cx}
                      cy={cy}
                      r={5}
                      fill="#FF4444"
                      stroke="#FF4444"
                      strokeWidth={2}
                      opacity={0.9}
                    />
                  );
                }
                return (
                  <circle
                    key={`dot-${payload.day}`}
                    cx={cx}
                    cy={cy}
                    r={2.5}
                    fill="#00D4FF"
                    stroke="none"
                    opacity={0.7}
                  />
                );
              }}
              activeDot={{ r: 5, fill: '#00D4FF', stroke: '#111827', strokeWidth: 2 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <CustomLegend />
    </div>
  );
}

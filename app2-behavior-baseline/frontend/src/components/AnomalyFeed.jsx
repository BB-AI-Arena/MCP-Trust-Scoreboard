import React, { useRef, useEffect } from 'react';

const SEVERITY_CONFIG = {
  critical: {
    border: '#FF0066',
    bg: 'rgba(255,0,102,0.08)',
    badge: { bg: 'rgba(255,0,102,0.2)', text: '#FF0066' },
    label: 'CRITICAL',
  },
  high: {
    border: '#FF4444',
    bg: 'rgba(255,68,68,0.06)',
    badge: { bg: 'rgba(255,68,68,0.2)', text: '#FF4444' },
    label: 'HIGH',
  },
  medium: {
    border: '#FFB800',
    bg: 'rgba(255,184,0,0.06)',
    badge: { bg: 'rgba(255,184,0,0.2)', text: '#FFB800' },
    label: 'MEDIUM',
  },
  low: {
    border: '#00FF9C',
    bg: 'rgba(0,255,156,0.04)',
    badge: { bg: 'rgba(0,255,156,0.15)', text: '#00FF9C' },
    label: 'LOW',
  },
};

function formatTimestamp(iso) {
  const date = new Date(iso);
  const now = new Date();
  const diff = Math.floor((now - date) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return date.toLocaleDateString();
}

function AnomalyItem({ anomaly }) {
  const config = SEVERITY_CONFIG[anomaly.severity] || SEVERITY_CONFIG.low;

  return (
    <div
      className={anomaly.isNew ? 'anomaly-item-enter' : ''}
      style={{
        borderLeft: `3px solid ${config.border}`,
        backgroundColor: config.bg,
        padding: '10px 12px',
        borderRadius: '0 6px 6px 0',
        marginBottom: '6px',
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Severity badge */}
          <span
            className="text-xs font-bold px-1.5 py-0.5 rounded"
            style={{ backgroundColor: config.badge.bg, color: config.badge.text }}
          >
            {config.label}
          </span>
          {/* Type badge */}
          <span
            className="text-xs font-medium px-1.5 py-0.5 rounded"
            style={{ backgroundColor: 'rgba(107,122,153,0.2)', color: '#6B7A99' }}
          >
            {anomaly.type}
          </span>
        </div>
        {/* Delta */}
        {anomaly.delta && (
          <span
            className="text-xs font-bold font-mono flex-shrink-0"
            style={{ color: config.border }}
          >
            {anomaly.delta}
          </span>
        )}
      </div>

      <p className="text-xs text-gray-300 mt-1.5 leading-relaxed">
        {anomaly.description}
      </p>

      <div className="flex items-center justify-between mt-1.5">
        <span className="text-xs" style={{ color: '#6B7A99' }}>
          {anomaly.metric}
        </span>
        <span className="text-xs" style={{ color: '#6B7A99' }}>
          {formatTimestamp(anomaly.timestamp)}
        </span>
      </div>
    </div>
  );
}

export default function AnomalyFeed({ anomalies }) {
  const feedRef = useRef(null);

  return (
    <div
      className="rounded-xl border flex flex-col"
      style={{
        backgroundColor: '#111827',
        borderColor: '#1F2937',
        height: '100%',
        minHeight: 0,
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b flex-shrink-0"
        style={{ borderColor: '#1F2937' }}
      >
        <div>
          <h2 className="text-sm font-semibold text-white">Anomaly Feed</h2>
          <p className="text-xs mt-0.5" style={{ color: '#6B7A99' }}>
            {anomalies.length} detected
          </p>
        </div>

        {/* Live indicator */}
        <div className="flex items-center gap-1.5">
          <span
            className="w-2 h-2 rounded-full pulse-dot"
            style={{ backgroundColor: '#00FF9C' }}
          />
          <span className="text-xs font-medium" style={{ color: '#00FF9C' }}>
            LIVE
          </span>
        </div>
      </div>

      {/* Feed list */}
      <div
        ref={feedRef}
        className="flex-1 overflow-y-auto p-3"
        style={{ maxHeight: 460 }}
      >
        {anomalies.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-center">
            <div className="text-2xl mb-2">✓</div>
            <p className="text-xs font-medium" style={{ color: '#00FF9C' }}>
              No anomalies detected
            </p>
            <p className="text-xs mt-1" style={{ color: '#6B7A99' }}>
              Baseline behavior nominal
            </p>
          </div>
        ) : (
          anomalies.map((anomaly) => (
            <AnomalyItem key={anomaly.id} anomaly={anomaly} />
          ))
        )}
      </div>
    </div>
  );
}

import React from 'react';

const CLASSIFICATION_CONFIG = {
  DataExfiltration: {
    label: 'Data Exfiltration',
    bg: 'rgba(255,0,102,0.12)',
    border: '#FF0066',
    badge: { bg: 'rgba(255,0,102,0.25)', text: '#FF0066' },
    icon: '🚨',
    level: 'CRITICAL',
  },
  LateralMovement: {
    label: 'Lateral Movement',
    bg: 'rgba(255,68,68,0.1)',
    border: '#FF4444',
    badge: { bg: 'rgba(255,68,68,0.2)', text: '#FF4444' },
    icon: '⚠️',
    level: 'DANGER',
  },
  PrivilegeEscalation: {
    label: 'Privilege Escalation',
    bg: 'rgba(255,0,102,0.12)',
    border: '#FF0066',
    badge: { bg: 'rgba(255,0,102,0.25)', text: '#FF0066' },
    icon: '🚨',
    level: 'CRITICAL',
  },
  BenignDrift: {
    label: 'Benign Drift',
    bg: 'rgba(255,184,0,0.08)',
    border: '#FFB800',
    badge: { bg: 'rgba(255,184,0,0.2)', text: '#FFB800' },
    icon: '⚡',
    level: 'WARNING',
  },
};

function ConfidenceBar({ confidence }) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 85 ? '#FF4444' : pct >= 65 ? '#FFB800' : '#6B7A99';
  return (
    <div className="flex items-center gap-2">
      <div
        className="relative rounded-full overflow-hidden"
        style={{ width: 80, height: 6, backgroundColor: 'rgba(107,122,153,0.2)' }}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs font-bold font-mono" style={{ color }}>
        {pct}%
      </span>
    </div>
  );
}

export default function AlertPanel({ summary, onDismiss }) {
  if (!summary) return null;

  const config = CLASSIFICATION_CONFIG[summary.classification] || {
    label: summary.classification,
    bg: 'rgba(107,122,153,0.1)',
    border: '#6B7A99',
    badge: { bg: 'rgba(107,122,153,0.2)', text: '#6B7A99' },
    icon: '⚠️',
    level: 'ALERT',
  };

  return (
    <div
      className="alert-panel-enter rounded-xl border p-4"
      style={{
        backgroundColor: config.bg,
        borderColor: config.border,
        borderLeftWidth: 4,
      }}
    >
      <div className="flex items-start gap-4">
        {/* Icon + level */}
        <div className="flex-shrink-0 flex flex-col items-center gap-1 pt-0.5">
          <span className="text-xl">{config.icon}</span>
          <span
            className="text-xs font-bold tracking-widest"
            style={{ color: config.border }}
          >
            {config.level}
          </span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Top row: classification + confidence */}
          <div className="flex items-center gap-3 flex-wrap mb-2">
            <span
              className="text-sm font-bold px-2 py-0.5 rounded"
              style={{ backgroundColor: config.badge.bg, color: config.badge.text }}
            >
              {config.label}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-xs" style={{ color: '#6B7A99' }}>Confidence</span>
              <ConfidenceBar confidence={summary.confidence} />
            </div>
          </div>

          {/* Explanation */}
          <p className="text-xs leading-relaxed text-gray-300 mb-2">
            {summary.explanation}
          </p>

          {/* Recommended action */}
          <div
            className="flex items-start gap-2 rounded-lg p-2.5"
            style={{ backgroundColor: 'rgba(0,0,0,0.25)' }}
          >
            <span className="text-xs flex-shrink-0" style={{ color: '#6B7A99' }}>
              Recommended action:
            </span>
            <span className="text-xs font-semibold text-white">
              {summary.recommended_action}
            </span>
          </div>
        </div>

        {/* Dismiss button */}
        <button
          onClick={onDismiss}
          className="flex-shrink-0 w-6 h-6 rounded flex items-center justify-center transition-colors hover:bg-white/10"
          style={{ color: '#6B7A99' }}
          aria-label="Dismiss alert"
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <line x1="1" y1="1" x2="11" y2="11" />
            <line x1="11" y1="1" x2="1" y2="11" />
          </svg>
        </button>
      </div>
    </div>
  );
}

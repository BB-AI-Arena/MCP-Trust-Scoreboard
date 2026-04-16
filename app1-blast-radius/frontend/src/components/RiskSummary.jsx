import React, { useState } from 'react'

const BLAST_RATINGS = {
  Contained: { gradient: 'from-success/20 to-success/5', border: 'border-success/30', text: 'text-success', score_color: '#00FF9C' },
  Moderate: { gradient: 'from-warning/20 to-warning/5', border: 'border-warning/30', text: 'text-warning', score_color: '#FFB800' },
  Severe: { gradient: 'from-danger/20 to-danger/5', border: 'border-danger/30', text: 'text-danger', score_color: '#FF4444' },
  Catastrophic: { gradient: 'from-critical/20 to-critical/5', border: 'border-critical/30', text: 'text-critical', score_color: '#FF0066' },
}

const CRITICALITY_STYLES = {
  critical: 'text-critical bg-critical/10 border-critical/25',
  high: 'text-danger bg-danger/10 border-danger/25',
  medium: 'text-warning bg-warning/10 border-warning/25',
  low: 'text-success bg-success/10 border-success/25',
}

function ScoreRing({ score, color }) {
  const size = 96
  const strokeWidth = 6
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const progress = Math.min(Math.max(score || 0, 0), 100)
  const offset = circumference - (progress / 100) * circumference

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#1F2937"
          strokeWidth={strokeWidth}
        />
        {/* Progress */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ filter: `drop-shadow(0 0 6px ${color}80)`, transition: 'stroke-dashoffset 1s ease-out' }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-2xl font-extrabold text-white tabular-nums leading-none">{progress}</span>
        <span className="text-[10px] text-muted font-medium">/100</span>
      </div>
    </div>
  )
}

export default function RiskSummary({ data }) {
  const [checkedMitigations, setCheckedMitigations] = useState({})

  if (!data) return null

  const {
    overall_score,
    blast_rating,
    critical_nodes = [],
    attack_narrative = '',
    mitigations = [],
    agent_name,
    endpoint_type,
  } = data

  const ratingStyle = BLAST_RATINGS[blast_rating] || BLAST_RATINGS.Moderate
  const scoreColor = ratingStyle.score_color

  const toggleMitigation = (i) => {
    setCheckedMitigations((prev) => ({ ...prev, [i]: !prev[i] }))
  }

  // Parse attack narrative into paragraphs
  const narrativeParagraphs = (attack_narrative || '')
    .split(/\n\n+/)
    .filter(Boolean)
    .map((p) => p.trim())

  // Parse mitigations — could be array of strings or objects
  const mitigationList = mitigations.map((m) => {
    if (typeof m === 'string') return m
    if (m.description) return m.description
    if (m.text) return m.text
    return JSON.stringify(m)
  })

  return (
    <div className="flex flex-col gap-0">
      {/* Score header */}
      <div className={`p-5 border-b border-border bg-gradient-to-b ${ratingStyle.gradient}`}>
        <div className="flex items-center gap-4">
          <ScoreRing score={overall_score} color={scoreColor} />
          <div className="flex flex-col gap-1.5">
            <p className="text-xs text-muted font-medium">Risk Score</p>
            <span
              className={`inline-flex items-center px-3 py-1 rounded-lg border text-sm font-bold uppercase tracking-wide ${ratingStyle.border} ${ratingStyle.text}`}
              style={{ background: `${scoreColor}15` }}
            >
              {blast_rating || 'Unknown'}
            </span>
            {agent_name && (
              <p className="text-xs text-muted mt-1">
                <span className="text-white/70 font-medium">{agent_name}</span>
                {endpoint_type && <span className="ml-1 text-muted/60">· {endpoint_type}</span>}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Critical nodes */}
      {critical_nodes.length > 0 && (
        <div className="p-4 border-b border-border">
          <p className="text-xs font-semibold text-muted uppercase tracking-widest mb-3 flex items-center gap-1.5">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M6 1l1.5 3.5H11l-2.8 2.3 1 3.7L6 8.5 3 10.5l1-3.7L1 4.5h3.5z" fill="#FF0066" />
            </svg>
            Critical Nodes
            <span className="ml-1 text-white/40 font-normal">({critical_nodes.length})</span>
          </p>
          <div className="flex flex-col gap-2">
            {critical_nodes.map((node, i) => {
              const nodeId = typeof node === 'string' ? node : node.id || node.label || String(node)
              const criticality = typeof node === 'object' ? node.criticality : 'critical'
              const style = CRITICALITY_STYLES[criticality] || CRITICALITY_STYLES.critical
              return (
                <div
                  key={i}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium ${style}`}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-current opacity-80 shrink-0" />
                  <span className="font-mono truncate">{nodeId}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Attack narrative */}
      {attack_narrative && (
        <div className="p-4 border-b border-border">
          <p className="text-xs font-semibold text-muted uppercase tracking-widest mb-3 flex items-center gap-1.5">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M1 3h10M1 6h7M1 9h8" stroke="#6B7A99" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            Attack Narrative
          </p>
          <div className="flex flex-col gap-3">
            {narrativeParagraphs.length > 0
              ? narrativeParagraphs.map((para, i) => (
                  <p key={i} className="text-xs text-white/70 leading-relaxed">
                    {para}
                  </p>
                ))
              : (
                <p className="text-xs text-white/70 leading-relaxed">{attack_narrative}</p>
              )
            }
          </div>
        </div>
      )}

      {/* Mitigations */}
      {mitigationList.length > 0 && (
        <div className="p-4">
          <p className="text-xs font-semibold text-muted uppercase tracking-widest mb-3 flex items-center gap-1.5">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M6 1L10 3v3c0 2.5-2 4.5-4 5-2-0.5-4-2.5-4-5V3l4-2z" stroke="#00FF9C" strokeWidth="1.2" strokeLinejoin="round" />
              <path d="M4 6l1.5 1.5 3-3" stroke="#00FF9C" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Mitigations
            <span className="ml-1 text-white/40 font-normal">({mitigationList.length})</span>
          </p>
          <div className="flex flex-col gap-2">
            {mitigationList.map((mitigation, i) => {
              const checked = checkedMitigations[i] || false
              return (
                <label
                  key={i}
                  className="flex items-start gap-3 cursor-pointer group"
                  onClick={() => toggleMitigation(i)}
                >
                  {/* Number + checkbox hybrid */}
                  <div
                    className={[
                      'shrink-0 w-6 h-6 rounded-md border flex items-center justify-center text-[10px] font-bold mt-0.5 transition-all',
                      checked
                        ? 'bg-success/20 border-success/40 text-success'
                        : 'bg-surface border-border text-muted group-hover:border-accent/40',
                    ].join(' ')}
                  >
                    {checked ? (
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path d="M2 5l2.5 2.5 4.5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    ) : (
                      <span>{i + 1}</span>
                    )}
                  </div>
                  <span
                    className={[
                      'text-xs leading-relaxed pt-0.5 transition-colors',
                      checked ? 'text-muted line-through' : 'text-white/80 group-hover:text-white',
                    ].join(' ')}
                  >
                    {mitigation}
                  </span>
                </label>
              )
            })}
          </div>

          {/* Progress bar */}
          {mitigationList.length > 0 && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-muted">Remediation Progress</span>
                <span className="text-[10px] text-white/60 tabular-nums">
                  {Object.values(checkedMitigations).filter(Boolean).length}/{mitigationList.length}
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-surface overflow-hidden">
                <div
                  className="h-full rounded-full bg-success transition-all duration-500"
                  style={{
                    width: `${(Object.values(checkedMitigations).filter(Boolean).length / mitigationList.length) * 100}%`,
                    boxShadow: '0 0 8px rgba(0,255,156,0.5)',
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

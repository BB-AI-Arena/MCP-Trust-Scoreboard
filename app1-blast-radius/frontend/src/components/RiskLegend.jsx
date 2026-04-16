import React, { useState } from 'react'

const NODE_TYPES = [
  { label: 'Agent', color: '#00D4FF', key: 'agent' },
  { label: 'Critical', color: '#FF0066', key: 'critical' },
  { label: 'High', color: '#FF4444', key: 'high' },
  { label: 'Medium', color: '#FFB800', key: 'medium' },
  { label: 'Low', color: '#00FF9C', key: 'low' },
]

const EDGE_TYPES = [
  { label: 'Write Access', color: '#FF4444', key: 'WriteAccess' },
  { label: 'Read Access', color: '#00D4FF', key: 'ReadAccess' },
  { label: 'Execute Access', color: '#9B59B6', key: 'ExecuteAccess' },
  { label: 'Authenticate', color: '#FFB800', key: 'Authenticate' },
]

const BLAST_RATINGS = {
  Contained: { bg: 'bg-success/15 border-success/30', text: 'text-success', icon: '●' },
  Moderate: { bg: 'bg-warning/15 border-warning/30', text: 'text-warning', icon: '◆' },
  Severe: { bg: 'bg-danger/15 border-danger/30', text: 'text-danger', icon: '▲' },
  Catastrophic: { bg: 'bg-critical/15 border-critical/30', text: 'text-critical', icon: '⬟' },
}

export default function RiskLegend({ blastRating, overallScore }) {
  const [collapsed, setCollapsed] = useState(false)
  const ratingStyle = BLAST_RATINGS[blastRating] || BLAST_RATINGS.Moderate

  return (
    <div className="absolute bottom-4 left-4 z-30">
      <div
        className="rounded-xl border border-border overflow-hidden"
        style={{
          background: 'rgba(17, 24, 39, 0.88)',
          backdropFilter: 'blur(12px)',
          boxShadow: '0 4px 24px rgba(0,0,0,0.5)',
          minWidth: '200px',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-3 py-2 border-b border-border cursor-pointer select-none"
          onClick={() => setCollapsed((c) => !c)}
        >
          <span className="text-xs font-semibold text-muted uppercase tracking-widest">Legend</span>
          <svg
            width="12"
            height="12"
            viewBox="0 0 12 12"
            fill="none"
            className="transition-transform duration-200"
            style={{ transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}
          >
            <path d="M2 4l4 4 4-4" stroke="#6B7A99" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>

        {!collapsed && (
          <div className="p-3 flex flex-col gap-3">
            {/* Blast Rating */}
            {blastRating && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">Blast Rating</span>
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs font-bold uppercase tracking-wide ${ratingStyle.bg} ${ratingStyle.text}`}
                >
                  <span className="text-[10px]">{ratingStyle.icon}</span>
                  {blastRating}
                </span>
              </div>
            )}

            {overallScore !== undefined && overallScore !== null && (
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">Risk Score</span>
                <span className="text-xs font-bold text-white tabular-nums">{overallScore}/100</span>
              </div>
            )}

            {(blastRating || overallScore !== undefined) && (
              <div className="border-t border-border/50" />
            )}

            {/* Node types */}
            <div>
              <p className="text-[10px] font-semibold text-muted/70 uppercase tracking-widest mb-1.5">
                Node Colors
              </p>
              <div className="flex flex-col gap-1.5">
                {NODE_TYPES.map((nt) => (
                  <div key={nt.key} className="flex items-center gap-2">
                    <div className="flex items-center justify-center w-5 h-5">
                      <span
                        className="w-3 h-3 rounded-full border"
                        style={{
                          background: `${nt.color}25`,
                          borderColor: nt.color,
                          boxShadow: `0 0 6px ${nt.color}40`,
                        }}
                      />
                    </div>
                    <span className="text-xs text-white/80">{nt.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Edge types */}
            <div>
              <p className="text-[10px] font-semibold text-muted/70 uppercase tracking-widest mb-1.5">
                Edge Types
              </p>
              <div className="flex flex-col gap-1.5">
                {EDGE_TYPES.map((et) => (
                  <div key={et.key} className="flex items-center gap-2">
                    <svg width="20" height="10" viewBox="0 0 20 10" fill="none">
                      <line x1="1" y1="5" x2="14" y2="5" stroke={et.color} strokeWidth="1.5" strokeOpacity="0.8" />
                      <path d="M12 2l4 3-4 3" fill={et.color} fillOpacity="0.8" />
                    </svg>
                    <span className="text-xs text-white/80">{et.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

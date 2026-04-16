import React, { useEffect, useState } from 'react'

const NODE_COLORS = {
  critical: '#FF0066',
  high: '#FF4444',
  medium: '#FFB800',
  low: '#00FF9C',
  agent: '#00D4FF',
  default: '#6B7A99',
}

const EDGE_COLORS = {
  WriteAccess: '#FF4444',
  ReadAccess: '#00D4FF',
  ExecuteAccess: '#9B59B6',
  Authenticate: '#FFB800',
}

const TYPE_ICONS = {
  agent: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="4" fill="#00D4FF" />
      <circle cx="10" cy="10" r="8" stroke="#00D4FF" strokeWidth="1.5" strokeDasharray="3 2" />
    </svg>
  ),
  database: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <ellipse cx="10" cy="6" rx="7" ry="3" stroke="currentColor" strokeWidth="1.5" />
      <path d="M3 6v8c0 1.66 3.13 3 7 3s7-1.34 7-3V6" stroke="currentColor" strokeWidth="1.5" />
      <path d="M3 10c0 1.66 3.13 3 7 3s7-1.34 7-3" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  ),
  api: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <rect x="2" y="5" width="16" height="10" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M6 10h8M10 7l3 3-3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  storage: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <rect x="3" y="4" width="14" height="12" rx="2" stroke="currentColor" strokeWidth="1.5" />
      <path d="M7 9h6M7 12h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  ),
  secret: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <rect x="4" y="9" width="12" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M7 9V7a3 3 0 016 0v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="10" cy="13" r="1.5" fill="currentColor" />
    </svg>
  ),
  default: (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
      <circle cx="10" cy="10" r="7" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="10" cy="10" r="2.5" fill="currentColor" />
    </svg>
  ),
}

function CriticalityBadge({ criticality }) {
  const map = {
    critical: { bg: 'bg-critical/15 border-critical/30', text: 'text-critical', label: 'Critical' },
    high: { bg: 'bg-danger/15 border-danger/30', text: 'text-danger', label: 'High' },
    medium: { bg: 'bg-warning/15 border-warning/30', text: 'text-warning', label: 'Medium' },
    low: { bg: 'bg-success/15 border-success/30', text: 'text-success', label: 'Low' },
    agent: { bg: 'bg-accent/15 border-accent/30', text: 'text-accent', label: 'Agent' },
  }
  const style = map[criticality] || { bg: 'bg-surface border-border', text: 'text-muted', label: criticality || 'Unknown' }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider border ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  )
}

function EdgeTypePill({ type }) {
  const color = EDGE_COLORS[type] || '#6B7A99'
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border"
      style={{
        color,
        background: `${color}15`,
        borderColor: `${color}30`,
      }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      {type}
    </span>
  )
}

export default function NodePanel({ node, allNodes, edges, narrative, onClose }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (node) {
      // Small delay so CSS transition triggers
      const t = setTimeout(() => setVisible(true), 10)
      return () => clearTimeout(t)
    } else {
      setVisible(false)
    }
  }, [node])

  // Handle escape key
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'Escape' && node) onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [node, onClose])

  if (!node) return null

  // Find connections
  const nodeById = Object.fromEntries(allNodes.map((n) => [n.id, n]))
  const connections = edges
    .filter((e) => {
      const srcId = typeof e.source === 'object' ? e.source.id : e.source
      const tgtId = typeof e.target === 'object' ? e.target.id : e.target
      return srcId === node.id || tgtId === node.id
    })
    .map((e) => {
      const srcId = typeof e.source === 'object' ? e.source.id : e.source
      const tgtId = typeof e.target === 'object' ? e.target.id : e.target
      const otherId = srcId === node.id ? tgtId : srcId
      const direction = srcId === node.id ? 'outbound' : 'inbound'
      return {
        node: nodeById[otherId],
        otherId,
        direction,
        type: e.type || e.access_type || 'Unknown',
        edge: e,
      }
    })
    .filter((c) => c.node)

  // Extract relevant narrative snippet
  const nodeLabel = (node.label || node.id || '').toLowerCase()
  const narrativeLines = (narrative || '').split('\n').filter((line) => {
    const l = line.toLowerCase()
    return l.includes(nodeLabel) || (node.type && l.includes(node.type.toLowerCase()))
  })
  const narrativeSnippet = narrativeLines.slice(0, 3).join(' ').trim()
    || narrative?.split('.').slice(0, 2).join('.').trim()
    || 'No specific narrative available for this node.'

  const nodeColor = NODE_COLORS[node.type === 'agent' ? 'agent' : node.criticality] || NODE_COLORS.default
  const TypeIcon = TYPE_ICONS[node.type] || TYPE_ICONS.default

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 transition-all duration-300"
        style={{
          background: visible ? 'rgba(10,14,26,0.4)' : 'transparent',
          backdropFilter: visible ? 'blur(2px)' : 'none',
          pointerEvents: visible ? 'auto' : 'none',
        }}
        onClick={onClose}
      />

      {/* Panel */}
      <aside
        className="fixed top-14 right-0 bottom-0 z-50 w-80 flex flex-col bg-card border-l border-border overflow-hidden"
        style={{
          transform: visible ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
          boxShadow: '-8px 0 32px rgba(0,0,0,0.5)',
        }}
      >
        {/* Header */}
        <div
          className="flex items-start justify-between p-4 border-b border-border shrink-0"
          style={{ borderBottomColor: `${nodeColor}20` }}
        >
          <div className="flex items-center gap-3 min-w-0">
            <div
              className="shrink-0 w-10 h-10 rounded-lg flex items-center justify-center"
              style={{ background: `${nodeColor}15`, color: nodeColor, border: `1px solid ${nodeColor}30` }}
            >
              {React.cloneElement(TYPE_ICONS[node.type] || TYPE_ICONS.default, { style: { color: nodeColor } })}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white truncate">{node.label || node.id}</p>
              <p className="text-xs text-muted capitalize">{node.type || 'Unknown type'}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="shrink-0 w-7 h-7 rounded-md flex items-center justify-center text-muted hover:text-white hover:bg-surface transition-all ml-2"
            aria-label="Close panel"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M1 1l10 10M11 1L1 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>

        {/* Body — scrollable */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-5">
          {/* Criticality */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted">Risk Level</span>
            <CriticalityBadge criticality={node.type === 'agent' ? 'agent' : node.criticality} />
          </div>

          {/* Properties */}
          {node.properties && Object.keys(node.properties).length > 0 && (
            <div>
              <p className="text-xs font-semibold text-muted uppercase tracking-widest mb-2">Properties</p>
              <div className="flex flex-col gap-1.5">
                {Object.entries(node.properties).map(([k, v]) => (
                  <div key={k} className="flex items-start gap-2 text-xs">
                    <span className="text-muted shrink-0 w-24 truncate">{k}</span>
                    <span className="text-white font-mono break-all">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Connections */}
          <div>
            <p className="text-xs font-semibold text-muted uppercase tracking-widest mb-2">
              Connections
              <span className="ml-1.5 text-white/50 font-normal normal-case tracking-normal">
                ({connections.length})
              </span>
            </p>
            {connections.length === 0 ? (
              <p className="text-xs text-muted/60 italic">No connections found</p>
            ) : (
              <div className="flex flex-col gap-2">
                {connections.map((conn, i) => {
                  const connColor = NODE_COLORS[conn.node.type === 'agent' ? 'agent' : conn.node.criticality] || NODE_COLORS.default
                  return (
                    <div
                      key={i}
                      className="flex items-center justify-between p-2.5 rounded-lg border"
                      style={{ background: `${connColor}08`, borderColor: `${connColor}20` }}
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span
                          className="w-2 h-2 rounded-full shrink-0"
                          style={{ background: connColor }}
                        />
                        <span className="text-xs text-white truncate font-medium">
                          {conn.node.label || conn.node.id}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0 ml-2">
                        {conn.direction === 'outbound' ? (
                          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                            <path d="M2 5h6M5 2l3 3-3 3" stroke="#6B7A99" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        ) : (
                          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                            <path d="M8 5H2M5 2L2 5l3 3" stroke="#6B7A99" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        )}
                        <EdgeTypePill type={conn.type} />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Compromise impact */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M6 1L7.5 4.5H11L8 6.8l1 3.7L6 8.5 3 10.5l1-3.7L1 4.5h3.5z" fill="#FF4444" />
              </svg>
              <p className="text-xs font-semibold text-danger uppercase tracking-widest">
                If Compromised
              </p>
            </div>
            <div className="p-3 rounded-lg border border-danger/20 bg-danger/5">
              <p className="text-xs text-white/80 leading-relaxed">{narrativeSnippet}</p>
            </div>
          </div>

          {/* Description if available */}
          {node.description && (
            <div>
              <p className="text-xs font-semibold text-muted uppercase tracking-widest mb-2">Description</p>
              <p className="text-xs text-white/70 leading-relaxed">{node.description}</p>
            </div>
          )}
        </div>
      </aside>
    </>
  )
}

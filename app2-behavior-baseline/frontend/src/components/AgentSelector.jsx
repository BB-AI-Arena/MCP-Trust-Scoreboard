import React from 'react';

const STATUS_CONFIG = {
  critical: { color: '#FF0066', label: 'Critical', dot: 'bg-critical' },
  high: { color: '#FF4444', label: 'High', dot: 'bg-danger' },
  medium: { color: '#FFB800', label: 'Medium', dot: 'bg-warning' },
  low: { color: '#00FF9C', label: 'Low', dot: 'bg-success' },
  null: { color: '#00FF9C', label: 'Normal', dot: 'bg-success' },
};

function getAgentStatus(agent) {
  if (!agent.highestSeverity || agent.anomalyCount === 0) return 'normal';
  if (agent.highestSeverity === 'critical') return 'critical';
  if (agent.highestSeverity === 'high') return 'high';
  if (agent.highestSeverity === 'medium') return 'medium';
  return 'low';
}

function StatusDot({ severity }) {
  const colors = {
    critical: '#FF0066',
    high: '#FF4444',
    medium: '#FFB800',
    low: '#00FF9C',
    normal: '#00FF9C',
  };
  return (
    <span
      className="inline-block w-2 h-2 rounded-full flex-shrink-0"
      style={{ backgroundColor: colors[severity] || '#00FF9C' }}
    />
  );
}

const AGENT_TYPE_ICONS = {
  code: '⚙️',
  data: '🗄️',
  auth: '🔐',
  ml: '🤖',
  index: '📑',
};

export default function AgentSelector({ agents, selectedAgent, onSelect }) {
  return (
    <div className="flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <h2 className="text-xs font-semibold text-muted uppercase tracking-widest">
          AI Agents
        </h2>
        <p className="text-xs text-muted mt-0.5">{agents.length} monitored</p>
      </div>

      <ul className="py-2">
        {agents.map((agent) => {
          const status = getAgentStatus(agent);
          const isSelected = selectedAgent?.id === agent.id;
          const icon = AGENT_TYPE_ICONS[agent.type] || '🤖';

          return (
            <li key={agent.id}>
              <button
                onClick={() => onSelect(agent)}
                className={[
                  'w-full text-left px-4 py-3 flex items-start gap-3 transition-all duration-150',
                  isSelected
                    ? 'bg-surface border-l-2 border-accent'
                    : 'border-l-2 border-transparent hover:bg-surface/50',
                ].join(' ')}
              >
                {/* Icon */}
                <span className="text-base mt-0.5 flex-shrink-0">{icon}</span>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1">
                    <span
                      className={`text-sm font-medium truncate ${
                        isSelected ? 'text-white' : 'text-gray-300'
                      }`}
                    >
                      {agent.name}
                    </span>
                    {agent.anomalyCount > 0 && (
                      <span
                        className="text-xs font-bold px-1.5 py-0.5 rounded-full flex-shrink-0"
                        style={{
                          backgroundColor:
                            status === 'critical'
                              ? 'rgba(255,0,102,0.2)'
                              : status === 'high'
                              ? 'rgba(255,68,68,0.2)'
                              : 'rgba(255,184,0,0.2)',
                          color:
                            status === 'critical'
                              ? '#FF0066'
                              : status === 'high'
                              ? '#FF4444'
                              : '#FFB800',
                        }}
                      >
                        {agent.anomalyCount}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5 mt-1">
                    <StatusDot severity={status} />
                    <span className="text-xs text-muted capitalize">
                      {status === 'normal' ? 'Nominal' : `${status} anomaly`}
                    </span>
                  </div>
                </div>
              </button>
            </li>
          );
        })}
      </ul>

      {/* Footer hint */}
      <div className="px-4 py-3 mt-auto border-t border-border">
        <p className="text-xs text-muted">Auto-refresh: 5s</p>
      </div>
    </div>
  );
}

import React, { useState, useRef, useCallback } from 'react'

const ENDPOINT_TYPES = [
  'LLM Agent',
  'Code Agent',
  'Browser Agent',
  'Data Agent',
  'Custom',
]

const DEFAULT_PERMISSIONS = ['read_files', 'write_files', 'execute_code', 'access_env_vars']
const DEFAULT_INTEGRATIONS = ['github', 's3', 'openai_api', 'postgres_db']

// ─── Tag Input ────────────────────────────────────────────────────────────────

function TagInput({ tags, onChange, placeholder, colorClass = 'accent' }) {
  const [inputVal, setInputVal] = useState('')
  const inputRef = useRef(null)

  const addTag = useCallback((value) => {
    const trimmed = value.trim().replace(/,+$/, '')
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed])
    }
    setInputVal('')
  }, [tags, onChange])

  const removeTag = useCallback((index) => {
    onChange(tags.filter((_, i) => i !== index))
  }, [tags, onChange])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addTag(inputVal)
    } else if (e.key === 'Backspace' && !inputVal && tags.length > 0) {
      removeTag(tags.length - 1)
    }
  }

  const handleBlur = () => {
    if (inputVal.trim()) addTag(inputVal)
  }

  const colorMap = {
    accent: {
      chip: 'bg-accent/10 border-accent/25 text-accent',
      remove: 'text-accent/60 hover:text-accent',
      input: 'focus:ring-accent/30 focus:border-accent/60',
    },
    warning: {
      chip: 'bg-warning/10 border-warning/25 text-warning',
      remove: 'text-warning/60 hover:text-warning',
      input: 'focus:ring-warning/30 focus:border-warning/60',
    },
  }
  const c = colorMap[colorClass] || colorMap.accent

  return (
    <div
      className={`min-h-[44px] flex flex-wrap gap-1.5 items-center px-3 py-2 rounded-lg bg-surface border border-border cursor-text transition-all ${c.input} focus-within:outline-none focus-within:ring-2 focus-within:ring-accent/20 focus-within:border-accent/50`}
      onClick={() => inputRef.current?.focus()}
    >
      {tags.map((tag, i) => (
        <span
          key={`${tag}-${i}`}
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-mono font-medium border ${c.chip}`}
        >
          {tag}
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); removeTag(i) }}
            className={`leading-none ${c.remove} transition-colors`}
            aria-label={`Remove ${tag}`}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M2 2l6 6M8 2l-6 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </span>
      ))}
      <input
        ref={inputRef}
        type="text"
        value={inputVal}
        onChange={(e) => setInputVal(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={tags.length === 0 ? placeholder : ''}
        className="flex-1 min-w-[120px] bg-transparent text-xs text-white placeholder-muted outline-none font-mono"
      />
    </div>
  )
}

// ─── Field Label ──────────────────────────────────────────────────────────────

function FieldLabel({ children, hint }) {
  return (
    <div className="flex items-baseline justify-between mb-1.5">
      <label className="text-xs font-semibold text-muted uppercase tracking-widest">
        {children}
      </label>
      {hint && <span className="text-xs text-muted/60 normal-case tracking-normal">{hint}</span>}
    </div>
  )
}

// ─── AgentInput ───────────────────────────────────────────────────────────────

export default function AgentInput({ onSubmit }) {
  const [agentName, setAgentName] = useState('GPT-4 Code Assistant')
  const [endpointType, setEndpointType] = useState('Code Agent')
  const [permissions, setPermissions] = useState([...DEFAULT_PERMISSIONS])
  const [integrations, setIntegrations] = useState([...DEFAULT_INTEGRATIONS])
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!agentName.trim()) return
    setIsLoading(true)
    try {
      await onSubmit({
        agent_name: agentName.trim(),
        endpoint_type: endpointType,
        permissions,
        integrations,
      })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="card p-6 flex flex-col gap-5"
      style={{ boxShadow: '0 4px 32px rgba(0,0,0,0.5), 0 0 0 1px rgba(31,41,55,0.8)' }}
    >
      {/* Agent Name */}
      <div>
        <FieldLabel>Agent Name</FieldLabel>
        <input
          type="text"
          value={agentName}
          onChange={(e) => setAgentName(e.target.value)}
          placeholder="e.g. GPT-4 Code Assistant"
          required
          className="w-full px-3 py-2.5 rounded-lg bg-surface border border-border text-sm text-white placeholder-muted outline-none transition-all focus:border-accent/50 focus:ring-2 focus:ring-accent/20"
        />
      </div>

      {/* Endpoint Type */}
      <div>
        <FieldLabel>Endpoint Type</FieldLabel>
        <div className="relative">
          <select
            value={endpointType}
            onChange={(e) => setEndpointType(e.target.value)}
            className="w-full px-3 py-2.5 rounded-lg bg-surface border border-border text-sm text-white outline-none appearance-none cursor-pointer transition-all focus:border-accent/50 focus:ring-2 focus:ring-accent/20"
          >
            {ENDPOINT_TYPES.map((type) => (
              <option key={type} value={type} className="bg-surface text-white">
                {type}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 4l4 4 4-4" stroke="#6B7A99" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
        </div>
      </div>

      {/* Permissions */}
      <div>
        <FieldLabel hint="Press Enter or comma to add">Permissions</FieldLabel>
        <TagInput
          tags={permissions}
          onChange={setPermissions}
          placeholder="e.g. read_files, execute_code"
          colorClass="accent"
        />
        {permissions.length === 0 && (
          <p className="mt-1.5 text-xs text-muted/60">Add at least one permission to analyze the blast radius</p>
        )}
      </div>

      {/* Integrations */}
      <div>
        <FieldLabel hint="Press Enter or comma to add">Integrations</FieldLabel>
        <TagInput
          tags={integrations}
          onChange={setIntegrations}
          placeholder="e.g. github, s3, postgres_db"
          colorClass="warning"
        />
      </div>

      {/* Divider */}
      <div className="border-t border-border/60" />

      {/* Submit */}
      <button
        type="submit"
        disabled={isLoading || !agentName.trim()}
        className={[
          'relative w-full py-3 rounded-xl text-sm font-semibold tracking-wide transition-all duration-200',
          'bg-accent text-bg',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          !isLoading && agentName.trim()
            ? 'hover:brightness-110 glow-accent active:scale-[0.98]'
            : '',
        ].join(' ')}
      >
        {isLoading ? (
          <span className="flex items-center justify-center gap-2">
            <svg className="animate-spin" width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="2" strokeOpacity="0.25" />
              <path d="M14 8a6 6 0 00-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Analyzing...
          </span>
        ) : (
          <span className="flex items-center justify-center gap-2">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="3" fill="currentColor" />
              <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 2" />
              <path d="M8 1v2M8 13v2M1 8h2M13 8h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            Analyze Blast Radius
          </span>
        )}
      </button>
    </form>
  )
}

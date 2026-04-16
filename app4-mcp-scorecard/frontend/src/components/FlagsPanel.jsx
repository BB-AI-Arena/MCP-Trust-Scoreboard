import React from 'react'

function WarningIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5 flex-shrink-0">
      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 flex-shrink-0">
      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
    </svg>
  )
}

export default function FlagsPanel({ flags }) {
  const hasFlags = flags && flags.length > 0

  return (
    <div className="bg-card card-border rounded-xl p-5">
      <h3 className="text-sm font-600 text-white mb-3 tracking-wide uppercase">Security Flags</h3>

      {!hasFlags ? (
        <div className="flex items-center gap-2 text-success">
          <CheckIcon />
          <span className="text-sm font-500">No flags detected — manifest passed all checks</span>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {flags.map((flag, i) => (
            <div
              key={i}
              className="flex items-center gap-1.5 bg-red-950/40 border border-danger/30 rounded-lg px-3 py-1.5 text-xs text-red-300 font-400 leading-snug max-w-full animate-fade-in"
              style={{ animationDelay: `${i * 60}ms`, animationFillMode: 'both' }}
            >
              <WarningIcon />
              <span>{flag}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

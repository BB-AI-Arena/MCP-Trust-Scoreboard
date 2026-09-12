import React, { useEffect, useRef } from 'react'

const DIMENSION_LABELS = {
  identity: 'Identity',
  permission_sprawl: 'Permission Sprawl',
  network_behavior: 'Network Behavior',
  code_transparency: 'Code Transparency',
  version_drift: 'Version Drift',
  community_signal: 'Community Signal',
}

const DIMENSION_ICONS = {
  identity: (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
    </svg>
  ),
  permission_sprawl: (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
    </svg>
  ),
  network_behavior: (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path fillRule="evenodd" d="M4.083 9h1.946c.089-1.546.383-2.97.837-4.118A6.004 6.004 0 004.083 9zM10 2a8 8 0 100 16A8 8 0 0010 2zm0 2c-.076 0-.232.032-.465.262-.238.234-.497.623-.737 1.182-.389.907-.673 2.142-.766 3.556h3.936c-.093-1.414-.377-2.649-.766-3.556-.24-.559-.499-.948-.737-1.182C10.232 4.032 10.076 4 10 4zm3.971 5c-.089-1.546-.383-2.97-.837-4.118A6.004 6.004 0 0115.917 9h-1.946zm-2.003 2H8.032c.093 1.414.377 2.649.766 3.556.24.559.499.948.737 1.182.233.23.389.262.465.262.076 0 .232-.032.465-.262.238-.234.498-.623.737-1.182.389-.907.673-2.142.766-3.556zm1.166 4.118c.454-1.147.748-2.572.837-4.118h1.946a6.004 6.004 0 01-2.783 4.118zm-6.268 0C6.412 13.97 6.118 12.546 6.03 11H4.083a6.004 6.004 0 002.783 4.118z" clipRule="evenodd" />
    </svg>
  ),
  code_transparency: (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" />
    </svg>
  ),
  version_drift: (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
    </svg>
  ),
  community_signal: (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
      <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
    </svg>
  ),
}

function getBarColor(score) {
  if (score >= 80) return 'bg-success'
  if (score >= 60) return 'bg-warning'
  if (score >= 40) return 'bg-orange-500'
  return 'bg-danger'
}

function getTextColor(score) {
  if (score >= 80) return 'text-success'
  if (score >= 60) return 'text-warning'
  if (score >= 40) return 'text-orange-400'
  return 'text-danger'
}

export default function DimensionCard({ dimension, data, index }) {
  const barRef = useRef(null)

  useEffect(() => {
    if (!barRef.current) return
    barRef.current.style.width = '0%'
    const timer = setTimeout(() => {
      if (barRef.current) {
        barRef.current.style.transition = 'width 1s cubic-bezier(0.4,0,0.2,1)'
        barRef.current.style.width = `${data.score}%`
      }
    }, index * 80 + 200)
    return () => clearTimeout(timer)
  }, [data.score, index])

  const label = DIMENSION_LABELS[dimension] || dimension
  const icon = DIMENSION_ICONS[dimension]

  return (
    <div
      className="bg-card card-border rounded-xl p-5 flex flex-col gap-3 animate-slide-up"
      style={{ animationDelay: `${index * 80}ms`, animationFillMode: 'both' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-muted">{icon}</span>
          <span className="text-sm font-600 text-white tracking-wide">{label}</span>
        </div>
        <span className={`text-lg font-800 ${getTextColor(data.score)}`}>
          {data.score}
        </span>
      </div>

      {/* Bar */}
      <div className="h-1.5 bg-surface rounded-full overflow-hidden">
        <div
          ref={barRef}
          data-report-width={`${data.score}%`}
          className={`h-full rounded-full ${getBarColor(data.score)}`}
          style={{ width: '0%' }}
        />
      </div>

      {/* Explanation */}
      <p className="text-xs text-muted leading-relaxed">{data.explanation}</p>
    </div>
  )
}

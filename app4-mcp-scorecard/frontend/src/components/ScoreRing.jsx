import React, { useEffect, useRef } from 'react'

const SIZE = 200
const STROKE = 14
const RADIUS = (SIZE - STROKE) / 2
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

function getColor(score) {
  if (score >= 80) return '#00FF9C'
  if (score >= 60) return '#FFB800'
  if (score >= 40) return '#FF8C00'
  return '#FF4444'
}

function getGlow(score) {
  if (score >= 80) return 'drop-shadow(0 0 12px rgba(0,255,156,0.6))'
  if (score >= 60) return 'drop-shadow(0 0 12px rgba(255,184,0,0.6))'
  if (score >= 40) return 'drop-shadow(0 0 12px rgba(255,140,0,0.6))'
  return 'drop-shadow(0 0 12px rgba(255,68,68,0.6))'
}

export default function ScoreRing({ score }) {
  const circleRef = useRef(null)

  useEffect(() => {
    if (!circleRef.current) return
    const offset = CIRCUMFERENCE - (score / 100) * CIRCUMFERENCE
    // Start fully hidden, animate to target
    circleRef.current.style.strokeDashoffset = CIRCUMFERENCE
    const frame = requestAnimationFrame(() => {
      circleRef.current.style.transition = 'stroke-dashoffset 1.4s cubic-bezier(0.4,0,0.2,1)'
      circleRef.current.style.strokeDashoffset = offset
    })
    return () => cancelAnimationFrame(frame)
  }, [score])

  const color = getColor(score)

  return (
    <div className="flex flex-col items-center gap-3">
      <svg
        width={SIZE}
        height={SIZE}
        style={{ filter: getGlow(score) }}
        aria-label={`Trust score ${score} out of 100`}
      >
        {/* Track */}
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke="#1E2A45"
          strokeWidth={STROKE}
        />
        {/* Progress */}
        <circle
          ref={circleRef}
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={CIRCUMFERENCE}
          transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
          style={{ willChange: 'stroke-dashoffset' }}
        />
        {/* Score label */}
        <text
          x="50%"
          y="46%"
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="42"
          fontWeight="800"
          fontFamily="Inter, sans-serif"
          fill={color}
        >
          {score}
        </text>
        <text
          x="50%"
          y="68%"
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="13"
          fontWeight="500"
          fontFamily="Inter, sans-serif"
          fill="#6B7A99"
          letterSpacing="2"
        >
          / 100
        </text>
      </svg>
    </div>
  )
}

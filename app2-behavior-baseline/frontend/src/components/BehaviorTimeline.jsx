import React, { useState } from 'react';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

// Activity level 0-3: inactive, low, medium, high
const LEVEL_COLORS = {
  0: '#1A2235', // inactive
  1: '#1a3a2a', // low
  2: '#00AA66', // medium
  3: '#00FF9C', // high
};

const LEVEL_LABELS = ['Inactive', 'Low', 'Medium', 'High'];

function getActivityColor(level) {
  return LEVEL_COLORS[level] ?? LEVEL_COLORS[0];
}

function isOffHours(hour) {
  return hour < 8 || hour >= 20;
}

export default function BehaviorTimeline({ agentData, agentId }) {
  const [tooltip, setTooltip] = useState(null);

  if (!agentData) {
    return (
      <div
        className="rounded-xl border p-6 flex items-center justify-center"
        style={{ backgroundColor: '#111827', borderColor: '#1F2937', height: 220 }}
      >
        <div className="text-center">
          <div
            className="w-6 h-6 border-2 border-t-transparent rounded-full animate-spin mx-auto mb-2"
            style={{ borderColor: '#00D4FF', borderTopColor: 'transparent' }}
          />
          <p className="text-xs" style={{ color: '#6B7A99' }}>Loading activity data…</p>
        </div>
      </div>
    );
  }

  const CELL_W = 24;
  const CELL_H = 18;
  const CELL_GAP = 2;
  const LEFT_LABEL_W = 36;
  const BOTTOM_LABEL_H = 20;
  const TOP_MARGIN = 4;

  const totalW = LEFT_LABEL_W + HOURS.length * (CELL_W + CELL_GAP);
  const totalH = TOP_MARGIN + DAYS.length * (CELL_H + CELL_GAP) + BOTTOM_LABEL_H;

  return (
    <div
      className="rounded-xl border p-4"
      style={{ backgroundColor: '#111827', borderColor: '#1F2937' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-semibold text-white">Activity Heatmap</h2>
          <p className="text-xs mt-0.5" style={{ color: '#6B7A99' }}>
            7-day hourly behavior — off-hours anomalies highlighted
          </p>
        </div>
      </div>

      {/* SVG heatmap */}
      <div style={{ position: 'relative', overflowX: 'auto' }}>
        <svg
          width={totalW}
          height={totalH}
          style={{ display: 'block', overflow: 'visible' }}
        >
          {/* Day labels */}
          {DAYS.map((day, dayIdx) => (
            <text
              key={day}
              x={LEFT_LABEL_W - 6}
              y={TOP_MARGIN + dayIdx * (CELL_H + CELL_GAP) + CELL_H / 2 + 4}
              textAnchor="end"
              style={{ fill: '#6B7A99', fontSize: 10, fontFamily: 'Inter' }}
            >
              {day}
            </text>
          ))}

          {/* Hour labels (every 4) */}
          {HOURS.filter((h) => h % 4 === 0).map((hour) => (
            <text
              key={hour}
              x={LEFT_LABEL_W + hour * (CELL_W + CELL_GAP) + CELL_W / 2}
              y={TOP_MARGIN + DAYS.length * (CELL_H + CELL_GAP) + 14}
              textAnchor="middle"
              style={{ fill: '#6B7A99', fontSize: 10, fontFamily: 'Inter' }}
            >
              {hour.toString().padStart(2, '0')}
            </text>
          ))}

          {/* Cells */}
          {DAYS.map((day, dayIdx) =>
            HOURS.map((hour) => {
              const level = agentData[dayIdx]?.[hour] ?? 0;
              const offHours = isOffHours(hour);
              const hasAnomalyActivity = offHours && level >= 2;
              const x = LEFT_LABEL_W + hour * (CELL_W + CELL_GAP);
              const y = TOP_MARGIN + dayIdx * (CELL_H + CELL_GAP);

              return (
                <g key={`${dayIdx}-${hour}`}>
                  <rect
                    x={x}
                    y={y}
                    width={CELL_W}
                    height={CELL_H}
                    rx={3}
                    fill={getActivityColor(level)}
                    stroke={hasAnomalyActivity ? '#FF4444' : 'none'}
                    strokeWidth={hasAnomalyActivity ? 1.5 : 0}
                    style={{ cursor: 'pointer', transition: 'opacity 0.15s' }}
                    onMouseEnter={(e) => {
                      setTooltip({
                        x: e.clientX,
                        y: e.clientY,
                        day,
                        hour,
                        level,
                        offHours,
                        hasAnomalyActivity,
                      });
                    }}
                    onMouseLeave={() => setTooltip(null)}
                  />
                  {/* Off-hours background tint when inactive */}
                  {offHours && level === 0 && (
                    <rect
                      x={x}
                      y={y}
                      width={CELL_W}
                      height={CELL_H}
                      rx={3}
                      fill="rgba(0,0,0,0.2)"
                      style={{ pointerEvents: 'none' }}
                    />
                  )}
                </g>
              );
            })
          )}
        </svg>

        {/* Tooltip */}
        {tooltip && (
          <div
            className="fixed z-50 rounded-lg border px-3 py-2 pointer-events-none shadow-xl"
            style={{
              backgroundColor: '#111827',
              borderColor: '#1F2937',
              left: tooltip.x + 12,
              top: tooltip.y - 40,
              fontSize: 12,
              minWidth: 140,
            }}
          >
            <div className="font-semibold text-white mb-1">
              {tooltip.day} {tooltip.hour.toString().padStart(2, '0')}:00
            </div>
            <div style={{ color: '#6B7A99' }}>
              Activity:{' '}
              <span
                className="font-semibold"
                style={{ color: getActivityColor(tooltip.level) }}
              >
                {LEVEL_LABELS[tooltip.level]}
              </span>
            </div>
            {tooltip.offHours && (
              <div style={{ color: '#6B7A99', fontSize: 11, marginTop: 2 }}>Off-hours window</div>
            )}
            {tooltip.hasAnomalyActivity && (
              <div className="font-semibold mt-1" style={{ color: '#FF4444', fontSize: 11 }}>
                ⚠ Anomalous off-hours activity
              </div>
            )}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-4 flex-wrap">
        {[0, 1, 2, 3].map((level) => (
          <div key={level} className="flex items-center gap-1.5">
            <span
              className="w-4 h-3 rounded-sm inline-block"
              style={{ backgroundColor: LEVEL_COLORS[level] }}
            />
            <span className="text-xs" style={{ color: '#6B7A99' }}>
              {LEVEL_LABELS[level]}
            </span>
          </div>
        ))}
        <div className="flex items-center gap-1.5 ml-2">
          <span
            className="w-4 h-3 rounded-sm inline-block"
            style={{
              backgroundColor: LEVEL_COLORS[2],
              border: '1.5px solid #FF4444',
            }}
          />
          <span className="text-xs" style={{ color: '#FF4444' }}>
            Off-hours anomaly
          </span>
        </div>
        <div className="ml-auto text-xs" style={{ color: '#6B7A99' }}>
          Off-hours: 20:00 – 08:00
        </div>
      </div>
    </div>
  );
}

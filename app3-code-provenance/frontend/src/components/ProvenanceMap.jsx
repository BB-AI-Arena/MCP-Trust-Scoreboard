import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';

const MODEL_COLORS = {
  Claude: '#7C3AED',
  'GPT-4': '#10B981',
  Gemini: '#F59E0B',
  Copilot: '#3B82F6',
  Human: '#6B7280',
  Unknown: '#374151',
};

const MODEL_LEGEND = [
  { model: 'Claude', color: '#7C3AED' },
  { model: 'GPT-4', color: '#10B981' },
  { model: 'Gemini', color: '#F59E0B' },
  { model: 'Copilot', color: '#3B82F6' },
  { model: 'Human', color: '#6B7280' },
  { model: 'Unknown', color: '#374151' },
];

export default function ProvenanceMap({ files, onFileClick }) {
  const svgRef = useRef(null);
  const containerRef = useRef(null);
  const [tooltip, setTooltip] = useState(null);
  const [dimensions, setDimensions] = useState({ width: 500, height: 340 });

  // Resize observer
  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.floor(entry.contentRect.width);
        if (w > 0) setDimensions({ width: w, height: Math.max(280, Math.round(w * 0.65)) });
      }
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  const buildTreemap = useCallback(() => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    if (!files || files.length === 0) return;

    const { width, height } = dimensions;

    // Build hierarchy data
    const children = files.map((f) => ({
      name: f.filename || 'file',
      value: Math.max(1, f.size || (f.findings?.length || 1) * 100 + 200),
      file: f,
    }));

    const root = d3
      .hierarchy({ name: 'root', children })
      .sum((d) => d.value)
      .sort((a, b) => b.value - a.value);

    d3.treemap()
      .size([width, height])
      .padding(3)
      .round(true)(root);

    const g = svg.attr('width', width).attr('height', height).append('g');

    const cells = g
      .selectAll('g')
      .data(root.leaves())
      .enter()
      .append('g')
      .attr('transform', (d) => `translate(${d.x0},${d.y0})`)
      .attr('class', 'treemap-cell')
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation();
        onFileClick && onFileClick(d.data.file);
      })
      .on('mousemove', (event, d) => {
        const rect = svgRef.current.getBoundingClientRect();
        setTooltip({
          x: event.clientX - rect.left + 12,
          y: event.clientY - rect.top - 10,
          file: d.data.file,
        });
      })
      .on('mouseleave', () => setTooltip(null));

    // Background rect
    cells
      .append('rect')
      .attr('width', (d) => Math.max(0, d.x1 - d.x0))
      .attr('height', (d) => Math.max(0, d.y1 - d.y0))
      .attr('rx', 4)
      .attr('fill', (d) => {
        const model = d.data.file?.provenance?.model || 'Unknown';
        return MODEL_COLORS[model] || MODEL_COLORS.Unknown;
      })
      .attr('fill-opacity', 0.7)
      .attr('stroke', '#0A0E1A')
      .attr('stroke-width', 1.5);

    // Risk badge overlay
    cells
      .append('rect')
      .attr('width', (d) => Math.max(0, d.x1 - d.x0))
      .attr('height', (d) => Math.max(0, d.y1 - d.y0))
      .attr('rx', 4)
      .attr('fill', (d) => {
        const risk = d.data.file?.risk_level;
        const overlay = { critical: '#FF0066', high: '#FF4444', medium: '#FFB800' };
        return overlay[risk] || 'transparent';
      })
      .attr('fill-opacity', (d) => {
        const risk = d.data.file?.risk_level;
        return ['critical', 'high', 'medium'].includes(risk) ? 0.15 : 0;
      });

    // Label — only if cell is large enough
    cells
      .filter((d) => d.x1 - d.x0 > 60 && d.y1 - d.y0 > 28)
      .append('text')
      .attr('x', 6)
      .attr('y', 16)
      .attr('font-size', 10)
      .attr('font-family', 'Inter, sans-serif')
      .attr('fill', 'rgba(255,255,255,0.85)')
      .attr('font-weight', '500')
      .text((d) => {
        const name = d.data.name.split('/').pop();
        const maxLen = Math.floor((d.x1 - d.x0) / 7);
        return name.length > maxLen ? name.slice(0, maxLen - 1) + '…' : name;
      });

    // Sub-label: model
    cells
      .filter((d) => d.x1 - d.x0 > 70 && d.y1 - d.y0 > 42)
      .append('text')
      .attr('x', 6)
      .attr('y', 28)
      .attr('font-size', 9)
      .attr('font-family', 'Inter, sans-serif')
      .attr('fill', 'rgba(255,255,255,0.5)')
      .text((d) => d.data.file?.provenance?.model || 'Unknown');
  }, [files, dimensions, onFileClick]);

  useEffect(() => {
    buildTreemap();
  }, [buildTreemap]);

  if (!files || files.length === 0) {
    return (
      <div className="bg-card border border-border rounded-xl p-6 flex items-center justify-center min-h-[300px]">
        <span className="text-muted text-sm">No files to display</span>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-border flex items-center justify-between">
        <h2 className="font-semibold text-sm text-white">Provenance Map</h2>
        <span className="text-xs text-muted">{files.length} files · click to inspect</span>
      </div>

      {/* Treemap */}
      <div ref={containerRef} className="relative w-full px-4 pt-4 pb-2">
        <svg ref={svgRef} className="w-full" style={{ display: 'block' }} />

        {/* Tooltip */}
        {tooltip && (
          <div
            className="pointer-events-none absolute z-50 bg-surface border border-border rounded-lg p-3 text-xs shadow-xl max-w-[220px]"
            style={{ left: tooltip.x, top: tooltip.y }}
          >
            <div className="font-medium text-white mb-1 truncate">
              {tooltip.file?.filename || 'file'}
            </div>
            <div className="space-y-0.5 text-muted">
              <div>
                Model:{' '}
                <span
                  className="font-semibold"
                  style={{
                    color: MODEL_COLORS[tooltip.file?.provenance?.model] || '#6B7A99',
                  }}
                >
                  {tooltip.file?.provenance?.model || 'Unknown'}
                </span>
              </div>
              <div>
                Confidence:{' '}
                <span className="text-white">{tooltip.file?.provenance?.confidence ?? '—'}%</span>
              </div>
              <div>
                Risk:{' '}
                <span
                  className={`font-semibold uppercase ${
                    {
                      critical: 'text-critical',
                      high: 'text-danger',
                      medium: 'text-warning',
                      low: 'text-green-400',
                      safe: 'text-success',
                    }[tooltip.file?.risk_level] || 'text-muted'
                  }`}
                >
                  {tooltip.file?.risk_level || 'unknown'}
                </span>
              </div>
              {tooltip.file?.findings?.length > 0 && (
                <div>Findings: <span className="text-white">{tooltip.file.findings.length}</span></div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="px-4 pb-4 pt-1 flex flex-wrap gap-x-4 gap-y-1.5">
        {MODEL_LEGEND.map(({ model, color }) => (
          <div key={model} className="flex items-center gap-1.5 text-xs text-muted">
            <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: color }} />
            {model}
          </div>
        ))}
      </div>
    </div>
  );
}

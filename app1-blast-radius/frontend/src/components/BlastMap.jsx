import React, { useEffect, useRef, useCallback } from 'react'
import * as d3 from 'd3'

// ─── Constants ─────────────────────────────────────────────────────────────────

const NODE_COLORS = {
  critical: '#FF0066',
  high: '#FF4444',
  medium: '#FFB800',
  low: '#00FF9C',
  agent: '#00D4FF',
  default: '#6B7A99',
}

const NODE_RADII = {
  critical: 20,
  high: 16,
  medium: 14,
  low: 12,
  agent: 24,
  default: 12,
}

const EDGE_COLORS = {
  WriteAccess: '#FF4444',
  ReadAccess: '#00D4FF',
  ExecuteAccess: '#9B59B6',
  Authenticate: '#FFB800',
  default: '#1F2937',
}

function getNodeColor(node) {
  if (node.type === 'agent') return NODE_COLORS.agent
  return NODE_COLORS[node.criticality] || NODE_COLORS.default
}

function getNodeRadius(node) {
  if (node.type === 'agent') return NODE_RADII.agent
  return NODE_RADII[node.criticality] || NODE_RADII.default
}

function getEdgeColor(edge) {
  return EDGE_COLORS[edge.type] || EDGE_COLORS[edge.access_type] || EDGE_COLORS.default
}

// ─── BlastMap ─────────────────────────────────────────────────────────────────

export default function BlastMap({ nodes, edges, onNodeClick }) {
  const containerRef = useRef(null)
  const svgRef = useRef(null)
  const simulationRef = useRef(null)

  const buildGraph = useCallback(() => {
    if (!containerRef.current || !nodes.length) return

    // Clear previous
    d3.select(svgRef.current).selectAll('*').remove()
    if (simulationRef.current) simulationRef.current.stop()

    const { width, height } = containerRef.current.getBoundingClientRect()

    // ── SVG setup ────────────────────────────────────────────────────────────
    const svg = d3.select(svgRef.current)
      .attr('width', width)
      .attr('height', height)
      .attr('viewBox', [0, 0, width, height])
      .style('cursor', 'grab')

    // Defs: arrow markers + glow filter
    const defs = svg.append('defs')

    // Glow filter
    const filter = defs.append('filter').attr('id', 'node-glow')
    filter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'coloredBlur')
    const feMerge = filter.append('feMerge')
    feMerge.append('feMergeNode').attr('in', 'coloredBlur')
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic')

    // Arrow markers for each edge type
    const markerTypes = Object.keys(EDGE_COLORS)
    markerTypes.forEach((type) => {
      const color = EDGE_COLORS[type]
      defs.append('marker')
        .attr('id', `arrow-${type}`)
        .attr('viewBox', '0 -4 8 8')
        .attr('refX', 18)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-4L8,0L0,4')
        .attr('fill', color)
        .attr('opacity', 0.8)
    })

    // ── Zoom / pan ─────────────────────────────────────────────────────────
    const zoomGroup = svg.append('g').attr('class', 'zoom-group')

    const zoom = d3.zoom()
      .scaleExtent([0.2, 4])
      .on('zoom', (event) => {
        zoomGroup.attr('transform', event.transform)
      })

    svg.call(zoom)
      .on('dblclick.zoom', null) // disable double-click zoom

    // Reset cursor on mouseup
    svg.on('mousedown', () => svg.style('cursor', 'grabbing'))
    svg.on('mouseup', () => svg.style('cursor', 'grab'))

    // ── Deep copy data for simulation mutation ─────────────────────────────
    const simNodes = nodes.map((n) => ({ ...n }))
    const nodeById = Object.fromEntries(simNodes.map((n) => [n.id, n]))

    const simEdges = edges
      .filter((e) => nodeById[e.source] && nodeById[e.target])
      .map((e) => ({
        ...e,
        source: nodeById[e.source],
        target: nodeById[e.target],
      }))

    // ── Force simulation ───────────────────────────────────────────────────
    const simulation = d3.forceSimulation(simNodes)
      .force('link', d3.forceLink(simEdges).id((d) => d.id).distance(120).strength(0.5))
      .force('charge', d3.forceManyBody().strength(-350))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius((d) => getNodeRadius(d) + 18))
      .alphaDecay(0.03)

    simulationRef.current = simulation

    // Start nodes at center (fly-out animation)
    simNodes.forEach((n) => {
      n.x = width / 2 + (Math.random() - 0.5) * 4
      n.y = height / 2 + (Math.random() - 0.5) * 4
    })

    // ── Edges ──────────────────────────────────────────────────────────────
    const edgeGroup = zoomGroup.append('g').attr('class', 'edges')

    const link = edgeGroup
      .selectAll('line')
      .data(simEdges)
      .join('line')
      .attr('stroke', (d) => getEdgeColor(d))
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.6)
      .attr('marker-end', (d) => {
        const type = d.type || d.access_type || 'default'
        return `url(#arrow-${markerTypes.includes(type) ? type : 'default'})`
      })

    // Edge labels
    const edgeLabelGroup = zoomGroup.append('g').attr('class', 'edge-labels')
    const edgeLabel = edgeLabelGroup
      .selectAll('text')
      .data(simEdges)
      .join('text')
      .attr('font-size', 9)
      .attr('fill', (d) => getEdgeColor(d))
      .attr('opacity', 0.7)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'middle')
      .text((d) => d.type || d.access_type || '')

    // ── Nodes ──────────────────────────────────────────────────────────────
    const nodeGroup = zoomGroup.append('g').attr('class', 'nodes')

    const nodeG = nodeGroup
      .selectAll('g')
      .data(simNodes)
      .join('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .call(
        d3.drag()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
          })
          .on('drag', (event, d) => {
            d.fx = event.x
            d.fy = event.y
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null
            d.fy = null
          })
      )
      .on('click', (event, d) => {
        event.stopPropagation()
        onNodeClick && onNodeClick(d)
      })

    // Outer glow ring for critical/agent nodes
    nodeG
      .filter((d) => d.type === 'agent' || d.criticality === 'critical')
      .append('circle')
      .attr('r', (d) => getNodeRadius(d) + 6)
      .attr('fill', 'none')
      .attr('stroke', (d) => getNodeColor(d))
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.3)
      .attr('filter', 'url(#node-glow)')

    // Main node circle
    nodeG
      .append('circle')
      .attr('r', (d) => getNodeRadius(d))
      .attr('fill', (d) => getNodeColor(d))
      .attr('fill-opacity', 0.15)
      .attr('stroke', (d) => getNodeColor(d))
      .attr('stroke-width', 2)
      .attr('filter', (d) => (d.type === 'agent' || d.criticality === 'critical') ? 'url(#node-glow)' : null)

    // Node icon (type indicator)
    nodeG
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('font-size', (d) => getNodeRadius(d) * 0.75)
      .attr('fill', (d) => getNodeColor(d))
      .attr('pointer-events', 'none')
      .text((d) => {
        const icons = {
          agent: '◈',
          database: '⬡',
          storage: '▣',
          api: '⬡',
          service: '◎',
          file: '▤',
          network: '⬡',
          secret: '⬟',
          permission: '◈',
          default: '○',
        }
        return icons[d.type] || icons.default
      })

    // Node labels
    nodeG
      .append('text')
      .attr('text-anchor', 'middle')
      .attr('y', (d) => getNodeRadius(d) + 12)
      .attr('font-size', 10)
      .attr('font-family', 'Inter, sans-serif')
      .attr('fill', '#e2e8f0')
      .attr('pointer-events', 'none')
      .text((d) => d.label || d.id)

    // Criticality badge dot
    nodeG
      .filter((d) => d.criticality && d.type !== 'agent')
      .append('circle')
      .attr('cx', (d) => getNodeRadius(d) - 4)
      .attr('cy', (d) => -(getNodeRadius(d) - 4))
      .attr('r', 4)
      .attr('fill', (d) => getNodeColor(d))
      .attr('stroke', '#0A0E1A')
      .attr('stroke-width', 1.5)

    // Hover effect
    nodeG
      .on('mouseenter', function (event, d) {
        d3.select(this).select('circle')
          .transition().duration(150)
          .attr('fill-opacity', 0.35)
          .attr('r', getNodeRadius(d) + 2)
      })
      .on('mouseleave', function (event, d) {
        d3.select(this).select('circle')
          .transition().duration(150)
          .attr('fill-opacity', 0.15)
          .attr('r', getNodeRadius(d))
      })

    // ── Simulation tick ────────────────────────────────────────────────────
    simulation.on('tick', () => {
      link
        .attr('x1', (d) => d.source.x)
        .attr('y1', (d) => d.source.y)
        .attr('x2', (d) => d.target.x)
        .attr('y2', (d) => d.target.y)

      edgeLabel
        .attr('x', (d) => (d.source.x + d.target.x) / 2)
        .attr('y', (d) => (d.source.y + d.target.y) / 2)

      nodeG.attr('transform', (d) => `translate(${d.x},${d.y})`)
    })

    // Click on SVG background deselects
    svg.on('click', () => onNodeClick && onNodeClick(null))

    // Zoom-to-fit helper on first settle
    let fitted = false
    simulation.on('end', () => {
      if (fitted) return
      fitted = true
      // Auto-fit the graph
      const bounds = zoomGroup.node().getBBox()
      if (bounds.width === 0 || bounds.height === 0) return
      const padding = 60
      const scale = Math.min(
        (width - padding * 2) / bounds.width,
        (height - padding * 2) / bounds.height,
        1.2
      )
      const tx = (width - scale * (bounds.x * 2 + bounds.width)) / 2
      const ty = (height - scale * (bounds.y * 2 + bounds.height)) / 2
      svg.transition().duration(600).call(
        zoom.transform,
        d3.zoomIdentity.translate(tx, ty).scale(scale)
      )
    })
  }, [nodes, edges, onNodeClick])

  // Initial build + rebuild on data change
  useEffect(() => {
    buildGraph()
    return () => {
      if (simulationRef.current) simulationRef.current.stop()
    }
  }, [buildGraph])

  // ResizeObserver to handle container resize
  useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver(() => buildGraph())
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [buildGraph])

  return (
    <div ref={containerRef} className="w-full h-full relative bg-bg overflow-hidden">
      {nodes.length === 0 ? (
        <div className="absolute inset-0 flex items-center justify-center text-muted text-sm">
          No graph data available
        </div>
      ) : (
        <svg
          ref={svgRef}
          className="w-full h-full"
          style={{ display: 'block' }}
        />
      )}

      {/* Zoom controls */}
      {nodes.length > 0 && (
        <div className="absolute top-4 right-4 flex flex-col gap-1">
          <button
            onClick={() => {
              const svg = d3.select(svgRef.current)
              svg.transition().call(d3.zoom().scaleBy, 1.3)
            }}
            className="w-8 h-8 rounded-md bg-surface border border-border text-muted hover:text-white hover:border-accent/40 transition-all flex items-center justify-center text-sm font-bold"
            title="Zoom in"
          >
            +
          </button>
          <button
            onClick={() => {
              const svg = d3.select(svgRef.current)
              svg.transition().call(d3.zoom().scaleBy, 0.77)
            }}
            className="w-8 h-8 rounded-md bg-surface border border-border text-muted hover:text-white hover:border-accent/40 transition-all flex items-center justify-center text-sm font-bold"
            title="Zoom out"
          >
            −
          </button>
          <button
            onClick={() => {
              const svg = d3.select(svgRef.current)
              svg.transition().call(d3.zoom().transform, d3.zoomIdentity)
            }}
            className="w-8 h-8 rounded-md bg-surface border border-border text-muted hover:text-white hover:border-accent/40 transition-all flex items-center justify-center"
            title="Reset zoom"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M1 1h4v4M11 1H7v4M1 11h4V7M11 11H7V7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      )}
    </div>
  )
}

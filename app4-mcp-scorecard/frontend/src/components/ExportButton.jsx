import React, { useState } from 'react'

export default function ExportButton({ targetId = 'results-view' }) {
  const [loading, setLoading] = useState(false)

  const handleExport = async () => {
    setLoading(true)
    try {
      // Dynamic imports to keep bundle lean
      const html2canvas = (await import('html2canvas')).default
      const { jsPDF } = await import('jspdf')

      const element = document.getElementById(targetId)
      if (!element) throw new Error('Results element not found')
      await document.fonts.ready
      // CSS animations restart in html2canvas's clone. Freeze only that clone;
      // otherwise staggered dimension cards disappear from an immediate export.

      const canvas = await html2canvas(element, {
        backgroundColor: '#0A0E1A',
        scale: 2,
        useCORS: true,
        logging: false,
        onclone: (document) => {
          document.querySelectorAll(`#${targetId}, #${targetId} *`).forEach(node => {
            node.style.transition = 'none'
            if (document.defaultView.getComputedStyle(node).animationName !== 'none') {
              node.style.animation = 'none'
              node.style.opacity = '1'
              node.style.transform = 'none'
            }
            if (node.dataset.reportWidth) node.style.width = node.dataset.reportWidth
            if (node.dataset.reportOffset) {
              node.style.strokeDashoffset = node.dataset.reportOffset
              node.setAttribute('stroke-dashoffset', node.dataset.reportOffset)
            }
          })
        },
      })

      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'px',
        format: [canvas.width / 2, canvas.height / 2],
      })

      pdf.addImage(imgData, 'PNG', 0, 0, canvas.width / 2, canvas.height / 2)
      pdf.save(`mcp-trust-scorecard-${Date.now()}.pdf`)
    } catch (err) {
      console.error('PDF export failed:', err)
      alert('PDF export failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      data-html2canvas-ignore="true"
      onClick={handleExport}
      disabled={loading}
      className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-surface border border-border text-sm font-500 text-white hover:border-accent hover:text-accent transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {loading ? (
        <>
          <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          Exporting…
        </>
      ) : (
        <>
          <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
          Export PDF
        </>
      )}
    </button>
  )
}

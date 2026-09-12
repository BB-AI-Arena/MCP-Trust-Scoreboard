import React, { useState } from 'react'

export default function ExportButton() {
  const [exporting, setExporting] = useState(false)
  const [done, setDone] = useState(false)

  const handleExport = async () => {
    if (exporting) return
    setExporting(true)
    setDone(false)

    try {
      // Dynamic imports to avoid bundling issues
      const html2canvas = (await import('html2canvas')).default
      const { jsPDF } = await import('jspdf')

      const el = document.getElementById('blast-results')
      if (!el) {
        console.error('Export target element #blast-results not found')
        setExporting(false)
        return
      }

      // Temporarily hide the right sidebar's scrollbar for clean capture
      const originalOverflow = el.style.overflow
      el.style.overflow = 'hidden'

      const canvas = await html2canvas(el, {
        backgroundColor: '#0A0E1A',
        scale: 1.5,
        useCORS: true,
        logging: false,
        allowTaint: true,
        windowWidth: el.scrollWidth,
        windowHeight: el.scrollHeight,
        ignoreElements: (element) => {
          // Ignore floating panels and controls during export
          return element.classList?.contains('fixed') && !element.id?.includes('blast')
        },
      })

      el.style.overflow = originalOverflow

      const imgData = canvas.toDataURL('image/jpeg', 0.92)
      const pdf = new jsPDF({
        orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
        unit: 'px',
        format: [canvas.width, canvas.height],
        compress: true,
      })

      // Add content
      pdf.addImage(imgData, 'JPEG', 0, 0, canvas.width, canvas.height)

      // Add metadata footer
      const now = new Date().toISOString().split('T')[0]
      pdf.setFontSize(9)
      pdf.setTextColor(107, 122, 153)
      pdf.text(
        `Agent Trust Platform — Blast Radius Visualizer — Generated ${now}`,
        20,
        canvas.height - 10
      )

      pdf.save(`blast-radius-report-${now}.pdf`)
      setDone(true)
      setTimeout(() => setDone(false), 3000)
    } catch (err) {
      console.error('PDF export failed:', err)
      alert('Export failed. Check browser console for details.')
    } finally {
      setExporting(false)
    }
  }

  return (
    <button
      data-html2canvas-ignore="true"
      onClick={handleExport}
      disabled={exporting}
      className={[
        'inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-semibold transition-all duration-200',
        done
          ? 'border-success/40 bg-success/10 text-success'
          : 'border-accent/30 bg-accent/5 text-accent hover:bg-accent/10 hover:border-accent/50',
        exporting ? 'opacity-70 cursor-not-allowed' : 'cursor-pointer',
      ].join(' ')}
      title="Export as PDF report"
    >
      {exporting ? (
        <>
          <svg className="animate-spin" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="7" cy="7" r="5" stroke="currentColor" strokeWidth="1.5" strokeOpacity="0.25" />
            <path d="M12 7A5 5 0 007 2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          Exporting...
        </>
      ) : done ? (
        <>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 7l4 4 6-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Saved!
        </>
      ) : (
        <>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1v8M4 6l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M1 10v2a1 1 0 001 1h10a1 1 0 001-1v-2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Export PDF Report
        </>
      )}
    </button>
  )
}

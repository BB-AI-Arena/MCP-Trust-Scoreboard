import React, { useState, useRef, useCallback } from 'react'

export default function InputCard({ onScan, error }) {
  const [url, setUrl] = useState('')
  const [dragging, setDragging] = useState(false)
  const [fileName, setFileName] = useState(null)
  const [manifest, setManifest] = useState(null)
  const fileRef = useRef(null)

  const parseFile = (file) => {
    if (!file) return
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const parsed = JSON.parse(e.target.result)
        setManifest(parsed)
        setFileName(file.name)
        setUrl('')
      } catch {
        alert('Invalid JSON file — please drop a valid MCP manifest.')
      }
    }
    reader.readAsText(file)
  }

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) parseFile(file)
  }, [])

  const onDragOver = (e) => { e.preventDefault(); setDragging(true) }
  const onDragLeave = () => setDragging(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!url && !manifest) return
    onScan(url || null, manifest || null)
  }

  const clearFile = () => {
    setManifest(null)
    setFileName(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  const canScan = url.trim() || manifest

  return (
    <div className="w-full max-w-xl mx-auto animate-fade-in">
      {/* Logo */}
      <div className="flex flex-col items-center mb-10">
        <div className="flex items-center gap-3 mb-3">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-label="MCP Trust Scoreboard">
            <rect width="40" height="40" rx="10" fill="#00D4FF" fillOpacity="0.12"/>
            <path d="M20 8L32 14.5V25.5L20 32L8 25.5V14.5L20 8Z" stroke="#00D4FF" strokeWidth="1.5" fill="none"/>
            <path d="M20 13L27 16.75V24.25L20 28L13 24.25V16.75L20 13Z" fill="#00D4FF" fillOpacity="0.2" stroke="#00D4FF" strokeWidth="1"/>
            <path d="M17 20L19.5 22.5L23.5 18" stroke="#00FF9C" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <div>
            <h1 className="text-xl font-800 text-white tracking-tight leading-none">MCP Trust Scoreboard</h1>
            <p className="text-xs text-muted mt-0.5">MCP Security Dashboard</p>
          </div>
        </div>
        <p className="text-sm text-muted text-center max-w-sm leading-relaxed">
          Assess Model Context Protocol servers, tools, permissions, identity, network references, and trust evidence.
        </p>
        <p className="text-xs text-muted text-center max-w-sm mt-2 leading-relaxed">
          Current assessment uses a submitted JSON manifest and its claimed top-level tools and permissions. Stdio and Streamable HTTP discovery are planned.
        </p>
      </div>

      {/* Card */}
      <form
        onSubmit={handleSubmit}
        className="bg-card card-border rounded-2xl p-6 flex flex-col gap-4"
      >
        {/* URL Input */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs font-500 text-muted uppercase tracking-wider">Manifest JSON URL</label>
          <input
            type="url"
            value={url}
            onChange={(e) => { setUrl(e.target.value); if (manifest) clearFile() }}
            placeholder="https://mcp-server.example.com/manifest.json"
            disabled={!!manifest}
            className="w-full bg-surface border border-border rounded-lg px-4 py-3 text-sm text-white placeholder-muted focus:outline-none focus:border-accent transition-colors duration-200 disabled:opacity-40"
          />
        </div>

        {/* Divider */}
        <div className="flex items-center gap-3">
          <div className="flex-1 h-px bg-border" />
          <span className="text-xs text-muted font-500">OR</span>
          <div className="flex-1 h-px bg-border" />
        </div>

        {/* Drop Zone */}
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={() => !manifest && fileRef.current?.click()}
          className={`relative flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed py-6 px-4 cursor-pointer transition-all duration-200 select-none
            ${dragging ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/50 hover:bg-surface/50'}
            ${manifest ? 'cursor-default' : ''}
          `}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".json"
            className="hidden"
            onChange={(e) => parseFile(e.target.files[0])}
          />
          {manifest ? (
            <div className="flex items-center gap-3 w-full">
              <svg viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5 text-success flex-shrink-0">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
              </svg>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-500 text-white truncate">{fileName}</p>
                <p className="text-xs text-muted">Manifest loaded</p>
              </div>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); clearFile() }}
                className="text-muted hover:text-white transition-colors p-1"
              >
                <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd"/>
                </svg>
              </button>
            </div>
          ) : (
            <>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-8 h-8 text-muted">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
              </svg>
              <div className="text-center">
                <p className="text-sm font-500 text-white">Drop manifest JSON here</p>
                <p className="text-xs text-muted mt-0.5">or click to browse</p>
              </div>
            </>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 bg-red-950/30 border border-danger/30 rounded-lg px-3 py-2.5">
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 text-danger flex-shrink-0 mt-0.5">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
            </svg>
            <p className="text-xs text-red-300 leading-relaxed">{error}</p>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={!canScan}
          className="w-full py-3 rounded-xl font-600 text-sm tracking-wide transition-all duration-200
            bg-accent text-bg hover:brightness-110 active:scale-[0.98]
            disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:brightness-100
            glow-accent"
        >
          Analyze MCP Server
        </button>
      </form>
    </div>
  )
}

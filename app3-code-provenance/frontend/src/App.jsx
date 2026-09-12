import React, { useState, useEffect, useCallback } from 'react';
import CodeUpload from './components/CodeUpload.jsx';
import ProvenanceMap from './components/ProvenanceMap.jsx';
import RiskBreakdown from './components/RiskBreakdown.jsx';
import SnippetViewer from './components/SnippetViewer.jsx';
import ReportExport from './components/ReportExport.jsx';
import { legacyResult } from './legacyResult.js';

// ─── Nav links ───────────────────────────────────────────────
const NAV_LINKS = [
  { label: 'Blast Radius', href: '#blast-radius' },
  { label: 'Behavior Baseline', href: '#behavior-baseline' },
  { label: 'Code Provenance', href: '#code-provenance', active: true },
  { label: 'MCP Scorecard', href: '#mcp-scorecard' },
];

// ─── Scanning messages ────────────────────────────────────────
const SCAN_MESSAGES = [
  'Parsing code...',
  'Detecting AI signatures...',
  'Scanning for vulnerabilities...',
  'Running Gemini analysis...',
  'Generating report...',
];

export default function App() {
  const [appState, setAppState] = useState('idle'); // idle | scanning | results
  const [scanProgress, setScanProgress] = useState(0);
  const [scanMessageIdx, setScanMessageIdx] = useState(0);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null); // for repo view

  // Cycle scanning messages
  useEffect(() => {
    if (appState !== 'scanning') return;
    const interval = setInterval(() => {
      setScanMessageIdx((i) => (i + 1) % SCAN_MESSAGES.length);
    }, 1400);
    return () => clearInterval(interval);
  }, [appState]);

  // Animate progress bar
  useEffect(() => {
    if (appState !== 'scanning') return;
    setScanProgress(0);
    const start = Date.now();
    const duration = 7000; // 7 seconds typical scan
    const raf = requestAnimationFrame(function tick() {
      const elapsed = Date.now() - start;
      const p = Math.min(95, (elapsed / duration) * 100);
      setScanProgress(p);
      if (p < 95) requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(raf);
  }, [appState]);

  const handleScan = useCallback(async ({ code, language, filename, type }) => {
    setError(null);
    setResults(null);
    setSelectedFile(null);
    setAppState('scanning');
    setScanMessageIdx(0);

    try {
      let data;
      if (type === 'repo') {
        // FormData upload for zip
        const formData = new FormData();
        formData.append('file', code); // code is a File object here
        const res = await fetch('/scan-repo', {
          method: 'POST',
          body: formData,
        });
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        data = await res.json();
      } else {
        // JSON payload for single file / pasted code
        const res = await fetch('/scan', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, language, filename: filename || 'snippet.py' }),
        });
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        data = await res.json();
      }

      setScanProgress(100);
      await new Promise((r) => setTimeout(r, 400));
      setResults(type === 'repo'
        ? { ...data, files: data.files.map(file => legacyResult(file)), type }
        : { ...legacyResult(data, code), type });
      setAppState('results');
    } catch (err) {
      setError(err.message || 'Scan failed');
      setAppState('idle');
    }
  }, []);

  const handleReset = () => {
    setAppState('idle');
    setResults(null);
    setError(null);
    setSelectedFile(null);
  };

  return (
    <div className="min-h-screen bg-bg text-white flex flex-col">
      {/* ── Header ─────────────────────────────────────────── */}
      <header className="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-[1400px] mx-auto px-6 h-14 flex items-center justify-between gap-6">
          {/* Logo / App Suite */}
          <div className="flex items-center gap-2.5 shrink-0">
            <PlatformIcon />
            <span className="font-semibold text-sm text-white tracking-tight">
              Agent Trust Platform
            </span>
          </div>

          {/* Center title */}
          <div className="hidden md:flex flex-col items-center">
            <span className="text-xs text-muted uppercase tracking-widest font-medium">
              App 3
            </span>
            <span className="text-sm font-semibold text-accent tracking-tight">
              Artifact Assurance
            </span>
          </div>

          {/* Nav */}
          <nav className="hidden lg:flex items-center gap-1">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                className={[
                  'px-3 py-1.5 rounded text-xs font-medium transition-colors',
                  link.active
                    ? 'text-accent bg-accent/10 border border-accent/30'
                    : 'text-muted hover:text-white hover:bg-surface',
                ].join(' ')}
              >
                {link.label}
              </a>
            ))}
          </nav>
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────────── */}
      <main className="flex-1 max-w-[1400px] mx-auto w-full px-6 py-10">
        {/* Error banner */}
        {error && (
          <div className="mb-6 flex items-center gap-3 bg-danger/10 border border-danger/30 rounded-lg px-4 py-3 text-sm text-danger animate-fade-in">
            <ErrorIcon />
            <span>{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-muted hover:text-white"
            >
              ✕
            </button>
          </div>
        )}

        {/* IDLE: Upload UI */}
        {appState === 'idle' && (
          <div className="flex flex-col items-center animate-fade-in">
            <div className="mb-8 text-center">
              <h1 className="text-2xl font-bold text-white mb-2">
                Code Provenance Tracker
              </h1>
              <p className="text-muted text-sm max-w-xl">
                Detect AI-generated code, identify the generating model, surface
                security vulnerabilities and review evidence-backed artifact assurance —
                for single files or entire repositories.
              </p>
            </div>
            <CodeUpload onScan={handleScan} />
          </div>
        )}

        {/* SCANNING: Progress UI */}
        {appState === 'scanning' && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] animate-fade-in">
            <div className="w-full max-w-md">
              {/* Animated orb */}
              <div className="flex justify-center mb-8">
                <div className="relative w-20 h-20">
                  <div className="absolute inset-0 rounded-full border-2 border-accent/30 animate-ping" />
                  <div className="absolute inset-2 rounded-full border-2 border-accent/60 animate-spin-slow" />
                  <div className="absolute inset-4 rounded-full bg-accent/20 flex items-center justify-center">
                    <ScanIcon />
                  </div>
                </div>
              </div>

              {/* Message */}
              <p className="text-center text-accent font-medium text-lg mb-6 min-h-[1.75rem] transition-all">
                {SCAN_MESSAGES[scanMessageIdx]}
              </p>

              {/* Progress bar */}
              <div className="bg-surface rounded-full h-2 overflow-hidden mb-3">
                <div
                  className="h-full bg-gradient-to-r from-accent to-success rounded-full transition-all duration-300"
                  style={{ width: `${scanProgress}%` }}
                />
              </div>
              <p className="text-muted text-xs text-right">{Math.round(scanProgress)}%</p>

              {/* Sub-steps */}
              <div className="mt-6 space-y-2">
                {SCAN_MESSAGES.map((msg, i) => (
                  <div
                    key={msg}
                    className={[
                      'flex items-center gap-3 text-sm px-3 py-2 rounded-lg transition-all',
                      i < scanMessageIdx
                        ? 'text-success'
                        : i === scanMessageIdx
                        ? 'text-white bg-surface'
                        : 'text-muted/40',
                    ].join(' ')}
                  >
                    <span className="w-4 shrink-0">
                      {i < scanMessageIdx ? '✓' : i === scanMessageIdx ? '›' : '·'}
                    </span>
                    {msg}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* RESULTS */}
        {appState === 'results' && results && (
          <div id="provenance-results" className="animate-slide-up">
            <p role="note">Experimental stylistic signals — not verified authorship or an approval gate. Hosted analysis may be unavailable.</p>
            {/* Results header bar */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleReset}
                  className="flex items-center gap-2 text-muted hover:text-white text-sm transition-colors"
                >
                  ← New Scan
                </button>
                <span className="text-border">|</span>
                <span className="text-sm text-muted">
                  {results.type === 'repo'
                    ? `Repository scan — ${results.files?.length ?? 0} files`
                    : `File: ${results.filename || 'snippet'}`}
                </span>
              </div>
              <ReportExport />
            </div>

            {/* REPO view */}
            {results.type === 'repo' ? (
              <div className="space-y-6">
                {/* Top row: treemap + risk breakdown */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <ProvenanceMap
                    files={results.files || []}
                    onFileClick={(f) => setSelectedFile(f)}
                  />
                  <RiskBreakdown results={results} />
                </div>

                {/* Selected file snippet */}
                {selectedFile && (
                  <div className="animate-slide-up">
                    <SnippetViewer result={selectedFile} />
                  </div>
                )}

                {/* Per-file table */}
                <FileTable
                  files={results.files || []}
                  onSelect={(f) => setSelectedFile(f)}
                  selectedFile={selectedFile}
                />
              </div>
            ) : (
              /* SINGLE FILE view */
              <div className="space-y-6">
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
                  <div className="xl:col-span-2">
                    <SnippetViewer result={results} />
                  </div>
                  <div>
                    <ProvenanceResult result={results} />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* ── Footer ─────────────────────────────────────────── */}
      <footer className="border-t border-border py-4 px-6 text-center text-muted text-xs">
        Agent Trust Platform · Artifact Assurance · Optional provider analysis
      </footer>
    </div>
  );
}

/* ─── ProvenanceResult (single-file sidebar) ──────────────── */
function ProvenanceResult({ result }) {
  const model = result.provenance?.model || 'Unknown';
  const confidence = result.provenance?.confidence ?? 0;
  const risk = result.risk_level || 'low';
  const findings = result.findings || [];

  const modelColors = {
    'Claude': '#7C3AED',
    'GPT-4': '#10B981',
    'Gemini': '#F59E0B',
    'Copilot': '#3B82F6',
    'Human': '#6B7280',
    'Unknown': '#374151',
  };
  const modelColor = modelColors[model] || '#6B7280';

  const riskColors = {
    safe: '#00FF9C', low: '#00AA66', medium: '#FFB800',
    high: '#FF4444', critical: '#FF0066',
  };
  const riskColor = riskColors[risk] || '#6B7280';

  return (
    <div className="bg-card border border-border rounded-xl p-5 space-y-5">
      <h2 className="font-semibold text-sm text-muted uppercase tracking-widest">
        Provenance Analysis
      </h2>

      {/* Model badge */}
      <div className="flex items-center gap-3 p-3 rounded-lg bg-surface">
        <div className="w-3 h-3 rounded-full shrink-0" style={{ background: modelColor }} />
        <div>
          <div className="font-semibold text-white">{model}</div>
          <div className="text-xs text-muted">{confidence}% confidence</div>
        </div>
        <div className="ml-auto text-right">
          <div className="text-xs text-muted">Risk Level</div>
          <div className="font-semibold text-sm uppercase" style={{ color: riskColor }}>
            {risk}
          </div>
        </div>
      </div>

      {/* Confidence bar */}
      <div>
        <div className="flex justify-between text-xs text-muted mb-1.5">
          <span>AI Confidence</span>
          <span>{confidence}%</span>
        </div>
        <div className="bg-surface rounded-full h-1.5">
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${confidence}%`, background: modelColor }}
          />
        </div>
      </div>

      {/* Findings */}
      {findings.length > 0 && (
        <div>
          <h3 className="text-xs text-muted uppercase tracking-widest mb-3">
            Findings ({findings.length})
          </h3>
          <div className="space-y-2">
            {findings.map((f, i) => (
              <FindingChip key={i} finding={f} />
            ))}
          </div>
        </div>
      )}

      {/* Gemini summary */}
      {result.gemini_summary && (
        <div className="p-3 rounded-lg bg-surface border border-border/50">
          <div className="text-xs text-muted mb-1">Gemini Summary</div>
          <p className="text-sm text-white/80 leading-relaxed">{result.gemini_summary}</p>
        </div>
      )}
    </div>
  );
}

function FindingChip({ finding }) {
  const colors = {
    medium: { bg: 'bg-warning/10', text: 'text-warning', border: 'border-warning/20' },
    high: { bg: 'bg-danger/10', text: 'text-danger', border: 'border-danger/20' },
    critical: { bg: 'bg-critical/10', text: 'text-critical', border: 'border-critical/20' },
    low: { bg: 'bg-success/10', text: 'text-success', border: 'border-success/20' },
  };
  const c = colors[finding.severity] || colors.low;
  return (
    <div className={`text-xs px-3 py-2 rounded-lg border ${c.bg} ${c.border}`}>
      <div className={`font-semibold ${c.text} mb-0.5`}>
        {finding.type} · Line {finding.line}
      </div>
      <div className="text-white/70">{finding.description}</div>
    </div>
  );
}

/* ─── File Table (repo view) ──────────────────────────────── */
function FileTable({ files, onSelect, selectedFile }) {
  if (!files.length) return null;

  const riskOrder = { critical: 0, high: 1, medium: 2, low: 3, safe: 4 };
  const sorted = [...files].sort(
    (a, b) => (riskOrder[a.risk_level] ?? 5) - (riskOrder[b.risk_level] ?? 5)
  );

  const riskColors = {
    safe: 'text-success', low: 'text-green-400', medium: 'text-warning',
    high: 'text-danger', critical: 'text-critical',
  };

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
        <h2 className="font-semibold text-sm text-white">Scanned Files</h2>
        <span className="text-xs text-muted">{files.length} files</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {['File', 'Language', 'Model', 'Confidence', 'Risk', 'Findings'].map((h) => (
                <th key={h} className="px-4 py-2.5 text-left text-xs text-muted font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((file, i) => {
              const isSelected = selectedFile?.filename === file.filename;
              return (
                <tr
                  key={i}
                  onClick={() => onSelect(file)}
                  className={[
                    'border-b border-border/50 cursor-pointer transition-colors',
                    isSelected ? 'bg-accent/5 border-accent/20' : 'hover:bg-surface',
                  ].join(' ')}
                >
                  <td className="px-4 py-3 font-mono text-xs text-accent truncate max-w-[200px]">
                    {file.filename}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted">{file.language || '—'}</td>
                  <td className="px-4 py-3 text-xs text-white">
                    {file.provenance?.model || 'Unknown'}
                  </td>
                  <td className="px-4 py-3 text-xs text-muted">
                    {file.provenance?.confidence ?? '—'}%
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs font-semibold uppercase ${
                        riskColors[file.risk_level] || 'text-muted'
                      }`}
                    >
                      {file.risk_level || 'unknown'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted">
                    {file.findings?.length ?? 0}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ─── Icons ───────────────────────────────────────────────── */
function PlatformIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M4 12 C4 7 20 7 20 12 C20 17 4 17 4 12Z" stroke="#00D4FF" strokeWidth="1.5" fill="none" />
      <circle cx="12" cy="12" r="2" fill="#00D4FF" />
      <path d="M3 9 L6 12 L3 15" stroke="#00FF9C" strokeWidth="1.5" fill="none" strokeLinecap="round" />
    </svg>
  );
}

function ScanIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="10" cy="10" r="6" stroke="#00D4FF" strokeWidth="1.5" />
      <path d="M10 7 L10 10 L12 12" stroke="#00D4FF" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="8" cy="8" r="7" stroke="#FF4444" strokeWidth="1.5" />
      <path d="M8 5 L8 8.5" stroke="#FF4444" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="8" cy="11" r="0.75" fill="#FF4444" />
    </svg>
  );
}

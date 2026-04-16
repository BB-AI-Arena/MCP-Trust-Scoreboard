import React, { useEffect, useRef, useState, useMemo } from 'react';
import hljs from 'highlight.js/lib/core';
import python from 'highlight.js/lib/languages/python';
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import go from 'highlight.js/lib/languages/go';
import java from 'highlight.js/lib/languages/java';
import rust from 'highlight.js/lib/languages/rust';

// Register languages
hljs.registerLanguage('python', python);
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('go', go);
hljs.registerLanguage('java', java);
hljs.registerLanguage('rust', rust);

const MODEL_COLORS = {
  Claude: '#7C3AED',
  'GPT-4': '#10B981',
  Gemini: '#F59E0B',
  Copilot: '#3B82F6',
  Human: '#6B7280',
  Unknown: '#374151',
};

const VERDICT_CONFIG = {
  APPROVE: { color: '#00FF9C', bg: 'bg-success/10', border: 'border-success/30', icon: '✓' },
  REVIEW:  { color: '#FFB800', bg: 'bg-warning/10', border: 'border-warning/30', icon: '⚠' },
  REJECT:  { color: '#FF4444', bg: 'bg-danger/10',  border: 'border-danger/30',  icon: '✕' },
};

const SEVERITY_STYLES = {
  critical: { line: 'risk-line-critical', badge: 'bg-critical/10 text-critical border-critical/30' },
  high:     { line: 'risk-line-high',     badge: 'bg-danger/10 text-danger border-danger/30' },
  medium:   { line: 'risk-line-medium',   badge: 'bg-warning/10 text-warning border-warning/30' },
  low:      { line: '',                   badge: 'bg-success/10 text-success border-success/30' },
};

function getHljsLang(lang) {
  const map = {
    Python: 'python', JavaScript: 'javascript', TypeScript: 'typescript',
    Go: 'go', Java: 'java', Rust: 'rust',
    py: 'python', js: 'javascript', ts: 'typescript',
    go: 'go', java: 'java', rs: 'rust',
  };
  return map[lang] || map[lang?.toLowerCase()] || 'python';
}

export default function SnippetViewer({ result }) {
  const codeRef = useRef(null);
  const [activeTooltip, setActiveTooltip] = useState(null);

  const code = result?.code || result?.source_code || '';
  const language = result?.language || 'Python';
  const model = result?.provenance?.model || 'Unknown';
  const confidence = result?.provenance?.confidence ?? 0;
  const findings = useMemo(() => result?.findings || [], [result]);
  const verdict = result?.gemini_verdict || result?.verdict || null;
  const verdictExplanation = result?.gemini_explanation || result?.explanation || '';
  const filename = result?.filename || '';

  const modelColor = MODEL_COLORS[model] || '#6B7A99';
  const hljsLang = getHljsLang(language);

  // Highlight code
  const highlighted = useMemo(() => {
    if (!code) return '';
    try {
      return hljs.highlight(code, { language: hljsLang }).value;
    } catch {
      return hljs.highlightAuto(code).value;
    }
  }, [code, hljsLang]);

  // Build line-indexed findings map
  const findingsByLine = useMemo(() => {
    const map = {};
    findings.forEach((f) => {
      const line = f.line || f.line_number;
      if (line != null) {
        if (!map[line]) map[line] = [];
        map[line].push(f);
      }
    });
    return map;
  }, [findings]);

  // Split into lines for annotation
  const lines = useMemo(() => highlighted.split('\n'), [highlighted]);

  if (!code) {
    return (
      <div className="bg-card border border-border rounded-xl p-6 text-center text-muted text-sm">
        No code available to display
      </div>
    );
  }

  const vc = verdict ? VERDICT_CONFIG[verdict.toUpperCase()] : null;

  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-border flex items-center justify-between gap-4">
        <div className="flex items-center gap-2 min-w-0">
          {filename && (
            <span className="font-mono text-xs text-muted truncate max-w-[200px]">
              {filename}
            </span>
          )}
          <span className="text-xs text-muted/50 hidden sm:inline">·</span>
          <span className="text-xs text-muted hidden sm:inline">{language}</span>
        </div>

        {/* Provenance badge */}
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium shrink-0"
          style={{
            background: `${modelColor}14`,
            borderColor: `${modelColor}30`,
            color: modelColor,
          }}
        >
          <span
            className="w-2 h-2 rounded-full shrink-0"
            style={{ background: modelColor }}
          />
          <span>{model}</span>
          <span className="text-white/40 font-normal">{confidence}%</span>
        </div>
      </div>

      {/* Gemini verdict banner */}
      {vc && (
        <div
          className={`flex items-start gap-3 px-5 py-3 border-b ${vc.bg} ${vc.border} border-x-0 border-t-0`}
        >
          <span
            className="text-base font-bold shrink-0 mt-0.5"
            style={{ color: vc.color }}
          >
            {vc.icon}
          </span>
          <div>
            <span
              className="text-xs font-bold uppercase tracking-widest"
              style={{ color: vc.color }}
            >
              Gemini Verdict: {verdict.toUpperCase()}
            </span>
            {verdictExplanation && (
              <p className="text-xs text-white/70 mt-0.5 leading-relaxed">
                {verdictExplanation}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Findings summary bar */}
      {findings.length > 0 && (
        <div className="flex items-center gap-2 px-5 py-2 border-b border-border/50 flex-wrap">
          <span className="text-xs text-muted shrink-0">
            {findings.length} finding{findings.length !== 1 ? 's' : ''}:
          </span>
          {['critical', 'high', 'medium', 'low'].map((sev) => {
            const count = findings.filter((f) => f.severity === sev).length;
            if (!count) return null;
            const styles = SEVERITY_STYLES[sev];
            return (
              <span
                key={sev}
                className={`text-xs px-2 py-0.5 rounded border ${styles.badge}`}
              >
                {count} {sev}
              </span>
            );
          })}
        </div>
      )}

      {/* Code with annotations */}
      <div className="relative overflow-auto max-h-[560px] code-block-wrapper rounded-none border-0">
        <table className="w-full border-collapse text-xs font-mono">
          <tbody>
            {lines.map((lineHtml, idx) => {
              const lineNum = idx + 1;
              const lineFindings = findingsByLine[lineNum] || [];
              const topSeverity = lineFindings.reduce((acc, f) => {
                const order = { critical: 0, high: 1, medium: 2, low: 3 };
                return (order[f.severity] ?? 99) < (order[acc] ?? 99) ? f.severity : acc;
              }, null);
              const rowClass = topSeverity ? SEVERITY_STYLES[topSeverity]?.line || '' : '';

              return (
                <React.Fragment key={idx}>
                  <tr className={`group relative ${rowClass}`}>
                    {/* Line number */}
                    <td className="select-none text-right pr-4 pl-4 py-0 text-muted/40 min-w-[3.5rem] align-top border-r border-border/30 bg-[#0D1117]">
                      <span className="leading-[1.7]">{lineNum}</span>
                    </td>

                    {/* Code cell */}
                    <td className="pl-4 pr-12 py-0 bg-[#0D1117] align-top relative">
                      <pre
                        className="hljs whitespace-pre"
                        style={{ background: 'transparent', padding: 0, margin: 0, fontSize: '0.8125rem', lineHeight: '1.7' }}
                        dangerouslySetInnerHTML={{ __html: lineHtml || ' ' }}
                      />

                      {/* Finding markers */}
                      {lineFindings.length > 0 && (
                        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
                          {lineFindings.map((f, fi) => {
                            const styles = SEVERITY_STYLES[f.severity] || SEVERITY_STYLES.low;
                            return (
                              <button
                                key={fi}
                                className={`text-[9px] px-1.5 py-0.5 rounded border font-bold uppercase leading-none ${styles.badge} hover:opacity-80 transition-opacity`}
                                onMouseEnter={(e) => {
                                  const rect = e.currentTarget.getBoundingClientRect();
                                  const tableRect = e.currentTarget.closest('table').getBoundingClientRect();
                                  setActiveTooltip({
                                    finding: f,
                                    top: rect.bottom - tableRect.top + 6,
                                    right: tableRect.right - rect.right,
                                  });
                                }}
                                onMouseLeave={() => setActiveTooltip(null)}
                              >
                                {f.severity.slice(0, 3)}
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </td>
                  </tr>
                </React.Fragment>
              );
            })}
          </tbody>
        </table>

        {/* Floating tooltip */}
        {activeTooltip && (
          <div
            className="absolute z-50 bg-surface border border-border rounded-lg p-3 shadow-2xl text-xs max-w-[280px] pointer-events-none"
            style={{
              top: activeTooltip.top,
              right: activeTooltip.right,
            }}
          >
            <div
              className={`font-semibold mb-1 uppercase text-[10px] tracking-wide ${
                SEVERITY_STYLES[activeTooltip.finding.severity]?.badge.split(' ')[1] || 'text-muted'
              }`}
            >
              {activeTooltip.finding.severity} · {activeTooltip.finding.type}
            </div>
            <p className="text-white/80 leading-relaxed mb-2">
              {activeTooltip.finding.description}
            </p>
            {activeTooltip.finding.remediation && (
              <div className="border-t border-border/50 pt-2">
                <span className="text-muted text-[10px] uppercase tracking-wide block mb-0.5">
                  Remediation
                </span>
                <p className="text-success/80 leading-relaxed">
                  {activeTooltip.finding.remediation}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

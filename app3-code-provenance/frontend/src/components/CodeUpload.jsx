import React, { useState, useRef, useCallback } from 'react';

const LANGUAGES = ['Python', 'JavaScript', 'TypeScript', 'Go', 'Java', 'Rust'];

const SUSPICIOUS_SNIPPET = `# config.py — suspicious snippet for demo
import os
import subprocess

# Placeholder values are intentionally non-secret demo strings.
AWS_ACCESS_KEY = "replace-with-secret"
AWS_SECRET_KEY = "replace-with-secret"
DB_PASSWORD = "replace-with-secret"
API_TOKEN = "replace-with-secret"

def run_user_command(user_input):
    # CRITICAL: eval() on untrusted input
    result = eval(user_input)
    return result

def execute_shell(cmd):
    # HIGH: shell injection risk
    output = subprocess.run(cmd, shell=True, capture_output=True)
    return output.stdout.decode()

def load_config(path):
    # MEDIUM: unsafe deserialization
    import pickle
    with open(path, "rb") as f:
        return pickle.load(f)

class DataProcessor:
    def process(self, data):
        # Potential SQL injection
        query = "SELECT * FROM users WHERE id = " + str(data)
        return query
`;

const LANG_EXTENSIONS = {
  py: 'Python', js: 'JavaScript', jsx: 'JavaScript', ts: 'TypeScript',
  tsx: 'TypeScript', go: 'Go', java: 'Java', rs: 'Rust',
};

function detectLangFromFilename(name) {
  const ext = name.split('.').pop()?.toLowerCase();
  return LANG_EXTENSIONS[ext] || 'Python';
}

export default function CodeUpload({ onScan }) {
  const [activeTab, setActiveTab] = useState('paste');
  const [code, setCode] = useState(SUSPICIOUS_SNIPPET);
  const [language, setLanguage] = useState('Python');
  const [filename, setFilename] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [repoFile, setRepoFile] = useState(null);
  const [repoDragOver, setRepoDragOver] = useState(false);
  const [fileDragOver, setFileDragOver] = useState(false);
  const [repoFileList, setRepoFileList] = useState([]);

  const fileRef = useRef();
  const repoRef = useRef();

  // ── Handlers ────────────────────────────────────────────────
  const handleFileDrop = useCallback((e) => {
    e.preventDefault();
    setFileDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) processCodeFile(f);
  }, []);

  const processCodeFile = (f) => {
    setUploadedFile(f);
    setFilename(f.name);
    const detectedLang = detectLangFromFilename(f.name);
    setLanguage(detectedLang);
    const reader = new FileReader();
    reader.onload = (e) => setCode(e.target.result || '');
    reader.readAsText(f);
  };

  const handleRepoDrop = useCallback((e) => {
    e.preventDefault();
    setRepoDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f && f.name.endsWith('.zip')) processRepoFile(f);
  }, []);

  const processRepoFile = (f) => {
    setRepoFile(f);
    // Show approximate file count hint from zip name
    setRepoFileList([f.name]);
  };

  const handleScan = () => {
    if (activeTab === 'paste' || activeTab === 'file') {
      onScan({ code, language, filename: filename || 'snippet.py', type: 'file' });
    } else if (activeTab === 'repo' && repoFile) {
      onScan({ code: repoFile, language: '', filename: repoFile.name, type: 'repo' });
    }
  };

  const canScan =
    (activeTab === 'paste' && code.trim().length > 0) ||
    (activeTab === 'file' && uploadedFile) ||
    (activeTab === 'repo' && repoFile);

  return (
    <div className="w-full max-w-2xl">
      <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-2xl shadow-black/40">
        {/* ── Tab bar ──────────────────────────────────────── */}
        <div className="flex border-b border-border">
          {[
            { id: 'paste', label: 'Paste Code', icon: '{ }' },
            { id: 'file', label: 'Upload File', icon: '↑' },
            { id: 'repo', label: 'Upload Repo (.zip)', icon: '⊞' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={[
                'flex items-center gap-2 px-5 py-3.5 text-sm font-medium transition-colors',
                activeTab === tab.id
                  ? 'text-accent border-b-2 border-accent bg-accent/5'
                  : 'text-muted hover:text-white hover:bg-surface',
              ].join(' ')}
            >
              <span className="font-mono text-xs opacity-70">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-5 space-y-4">
          {/* ── Paste Code tab ─────────────────────────────── */}
          {activeTab === 'paste' && (
            <>
              {/* Controls row */}
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <label className="block text-xs text-muted mb-1.5">Language</label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent/60 transition-colors"
                  >
                    {LANGUAGES.map((l) => (
                      <option key={l} value={l}>{l}</option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="block text-xs text-muted mb-1.5">
                    Filename <span className="opacity-50">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={filename}
                    onChange={(e) => setFilename(e.target.value)}
                    placeholder="e.g. config.py"
                    className="w-full bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white placeholder-muted focus:outline-none focus:border-accent/60 transition-colors"
                  />
                </div>
              </div>

              {/* Code textarea */}
              <div>
                <label className="block text-xs text-muted mb-1.5">Code</label>
                <textarea
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  rows={16}
                  spellCheck={false}
                  className="w-full bg-[#0D1117] border border-border rounded-lg px-4 py-3 text-xs font-mono text-white/90 placeholder-muted/40 focus:outline-none focus:border-accent/50 resize-y transition-colors leading-relaxed"
                  placeholder="Paste code here..."
                />
                <div className="flex justify-between text-xs text-muted mt-1">
                  <span>{code.split('\n').length} lines</span>
                  <span>{code.length} chars</span>
                </div>
              </div>
            </>
          )}

          {/* ── Upload File tab ─────────────────────────────── */}
          {activeTab === 'file' && (
            <div
              className={`drop-zone rounded-xl p-8 flex flex-col items-center justify-center gap-4 cursor-pointer text-center min-h-[220px] transition-all ${fileDragOver ? 'drag-over' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setFileDragOver(true); }}
              onDragLeave={() => setFileDragOver(false)}
              onDrop={handleFileDrop}
              onClick={() => fileRef.current?.click()}
            >
              <input
                ref={fileRef}
                type="file"
                className="hidden"
                accept=".py,.js,.jsx,.ts,.tsx,.go,.java,.rs,.rb,.php,.cpp,.c,.h,.cs"
                onChange={(e) => e.target.files[0] && processCodeFile(e.target.files[0])}
              />

              {uploadedFile ? (
                <>
                  <div className="w-12 h-12 rounded-full bg-success/10 border border-success/30 flex items-center justify-center">
                    <span className="text-success text-xl">✓</span>
                  </div>
                  <div>
                    <div className="text-white font-medium">{uploadedFile.name}</div>
                    <div className="text-muted text-sm mt-1">
                      {(uploadedFile.size / 1024).toFixed(1)} KB · {language}
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setUploadedFile(null); setCode(''); }}
                    className="text-xs text-muted hover:text-danger transition-colors"
                  >
                    Remove file
                  </button>
                </>
              ) : (
                <>
                  <div className="w-14 h-14 rounded-xl bg-surface border border-border flex items-center justify-center">
                    <UploadIcon />
                  </div>
                  <div>
                    <div className="text-white font-medium text-sm">
                      Drop a code file here
                    </div>
                    <div className="text-muted text-xs mt-1">
                      .py, .js, .ts, .go, .java, .rs supported
                    </div>
                  </div>
                  <div className="text-xs text-accent/60 border border-accent/20 rounded-full px-3 py-1">
                    or click to browse
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── Upload Repo tab ─────────────────────────────── */}
          {activeTab === 'repo' && (
            <div
              className={`drop-zone rounded-xl p-8 flex flex-col items-center justify-center gap-4 cursor-pointer text-center min-h-[220px] transition-all ${repoDragOver ? 'drag-over' : ''}`}
              onDragOver={(e) => { e.preventDefault(); setRepoDragOver(true); }}
              onDragLeave={() => setRepoDragOver(false)}
              onDrop={handleRepoDrop}
              onClick={() => repoRef.current?.click()}
            >
              <input
                ref={repoRef}
                type="file"
                className="hidden"
                accept=".zip"
                onChange={(e) => e.target.files[0] && processRepoFile(e.target.files[0])}
              />

              {repoFile ? (
                <>
                  <div className="w-12 h-12 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center">
                    <ZipIcon />
                  </div>
                  <div>
                    <div className="text-white font-medium">{repoFile.name}</div>
                    <div className="text-muted text-sm mt-1">
                      {(repoFile.size / 1024).toFixed(1)} KB
                    </div>
                  </div>
                  <div className="text-xs text-success bg-success/10 border border-success/20 rounded-full px-3 py-1">
                    Ready to scan
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setRepoFile(null); setRepoFileList([]); }}
                    className="text-xs text-muted hover:text-danger transition-colors"
                  >
                    Remove
                  </button>
                </>
              ) : (
                <>
                  <div className="w-14 h-14 rounded-xl bg-surface border border-border flex items-center justify-center">
                    <ZipIcon />
                  </div>
                  <div>
                    <div className="text-white font-medium text-sm">
                      Drop your repository .zip here
                    </div>
                    <div className="text-muted text-xs mt-1">
                      The zip will be extracted and each code file scanned individually
                    </div>
                  </div>
                  <div className="text-xs text-accent/60 border border-accent/20 rounded-full px-3 py-1">
                    .zip files only · or click to browse
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── Scan button ─────────────────────────────────── */}
          <button
            onClick={handleScan}
            disabled={!canScan}
            className={[
              'w-full py-3.5 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2.5',
              canScan
                ? 'bg-accent text-bg hover:bg-accent/90 shadow-lg shadow-accent/20 hover:shadow-accent/30'
                : 'bg-surface text-muted cursor-not-allowed',
            ].join(' ')}
          >
            <ScanStartIcon />
            Scan for Provenance
          </button>

          {/* Hint */}
          <p className="text-center text-xs text-muted/60">
            Detects AI-generated code · Identifies model · Surfaces vulnerabilities
          </p>
        </div>
      </div>
    </div>
  );
}

function UploadIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#6B7A99" strokeWidth="1.5" strokeLinecap="round">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function ZipIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#00D4FF" strokeWidth="1.5" strokeLinecap="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="12" y1="12" x2="12" y2="18" />
      <line x1="9" y1="15" x2="15" y2="15" />
    </svg>
  );
}

function ScanStartIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <circle cx="8" cy="8" r="6" />
      <path d="M5 8 L7.5 10.5 L11 6" />
    </svg>
  );
}

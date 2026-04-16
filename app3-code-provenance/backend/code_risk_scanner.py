"""
code_risk_scanner.py
Security risk scanner for source code.
Uses regex patterns to identify common vulnerability classes.
No external API calls — pure static analysis.
"""

import re
from typing import Dict, List, Any, Tuple


# ---------------------------------------------------------------------------
# Severity weights for risk scoring
# ---------------------------------------------------------------------------

SEVERITY_WEIGHTS: Dict[str, int] = {
    "critical": 40,
    "high": 20,
    "medium": 10,
    "low": 5,
}


# ---------------------------------------------------------------------------
# Rule definitions
# Each rule: type, severity, pattern, description, remediation
# ---------------------------------------------------------------------------

RULES: List[Dict[str, Any]] = [
    # ---- Hardcoded secrets ----
    {
        "type": "Hardcoded API Key",
        "severity": "critical",
        "pattern": r"(?i)(?:api[_\-]?key|apikey)\s*=\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
        "description": "Hardcoded API key detected. Credentials embedded in source code can be exposed in version control.",
        "remediation": "Store API keys in environment variables or a secrets manager. Use os.environ.get('API_KEY') or a library like python-dotenv.",
    },
    {
        "type": "Hardcoded Password",
        "severity": "critical",
        "pattern": r"(?i)(?:password|passwd|pwd)\s*=\s*['\"][^'\"]{4,}['\"]",
        "description": "Hardcoded password detected. Plaintext passwords in code are a critical security risk.",
        "remediation": "Never hardcode passwords. Use environment variables, a secrets vault (e.g., HashiCorp Vault), or OS keyring.",
    },
    {
        "type": "Hardcoded Secret/Token",
        "severity": "critical",
        "pattern": r"(?i)(?:secret|token|auth[_\-]?token|access[_\-]?token|bearer)\s*=\s*['\"][A-Za-z0-9_\-\.]{8,}['\"]",
        "description": "Hardcoded secret or token detected. Tokens exposed in code can be exploited by attackers.",
        "remediation": "Move secrets to environment variables or a dedicated secrets management service.",
    },
    # ---- SQL Injection ----
    {
        "type": "SQL Injection (f-string)",
        "severity": "critical",
        "pattern": r'f["\'](?i)SELECT\s[\s\S]*?\{[\w\s\.\[\]]+\}[\s\S]*?["\']',
        "description": "Potential SQL injection via f-string interpolation. User-controlled data in SQL queries enables injection attacks.",
        "remediation": "Use parameterized queries or an ORM. Replace string interpolation with query parameters: cursor.execute('SELECT ... WHERE id = %s', (user_id,))",
    },
    {
        "type": "SQL Injection (concatenation)",
        "severity": "critical",
        "pattern": r'(?i)["\']SELECT\s[\s\S]*?["\'\s]\s*\+\s*\w+',
        "description": "Potential SQL injection via string concatenation. Never concatenate user input into SQL queries.",
        "remediation": "Use parameterized queries or prepared statements instead of string concatenation.",
    },
    # ---- eval/exec usage ----
    {
        "type": "Dangerous eval() Usage",
        "severity": "high",
        "pattern": r"\beval\s*\(",
        "description": "Use of eval() can execute arbitrary code. If user input reaches eval(), this is a remote code execution vulnerability.",
        "remediation": "Avoid eval(). Use ast.literal_eval() for safe evaluation of literals, or redesign to not require dynamic evaluation.",
    },
    {
        "type": "Dangerous exec() Usage",
        "severity": "high",
        "pattern": r"\bexec\s*\(",
        "description": "Use of exec() can execute arbitrary Python code. Especially dangerous with user-controlled input.",
        "remediation": "Avoid exec(). Redesign the feature to use explicit logic instead of dynamic code execution.",
    },
    {
        "type": "Dynamic __import__()",
        "severity": "high",
        "pattern": r"\b__import__\s*\(",
        "description": "Dynamic __import__() can load arbitrary modules, potentially enabling code injection.",
        "remediation": "Use explicit import statements or importlib.import_module() with a strict allowlist of permitted module names.",
    },
    # ---- Shell injection ----
    {
        "type": "Shell Command via os.system()",
        "severity": "high",
        "pattern": r"\bos\.system\s*\(",
        "description": "os.system() spawns a shell and is vulnerable to shell injection if input is not sanitized.",
        "remediation": "Use subprocess.run() with a list of arguments (not a string) and shell=False to avoid shell injection.",
    },
    {
        "type": "Shell Injection via subprocess shell=True",
        "severity": "high",
        "pattern": r"\bsubprocess\.\w+\s*\([^)]*shell\s*=\s*True",
        "description": "subprocess called with shell=True enables shell injection attacks if any argument contains user input.",
        "remediation": "Pass a list of arguments to subprocess and set shell=False (the default). Validate all external input before use.",
    },
    {
        "type": "Shell Command via os.popen()",
        "severity": "high",
        "pattern": r"\bos\.popen\s*\(",
        "description": "os.popen() executes a shell command and is deprecated. Vulnerable to shell injection.",
        "remediation": "Replace with subprocess.run() using a list of arguments and shell=False.",
    },
    # ---- Unsafe deserialization ----
    {
        "type": "Unsafe pickle.loads()",
        "severity": "critical",
        "pattern": r"\bpickle\.loads?\s*\(",
        "description": "pickle.loads() on untrusted data can execute arbitrary code. A critical deserialization vulnerability.",
        "remediation": "Never unpickle data from untrusted sources. Use JSON, MessagePack, or another safe serialization format for untrusted data.",
    },
    {
        "type": "Unsafe yaml.load() Without Loader",
        "severity": "high",
        "pattern": r"\byaml\.load\s*\(\s*(?!.*Loader\s*=\s*yaml\.(?:SafeLoader|BaseLoader))[^)]*\)",
        "description": "yaml.load() without an explicit safe Loader can deserialize arbitrary Python objects.",
        "remediation": "Use yaml.safe_load() or yaml.load(data, Loader=yaml.SafeLoader) to prevent deserialization attacks.",
    },
    # ---- Overly broad permissions ----
    {
        "type": "Overly Broad File Permissions (chmod 777)",
        "severity": "high",
        "pattern": r"\bchmod\s+(?:777|0o777|0777)\b",
        "description": "Setting permissions to 777/rwxrwxrwx grants full access to all users. This violates the principle of least privilege.",
        "remediation": "Use the minimum necessary permissions. For files, 644 (rw-r--r--) is typical; for executables, 755 (rwxr-xr-x).",
    },
    {
        "type": "Overly Broad Permissions Pattern (rwxrwxrwx)",
        "severity": "high",
        "pattern": r"rwxrwxrwx",
        "description": "rwxrwxrwx grants full read/write/execute to owner, group, and world.",
        "remediation": "Restrict permissions to the minimum required. Avoid world-writable or world-executable files.",
    },
    # ---- Deprecated / unsafe functions ----
    {
        "type": "Deprecated md5 Hash Usage",
        "severity": "medium",
        "pattern": r"\bhashlib\.md5\s*\(",
        "description": "MD5 is cryptographically broken and should not be used for security purposes.",
        "remediation": "Use SHA-256 or stronger: hashlib.sha256(). For passwords, use bcrypt, scrypt, or argon2.",
    },
    {
        "type": "Deprecated sha1 Hash Usage",
        "severity": "medium",
        "pattern": r"\bhashlib\.sha1\s*\(",
        "description": "SHA-1 is deprecated for security uses. Collision attacks are practical.",
        "remediation": "Use SHA-256 or stronger: hashlib.sha256().",
    },
    {
        "type": "Use of assert for Security Checks",
        "severity": "medium",
        "pattern": r"\bassert\s+.+(?:auth|perm|access|admin|login|role|token|valid)",
        "description": "assert statements are removed when Python runs with the -O flag. Do not use assert for security-critical checks.",
        "remediation": "Replace assert with explicit if/raise checks: if not condition: raise PermissionError(...)",
    },
    {
        "type": "Deprecated random Module for Security",
        "severity": "medium",
        "pattern": r"\brandom\.(?:random|randint|randrange|choice|shuffle)\s*\(",
        "description": "The random module is not cryptographically secure. Do not use it for tokens, passwords, or security nonces.",
        "remediation": "Use the secrets module for cryptographically secure random values: secrets.token_hex(), secrets.choice().",
    },
    # ---- Hardcoded IPs/URLs ----
    {
        "type": "Hardcoded Non-Localhost IP Address",
        "severity": "medium",
        "pattern": r'["\'](?!(?:127\.0\.0\.1|0\.0\.0\.0|::1|localhost))(?:\d{1,3}\.){3}\d{1,3}["\']',
        "description": "Hardcoded IP address detected. Non-localhost IPs embedded in code may expose internal infrastructure.",
        "remediation": "Move IP addresses and hostnames to configuration files or environment variables.",
    },
    {
        "type": "Hardcoded HTTP URL (Non-HTTPS)",
        "severity": "low",
        "pattern": r'["\']http://(?!localhost|127\.0\.0\.1)[^"\']{5,}["\']',
        "description": "Hardcoded HTTP (non-HTTPS) URL detected. Unencrypted connections can expose data in transit.",
        "remediation": "Use HTTPS URLs wherever possible. Avoid hardcoding URLs; use configuration or environment variables.",
    },
    # ---- Logging sensitive data ----
    {
        "type": "Potential Sensitive Data in Logs",
        "severity": "medium",
        "pattern": r'(?:print|log(?:ger)?\.(?:info|debug|warning|error|critical))\s*\([^)]*(?:password|token|secret|key|credential)[^)]*\)',
        "description": "Potentially sensitive data (password, token, secret) may be written to logs.",
        "remediation": "Never log sensitive data. Mask or omit credentials from log output.",
    },
    # ---- Open redirect ----
    {
        "type": "Potential Open Redirect",
        "severity": "medium",
        "pattern": r'redirect\s*\(\s*(?:request\.|req\.)[\w\.]+\s*\)',
        "description": "Potential open redirect: redirecting to a URL derived from user-controlled request data.",
        "remediation": "Validate redirect targets against an allowlist of trusted URLs or use relative paths only.",
    },
    # ---- Debug mode ----
    {
        "type": "Debug Mode Enabled",
        "severity": "low",
        "pattern": r"(?i)\bdebug\s*=\s*True\b",
        "description": "Debug mode appears to be enabled. Debug mode in production exposes stack traces and internal details.",
        "remediation": "Set debug=False in production. Control debug mode via environment variables.",
    },
]


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _get_line_and_column(code: str, match_start: int) -> Tuple[int, int]:
    """
    Compute 1-based line and column numbers for a character offset.

    Args:
        code: Full source code string.
        match_start: Character offset of the match start.

    Returns:
        Tuple of (line_number, column_number), both 1-based.
    """
    lines_before = code[:match_start].split("\n")
    line = len(lines_before)
    column = len(lines_before[-1]) + 1
    return line, column


def _get_code_snippet(code: str, line_number: int, context: int = 1) -> str:
    """
    Extract a code snippet centered on a given line.

    Args:
        code: Full source code string.
        line_number: 1-based line number of the finding.
        context: Number of surrounding lines to include on each side.

    Returns:
        Multi-line string snippet.
    """
    lines = code.split("\n")
    start = max(0, line_number - 1 - context)
    end = min(len(lines), line_number + context)
    snippet_lines = lines[start:end]
    return "\n".join(snippet_lines)


def _risk_level_from_score(score: int) -> str:
    """
    Map a numeric risk score to a human-readable risk level.

    Args:
        score: Integer risk score (0-100).

    Returns:
        One of: "Safe", "Low", "Medium", "High", "Critical".
    """
    if score == 0:
        return "Safe"
    elif score <= 20:
        return "Low"
    elif score <= 50:
        return "Medium"
    elif score <= 80:
        return "High"
    else:
        return "Critical"


def _build_summary(findings: List[Dict[str, Any]], risk_level: str, score: int) -> str:
    """
    Generate a human-readable summary of scan results.

    Args:
        findings: List of finding dicts from the scan.
        risk_level: Risk level string.
        score: Numeric risk score.

    Returns:
        Summary string.
    """
    if not findings:
        return f"No security issues detected. Risk level: {risk_level} (score: {score}/100)."

    severity_counts: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f.get("severity", "low")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    parts = []
    for sev in ("critical", "high", "medium", "low"):
        count = severity_counts[sev]
        if count > 0:
            parts.append(f"{count} {sev}")

    finding_summary = ", ".join(parts)
    return (
        f"Found {len(findings)} issue(s): {finding_summary}. "
        f"Risk level: {risk_level} (score: {score}/100)."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_code(code: str, language: str) -> dict:
    """
    Scan source code for security vulnerabilities using static pattern analysis.

    Args:
        code: The source code string to scan.
        language: Programming language (informational; patterns currently target
                  Python but several rules are language-agnostic).

    Returns:
        A dict with keys:
          - risk_level (str): "Safe", "Low", "Medium", "High", or "Critical".
          - findings (list): List of finding dicts.
          - score (int): Aggregate risk score (0-100).
          - summary (str): Human-readable summary.
    """
    if not code or not code.strip():
        return {
            "risk_level": "Safe",
            "findings": [],
            "score": 0,
            "summary": "No code provided to scan.",
        }

    findings: List[Dict[str, Any]] = []
    raw_score = 0

    for rule in RULES:
        try:
            for match in re.finditer(rule["pattern"], code, re.MULTILINE):
                line, column = _get_line_and_column(code, match.start())
                snippet = _get_code_snippet(code, line)
                findings.append({
                    "type": rule["type"],
                    "severity": rule["severity"],
                    "line": line,
                    "column": column,
                    "description": rule["description"],
                    "code_snippet": snippet,
                    "remediation": rule["remediation"],
                })
                # Only score the first occurrence of each rule type to avoid
                # inflating the score for repeated patterns of the same class
                raw_score += SEVERITY_WEIGHTS.get(rule["severity"], 0)
                break  # one hit per rule for scoring
        except re.error:
            continue

    score = min(100, raw_score)
    risk_level = _risk_level_from_score(score)
    summary = _build_summary(findings, risk_level, score)

    return {
        "risk_level": risk_level,
        "findings": findings,
        "score": score,
        "summary": summary,
    }

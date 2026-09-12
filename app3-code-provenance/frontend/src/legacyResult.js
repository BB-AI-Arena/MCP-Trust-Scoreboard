// Keep backend responses stable; adapt their nested fields for existing views.
export function legacyResult(data, code = '') {
  return {
    ...data, code,
    provenance: { ...data.provenance, model: data.provenance?.likely_model || 'Unknown' },
    risk_level: data.risks?.risk_level?.toLowerCase() || 'unknown',
    findings: (data.risks?.findings || []).map(f => ({ ...f, severity: f.severity.toLowerCase() })),
    explanation: data.gemini?.explanation || '',
  };
}

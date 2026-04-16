"""
main.py
FastAPI backend for the Vibe Code Provenance Tracker.
Exposes endpoints for single-file and repository-level analysis.
"""

import io
import os
import zipfile
import logging
import tempfile
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from provenance_detector import detect_provenance
from code_risk_scanner import scan_code
from gemini_analyzer import analyze_snippet

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Vibe Code Provenance Tracker",
    description="Analyze source code for AI origin and security vulnerabilities.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:5174","http://localhost:5175","http://localhost:5176","http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES = ["Python", "JavaScript", "TypeScript", "Go", "Java", "Rust"]

EXTENSION_TO_LANGUAGE: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".java": "Java",
    ".rs": "Rust",
}

SCANNABLE_EXTENSIONS = set(EXTENSION_TO_LANGUAGE.keys())


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    code: str
    language: str
    filename: Optional[str] = None


class ScanResponse(BaseModel):
    filename: str
    language: str
    provenance: Dict[str, Any]
    risks: Dict[str, Any]
    gemini: Dict[str, Any]


# ---------------------------------------------------------------------------
# Helper: language detection from filename
# ---------------------------------------------------------------------------

def _language_from_filename(filename: str) -> str:
    """
    Infer programming language from a filename's extension.

    Args:
        filename: File name, possibly including path.

    Returns:
        Language string, or "Unknown" if the extension is not recognized.
    """
    _, ext = os.path.splitext(filename.lower())
    return EXTENSION_TO_LANGUAGE.get(ext, "Unknown")


# ---------------------------------------------------------------------------
# Helper: run full analysis pipeline on a code string
# ---------------------------------------------------------------------------

async def _analyze(code: str, language: str, filename: str) -> Dict[str, Any]:
    """
    Run the full provenance + risk + Gemini analysis pipeline.

    Args:
        code: Source code string.
        language: Programming language name.
        filename: Display filename for the result.

    Returns:
        Analysis result dict.
    """
    provenance = detect_provenance(code, language)
    risks = scan_code(code, language)
    gemini = await analyze_snippet(code, provenance, risks)

    return {
        "filename": filename,
        "language": language,
        "provenance": provenance,
        "risks": risks,
        "gemini": gemini,
    }


# ---------------------------------------------------------------------------
# Helper: aggregate repo-level summary
# ---------------------------------------------------------------------------

def _build_repo_summary(file_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute aggregate statistics across all scanned files.

    Args:
        file_results: List of per-file analysis result dicts.

    Returns:
        Summary dict with ai_generated_pct, most_common_model,
        highest_risk_file, and risk_distribution.
    """
    if not file_results:
        return {
            "ai_generated_pct": 0.0,
            "most_common_model": "Unknown",
            "highest_risk_file": "",
            "risk_distribution": {},
        }

    # AI-generated percentage: models other than "Human" and "Unknown"
    ai_models = {"Claude", "GPT-4", "Gemini", "Copilot"}
    ai_count = sum(
        1 for r in file_results
        if r.get("provenance", {}).get("likely_model") in ai_models
    )
    ai_generated_pct = round((ai_count / len(file_results)) * 100, 1)

    # Most common model
    model_counts: Dict[str, int] = {}
    for r in file_results:
        model = r.get("provenance", {}).get("likely_model", "Unknown")
        model_counts[model] = model_counts.get(model, 0) + 1
    most_common_model = max(model_counts, key=lambda m: model_counts[m])

    # Highest risk file (by score)
    highest_risk_file = max(
        file_results,
        key=lambda r: r.get("risks", {}).get("score", 0),
    ).get("filename", "")

    # Risk distribution
    risk_distribution: Dict[str, int] = {}
    for r in file_results:
        level = r.get("risks", {}).get("risk_level", "Safe")
        risk_distribution[level] = risk_distribution.get(level, 0) + 1

    return {
        "ai_generated_pct": ai_generated_pct,
        "most_common_model": most_common_model,
        "highest_risk_file": highest_risk_file,
        "risk_distribution": risk_distribution,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        {"status": "ok"}
    """
    return {"status": "ok"}


@app.get("/languages")
async def get_languages():
    """
    Return the list of supported programming languages.

    Returns:
        List of language name strings.
    """
    return SUPPORTED_LANGUAGES


@app.post("/scan", response_model=ScanResponse)
async def scan_single(request: ScanRequest):
    """
    Scan a single code snippet for AI provenance and security risks.

    Accepts:
        - code: Source code string (required).
        - language: Programming language (required).
        - filename: Optional display filename.

    Returns:
        Full analysis result with provenance, risks, and Gemini verdict.
    """
    if not request.code or not request.code.strip():
        raise HTTPException(status_code=422, detail="'code' field must not be empty.")

    if request.language not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported language '{request.language}'. "
                   f"Supported: {', '.join(SUPPORTED_LANGUAGES)}",
        )

    filename = request.filename or f"snippet.{request.language.lower()}"

    logger.info("Scanning single file: %s (%s)", filename, request.language)

    try:
        result = await _analyze(request.code, request.language, filename)
        return result
    except Exception as exc:
        logger.exception("Error scanning file %s: %s", filename, exc)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}")


@app.post("/scan-repo")
async def scan_repo(file: UploadFile = File(...)):
    """
    Scan all source files in an uploaded ZIP archive.

    Accepts:
        - file: multipart/form-data ZIP file upload.

    Returns:
        Aggregate report with per-file results and summary statistics.
    """
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=422,
            detail="Uploaded file must be a .zip archive.",
        )

    logger.info("Received ZIP archive for repo scan: %s", file.filename)

    try:
        zip_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read uploaded file: {str(exc)}")

    if len(zip_bytes) == 0:
        raise HTTPException(status_code=422, detail="Uploaded ZIP file is empty.")

    file_results: List[Dict[str, Any]] = []
    errors: List[Dict[str, str]] = []

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            # Collect scannable entries
            entries = [
                name for name in zf.namelist()
                if not name.endswith("/")
                and os.path.splitext(name.lower())[1] in SCANNABLE_EXTENSIONS
            ]

            logger.info("ZIP contains %d scannable file(s).", len(entries))

            if not entries:
                return {
                    "total_files": 0,
                    "files": [],
                    "summary": {
                        "ai_generated_pct": 0.0,
                        "most_common_model": "Unknown",
                        "highest_risk_file": "",
                        "risk_distribution": {},
                    },
                    "message": "No scannable source files found in the archive.",
                }

            for entry_name in entries:
                try:
                    raw = zf.read(entry_name)
                    # Attempt UTF-8 decoding; skip binary files
                    try:
                        code = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                            code = raw.decode("latin-1")
                        except UnicodeDecodeError:
                            errors.append({
                                "filename": entry_name,
                                "error": "Could not decode file as text.",
                            })
                            continue

                    # Determine language from extension
                    _, ext = os.path.splitext(entry_name.lower())
                    language = EXTENSION_TO_LANGUAGE.get(ext, "Unknown")

                    # Use only the basename for display
                    display_name = os.path.basename(entry_name) or entry_name

                    result = await _analyze(code, language, display_name)
                    # Preserve full path for reference
                    result["path"] = entry_name
                    file_results.append(result)

                except Exception as exc:
                    logger.warning("Error scanning %s: %s", entry_name, exc)
                    errors.append({"filename": entry_name, "error": str(exc)})

    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=422,
            detail="Uploaded file is not a valid ZIP archive.",
        )
    except Exception as exc:
        logger.exception("Unexpected error processing ZIP: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to process archive: {str(exc)}")

    summary = _build_repo_summary(file_results)

    response: Dict[str, Any] = {
        "total_files": len(file_results),
        "files": file_results,
        "summary": summary,
    }

    if errors:
        response["errors"] = errors

    logger.info(
        "Repo scan complete: %d files scanned, %d errors.",
        len(file_results),
        len(errors),
    )

    return response

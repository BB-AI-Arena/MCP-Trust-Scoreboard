"""Bounded, non-secret diagnostics for disposable Windows acceptance failures."""
from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

MAX_JSON_BYTES = 64 * 1024
MAX_INVENTORY_ENTRIES = 64
MAX_SCAN_ENTRIES = 20_000
MAX_NAME_CHARS = 128
MAX_TIMESTAMP_CHARS = 64
MAX_CHECKPOINTS = 16
COUNTER_NUMBER_KEYS = ("sent", "dropped", "expired")
COUNTER_TIMESTAMP_KEYS = ("last_upload",)
COUNTER_KEYS = COUNTER_NUMBER_KEYS + COUNTER_TIMESTAMP_KEYS


def _nonnegative_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _timestamp(value):
    if not isinstance(value, str) or not value or len(value) > MAX_TIMESTAMP_CHARS:
        return None
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value


def _inventory_name(name):
    if name == "counters.json":
        classification = "counters"
    elif name.startswith(".pending-"):
        classification = "pending"
    elif name.endswith(".event"):
        classification = "event"
    else:
        classification = "other"
    return {"name_class": classification, "name_digest": hashlib.sha256(name.encode("utf-8", "surrogatepass")).hexdigest()[:32]}


def _counters(value):
    """Retain only recognized, validated top-level counter fields."""
    if not isinstance(value, dict):
        return None
    result = {}
    for key in COUNTER_NUMBER_KEYS:
        if key in value:
            if not _nonnegative_int(value[key]):
                return None
            result[key] = value[key]
    if "last_upload" in value:
        stamp = value["last_upload"]
        if stamp != "" and _timestamp(stamp) is None:
            return None
        result["last_upload"] = stamp
    return result


def _status(value):
    if not isinstance(value, dict):
        return None
    result = {"missing_fields": []}
    for key in ("updated_at", "pid", "online", "reason", "collectors", "spool_depth", "counters"):
        if key not in value:
            result["missing_fields"].append(key)
    if "updated_at" in value:
        updated_at = _timestamp(value["updated_at"])
        if updated_at is None:
            return None
        result["updated_at"] = updated_at
    if "pid" in value:
        if not _nonnegative_int(value["pid"]):
            return None
        result["pid"] = value["pid"]
    if "spool_depth" in value:
        if not _nonnegative_int(value["spool_depth"]):
            return None
        result["spool_depth"] = value["spool_depth"]
    if "online" in value:
        if not isinstance(value["online"], bool):
            return None
        result["online"] = value["online"]
    # Never persist runtime error text or collector values.
    if "reason" in value:
        result["reason_present"] = value["reason"] is not None
    if "collectors" in value:
        if not isinstance(value["collectors"], (dict, list)):
            return None
        result["collectors_present"] = True
        result["collectors_count"] = len(value["collectors"])
    if "counters" in value:
        counters = _counters(value["counters"])
        if counters is None:
            return None
        result["counters"] = counters
        result["missing_fields"].extend("counters." + key for key in COUNTER_KEYS if key not in counters)
    return result


def _json_evidence(path, transform):
    try:
        with Path(path).open("rb") as source:
            body = source.read(MAX_JSON_BYTES + 1)
    except FileNotFoundError:
        return {"availability": "missing"}
    except OSError:
        return {"availability": "unavailable", "reason": "read_error"}
    if len(body) > MAX_JSON_BYTES:
        return {"availability": "unavailable", "reason": "oversize"}
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"availability": "corrupt"}
    value = transform(value)
    if value is None:
        return {"availability": "corrupt"}
    result = {"availability": "available", "value": value}
    if transform is _counters:
        result["missing_fields"] = [key for key in COUNTER_KEYS if key not in value]
    return result


def spool_inventory(data_dir):
    spool = Path(data_dir) / "spool"
    try:
        with os.scandir(spool) as entries:
            scanned = []
            scan_truncated = False
            for entry in entries:
                if len(scanned) == MAX_SCAN_ENTRIES:
                    scan_truncated = True
                    break
                scanned.append(entry)
    except FileNotFoundError:
        return {"availability": "missing"}
    except OSError:
        return {"availability": "unavailable", "reason": "scan_error"}
    try:
        files = []
        file_count = total_bytes = pending_count = 0
        for entry in scanned:
            if not entry.is_file():
                continue
            stat = entry.stat()
            file_count += 1
            total_bytes += stat.st_size
            if entry.name.startswith(".pending-"):
                pending_count += 1
            if len(files) < MAX_INVENTORY_ENTRIES:
                files.append(_inventory_name(entry.name) | {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns})
    except OSError:
        return {"availability": "unavailable", "reason": "stat_error"}
    return {
        "availability": "available",
        "file_count_lower_bound": file_count,
        "total_bytes_lower_bound": total_bytes,
        "pending_count_lower_bound": pending_count,
        "files": files,
        "output_truncated": file_count > MAX_INVENTORY_ENTRIES,
        "scan_truncated": scan_truncated,
    }


def _captured_at():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _source_binary_identity(value):
    value = value if isinstance(value, dict) else {}
    result = {}
    source_sha = value.get("source_sha")
    if isinstance(source_sha, str) and (source_sha == "local" or re.fullmatch(r"[0-9a-fA-F]{7,64}", source_sha)):
        result["source_sha"] = source_sha
    binary_sha256 = value.get("binary_sha256")
    if isinstance(binary_sha256, str) and re.fullmatch(r"[0-9a-fA-F]{64}", binary_sha256):
        result["binary_sha256"] = binary_sha256
    return result


def checkpoint(phase, data_dir):
    try:
        data_dir = Path(data_dir)
        return {
            "phase": phase,
            "captured_at": _captured_at(),
            "status": _json_evidence(data_dir / "status.json", _status),
            "counters": _json_evidence(data_dir / "spool" / "counters.json", _counters),
            "spool_inventory": spool_inventory(data_dir),
        }
    except BaseException:
        return {"phase": phase, "captured_at": _captured_at(), "availability": "unavailable", "reason": "collection_error"}


def _partial(snapshot):
    if snapshot.get("availability") == "unavailable":
        return True
    for value in snapshot.values():
        if not isinstance(value, dict):
            continue
        if (value.get("availability") != "available" or value.get("missing_fields")
                or value.get("scan_truncated") or value.get("output_truncated")):
            return True
        evidence = value.get("value")
        if isinstance(evidence, dict) and (evidence.get("missing_fields") or ("counters" in evidence and not evidence["counters"])):
            return True
        if value.get("availability") == "available" and isinstance(evidence, dict) and not evidence:
            return True
    return False


def _bounded_checkpoints(checkpoints):
    return list(checkpoints)[-MAX_CHECKPOINTS:]


def persist_checkpoint(evidence_dir, state, phase, data_dir, source_binary_identity):
    """Best-effort running evidence; never lets diagnostic collection fail acceptance."""
    try:
        state["phase"] = phase
        state["data_dir"] = Path(data_dir)
        snapshot = checkpoint(phase, data_dir)
        checkpoints = state.setdefault("checkpoints", [])
        checkpoints.append(snapshot)
        del checkpoints[:-MAX_CHECKPOINTS]
        record = {
            "state": "partial" if _partial(snapshot) else "running",
            "phase": phase,
            "source_binary_identity": _source_binary_identity(source_binary_identity),
            "checkpoints": _bounded_checkpoints(checkpoints),
            "observations": _bounded_checkpoints(state.get("observations", ())),
        }
        destination = Path(evidence_dir) / "checkpoint-diagnostic.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return snapshot
    except BaseException:
        return {"phase": phase, "captured_at": _captured_at(), "availability": "unavailable", "reason": "persistence_error"}


def persist_health_observation(evidence_dir, state, phase, health, source_binary_identity):
    """Persist validated counters from the exact status read used by an assertion."""
    try:
        validated = _status(health)
        observation = {"phase": phase, "captured_at": _captured_at(), "status": {"availability": "available", "value": validated} if validated is not None else {"availability": "corrupt"}}
        observations = state.setdefault("observations", [])
        observations.append(observation)
        del observations[:-MAX_CHECKPOINTS]
        return persist_checkpoint(evidence_dir, state, phase, state.get("data_dir"), source_binary_identity)
    except BaseException:
        return {"phase": phase, "availability": "unavailable", "reason": "observation_error"}


def record_failure(evidence_dir, phase, data_dir, source_binary_identity, error, checkpoints=(), name="failure-diagnostic.json", observations=(), cleanup_failure_types=()):
    """Best-effort failure capture which never masks the acceptance exception."""
    try:
        snapshot = checkpoint(phase, data_dir) if data_dir else {"phase": phase, "captured_at": _captured_at(), "availability": "unavailable", "reason": "data_dir_unset"}
        record = {
            "state": "failed",
            "diagnostics": "partial" if _partial(snapshot) else "complete",
            "phase": phase,
            "error_class": type(error).__name__,
            "source_binary_identity": _source_binary_identity(source_binary_identity),
            "checkpoint": snapshot,
            "checkpoints": _bounded_checkpoints(checkpoints),
            "observations": _bounded_checkpoints(observations),
            "cleanup_failure_types": list(dict.fromkeys(type_name for type_name in cleanup_failure_types if isinstance(type_name, str) and len(type_name) <= MAX_NAME_CHARS)),
        }
        destination = Path(evidence_dir) / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(record, indent=2), encoding="utf-8")
    except BaseException:
        pass


@contextmanager
def capture_before_cleanup(evidence_dir, state, source_binary_identity):
    """Capture the original exception while the caller still owns its workspace."""
    try:
        yield
    except BaseException as error:
        try:
            record_failure(evidence_dir, state.get("phase", "unknown"), state.get("data_dir"), source_binary_identity, error, state.get("checkpoints", ()), observations=state.get("observations", ()))
        except BaseException:
            pass
        raise

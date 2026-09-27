"""Owned by G5. Append-only audit log backing the Audit screen (demo/audit.html).

Interface: record(event: dict) -> None; recent(limit: int = 100) -> list[dict];
backfill() -> int.

record() appends one JSON line (timestamp, kind, matter, summary, counts) to
/Users/dqi26/the-wall/.runtime/audit.jsonl under an exclusive lock and NEVER
raises into the caller's request path. recent() returns newest first.
backfill() seeds initial events from existing evidence
(.runtime/demo_cache/*.json and results/results.json); it is a no-op once the
log is non-empty.
"""

import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path

AUDIT_FILE = Path(os.environ.get("WALL_AUDIT", "/Users/dqi26/the-wall/.runtime/audit.jsonl"))
RUNTIME_DIR = Path(os.environ.get("WALL_RUNTIME", "/Users/dqi26/the-wall/.runtime"))
RESULTS_FILE = Path(os.environ.get("WALL_RESULTS", "/Users/dqi26/the-wall/results/results.json"))

# Timeline kinds: de-identify runs, wall attacks with verdicts, procedures
# scrubbed and promoted, evals recorded.
CACHE_KINDS = {
    "wall": "wall",
    "compound": "promote",
    "deidentify": "deidentify",
    "deid": "deidentify",
    "scrub": "scrub",
}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _numbers(mapping: dict) -> dict:
    counts = {}
    if isinstance(mapping, dict):
        for key, value in mapping.items():
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                counts[str(key)] = value
    return counts


def record(event: dict) -> None:
    """Append one audit event; never raises."""
    try:
        if not isinstance(event, dict):
            event = {}
        entry = {
            "timestamp": event.get("timestamp") or _utcnow(),
            "kind": str(event.get("kind") or "note"),
            "matter": str(event.get("matter") or ""),
            "summary": str(event.get("summary") or ""),
            "counts": _numbers(event.get("counts")),
        }
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_FILE.open("a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(json.dumps(entry, default=str) + "\n")
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception:
        pass


def recent(limit: int = 100) -> list:
    """Newest-first events; never raises."""
    try:
        limit = max(0, int(limit))
    except Exception:
        limit = 100
    try:
        events = []
        for line in AUDIT_FILE.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue
        events.reverse()
        return events[:limit]
    except Exception:
        return []


def _cache_event(stem: str, data: dict, mtime: str) -> dict | None:
    if not isinstance(data, dict):
        return None
    if stem == "wall":
        passed = data.get("passed", "?")
        total = data.get("total", "?")
        return {
            "timestamp": mtime,
            "kind": "wall",
            "matter": "",
            "summary": f"Wall attack held: {passed}/{total} checks passed",
            "counts": _numbers(data),
        }
    kind = CACHE_KINDS.get(stem, "note")
    return {
        "timestamp": mtime,
        "kind": kind,
        "matter": str(data.get("matter") or data.get("target") or ""),
        "summary": f"Demo result replayed from {stem}.json",
        "counts": _numbers(data),
    }


def backfill() -> int:
    """Seed the log from demo_cache + results.json. No-op when non-empty."""
    try:
        if AUDIT_FILE.exists() and AUDIT_FILE.stat().st_size > 0:
            return 0
        seeded = 0
        cache = RUNTIME_DIR / "demo_cache"
        if cache.is_dir():
            for path in sorted(cache.glob("*.json")):
                try:
                    data = json.loads(path.read_text())
                    mtime = datetime.fromtimestamp(
                        path.stat().st_mtime, tz=timezone.utc
                    ).isoformat(timespec="seconds")
                except Exception:
                    continue
                event = _cache_event(path.stem, data, mtime)
                if event is None:
                    continue
                record(event)
                seeded += 1
        try:
            results = json.loads(RESULTS_FILE.read_text()) if RESULTS_FILE.exists() else {}
        except Exception:
            results = {}
        if isinstance(results, dict):
            for detector in sorted(results):
                sets = results[detector]
                if not isinstance(sets, dict):
                    continue
                for eval_set in sorted(sets):
                    row = sets[eval_set]
                    if not isinstance(row, dict):
                        continue
                    caught = row.get("caught", "?")
                    leaks = row.get("leaks", "?")
                    false_alarms = row.get("false_alarms", "?")
                    n = row.get("n", "?")
                    record(
                        {
                            "kind": "eval",
                            "matter": "",
                            "summary": (
                                f"{detector} on {eval_set}: caught "
                                f"{caught}/{leaks}, {false_alarms} false alarms (n={n})"
                            ),
                            "counts": _numbers(row),
                        }
                    )
                    seeded += 1
        return seeded
    except Exception:
        return 0

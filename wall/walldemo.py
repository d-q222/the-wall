"""Owned by F1. Runs the live wall attack for the web demo.

Mirrors walls/attack.py's 5 checks (self-recall, control, blocked search,
clamped __all__, blocked direct page read), generalized to any matter/target
pair via walls.client.Client against the live GBrain server.

Demo-safe rule: cache the last live success under .runtime/demo_cache/wall.json
and replay it (flagged "replayed": true) if the live call fails. Never
fabricate a result that was never produced live.
"""
import json
from pathlib import Path

from walls.client import Client

CACHE = Path(__file__).resolve().parent.parent / ".runtime" / "demo_cache" / "wall.json"


def _check(checks: list, name: str, call: str, result: str, passed: bool) -> None:
    checks.append({"name": name, "call": call, "result": result, "passed": bool(passed)})


def _run_live(matter: str, target: str) -> dict:
    checks: list = []
    attacker = Client(matter)
    victim = Client(target)

    hits = attacker.search(matter)
    _check(checks, f"{matter} recalls its own facts", f'search: "{matter}"',
           f"{len(hits)} hit(s)",
           len(hits) > 0 and {h["source_id"] for h in hits} == {matter})

    hits = victim.search(target)
    _check(checks, f"{target} reads its own file (control)", f'search: "{target}"',
           f"{len(hits)} hit(s) -- the data exists behind the wall", len(hits) > 0)

    hits = attacker.search(target)
    _check(checks, f"{matter} searches for {target}", f'search: "{target}"',
           f"{len(hits)} hit(s)", len(hits) == 0)

    try:
        hits = attacker.search(target, source_id="__all__")
        _check(checks, f"{matter} asks for ALL sources", 'search all sources ("__all__")',
               f"{len(hits)} hit(s) -- clamped to {matter}'s grant", len(hits) == 0)
    except PermissionError as e:
        _check(checks, f"{matter} asks for ALL sources", 'search all sources ("__all__")',
               f"refused: {e}", True)

    page = attacker.get_page("intake", source_id=target)
    err = page.get("error")
    _check(checks, f"{matter} opens {target}'s file directly", f'open: "{target}/intake"',
           err or "PAGE RETURNED -- WALL BREACHED", err == "permission_denied")

    passed = sum(c["passed"] for c in checks)
    return {"checks": checks, "passed": passed, "total": len(checks), "replayed": False}


def attack(matter: str = "chen", target: str = "delmarva") -> dict:
    """{"checks": [{"name", "call", "result", "passed"}], "passed": int, "total": int, "replayed": bool}"""
    try:
        result = _run_live(matter, target)
    except Exception:
        if CACHE.exists():
            cached = json.loads(CACHE.read_text())
            cached["replayed"] = True
            return cached
        raise
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(result))
    return result

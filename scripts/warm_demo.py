"""Warm every live demo flow once so each demo-safe cache holds a real, recent success.

Calls the running API (WALL_API_URL, default http://localhost:8788; never restarts it) and
prints: flow | status | latency | cached-file updated. A flow is "updated" when its own cache
file in the server's .runtime/demo_cache/ changed during its call (other lanes hit the same
server, so unrelated files may change too). Synthetic fixtures only.

    uv run python scripts/warm_demo.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = os.environ.get("WALL_API_URL", "http://localhost:8788").rstrip("/")
ROOT = Path(os.environ.get("WALL_ROOT", "/Users/dqi26/the-wall"))  # the repo the API serves from
CACHE_DIR = ROOT / ".runtime" / "demo_cache"
FIXTURES = ROOT / "fixtures" / "matters"

# Owner lane per flow (docs/DESIGN.md, docs/CONTRACT.md), for the failure report.
OWNERS = {
    "wall": "f1-wall-page",
    "deidentify": "c2-deid",
    "compound": "f2-compound-page",
    "judge": "b2-river",
    "matters": "g4-matters",
    "policy": "g2-policy",
    "audit": "g5-audit",
    "feedback": "k2-loop",
}

# The demo-safe cache file each flow writes; None = no cache path (a live failure errors on stage).
CACHE_FILE = {"wall": "wall.json", "compound": "compound.json", "deidentify": None, "judge": None}

# Self-written synthetic drafts for chen (current) vs delmarva (protected).
JUDGE_DRAFTS = {
    "clean": "Dear Ms. Chen, following our meeting we will prepare the trust accounting and "
    "circulate a draft of the beneficiary notice for your review next week.",
    "verbatim-leak": "As in the Delmarva Logistics dispute, where Hollis Freight Brokers owed "
    "$418,250, we should demand the full amount from Harborview Bank in writing.",
    "paraphrase-leak": "I recall another client whose refrigerated truck sat running in a "
    "Salisbury lot for most of a day; we could use that playbook for the lake house claim.",
}


def cache_mtimes() -> dict[str, float]:
    return {p.name: p.stat().st_mtime for p in CACHE_DIR.glob("*.json")} if CACHE_DIR.exists() else {}


def call(method: str, path: str, body: dict | None = None, timeout: float = 240) -> tuple[str, object]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(API + path, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read() or b"null")
            return str(resp.status), payload
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}", None
    except Exception as e:  # connection refused, timeout
        return f"ERR {type(e).__name__}", None


def replayed(payload: object) -> bool:
    if isinstance(payload, dict):
        return bool(payload.get("replayed")) or any(
            isinstance(s, dict) and s.get("replayed") for s in payload.get("spans") or []
        )
    return False


def run(flow: str, label: str, method: str, path: str, body: dict | None = None) -> dict:
    before = cache_mtimes()
    t0 = time.monotonic()
    status, payload = call(method, path, body)
    latency = time.monotonic() - t0
    after = cache_mtimes()
    changed = sorted(n for n, m in after.items() if before.get(n) != m)
    if status == "200" and replayed(payload):
        status = "200 REPLAYED"
    row = {"flow": label, "kind": flow, "status": status, "latency": latency, "changed": changed, "payload": payload}
    print(f"  {label:<44} {status:<14} {latency:6.1f}s  {', '.join(changed) or 'no'}", file=sys.stderr)
    return row


def main() -> int:
    rows = []
    for m, t in [("chen", "delmarva"), ("o1-almeida", "o1-brandt"), ("o1-umeh", "o1-achterberg")]:
        q = urllib.parse.urlencode({"matter": m, "target": t})
        rows.append(run("wall", f"POST /demo/api/wall {m}->{t}", "POST", f"/demo/api/wall?{q}"))

    rows.append(run("matters", "GET /demo/api/matters", "GET", "/demo/api/matters"))
    matters = rows[-1]["payload"] or []
    for m in matters:
        if m.get("practice") != "immigration":
            continue
        for doc in m.get("documents", []):
            name = doc if isinstance(doc, str) else doc.get("name", "")
            text = (FIXTURES / m["id"] / name).read_text()
            body = {"text": text, "practice": "immigration", "matter_id": m["id"]}
            rows.append(run("deidentify", f"POST /deidentify {m['id']}/{name}", "POST", "/deidentify", body))

    rows.append(run("compound", "POST /demo/api/compound", "POST", "/demo/api/compound"))

    delmarva = next((m for m in matters if m.get("id") == "delmarva"), {})
    protected = [f"delmarva: {json.dumps(delmarva.get('facts', {}))}"]
    for name, draft in JUDGE_DRAFTS.items():
        body = {"current": "chen", "protected": protected, "draft": draft}
        row = run("judge", f"POST /judge {name}", "POST", "/judge", body)
        if isinstance(row["payload"], dict):
            row["status"] += f" ({row['payload'].get('verdict')})"
        rows.append(row)

    for path in ["/demo/api/policy", "/demo/api/audit", "/demo/api/feedback"]:
        rows.append(run(path.rsplit("/", 1)[-1], f"GET {path}", "GET", path))

    print(f"\nWarm run {time.strftime('%H:%M:%S')} against {API}\n")
    print("| flow | status | latency | cached-file updated |")
    print("|---|---|---|---|")
    for r in rows:
        f = CACHE_FILE.get(r["kind"], "")
        upd = "n/a (read-only)" if f == "" else "no cache path" if f is None else "yes" if f in r["changed"] else "no"
        print(f"| {r['flow']} | {r['status']} | {r['latency']:.1f}s | {upd} |")

    failed = [r for r in rows if not r["status"].startswith("200") or "REPLAYED" in r["status"]]
    posts_no_cache = sorted({r["kind"] for r in rows if r["flow"].startswith("POST") and CACHE_FILE.get(r["kind"]) is None})
    print()
    for r in failed:
        print(f"FAIL {r['flow']}: {r['status']} -> owner {OWNERS.get(r['kind'], '?')}")
    for k in posts_no_cache:
        print(f"NO CACHE PATH: {k} (a live failure on stage shows an error) -> owner {OWNERS.get(k, '?')}")
    ok = sum(1 for r in rows if r not in failed)
    print(f"\n{ok}/{len(rows)} flows live OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

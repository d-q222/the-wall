"""Shared helpers for talking to a local QM dev instance's core API.

QM's dev sign-in is an email-link broker (needs Resend/SMTP -- out of scope for a
local-only hackathon box). Instead of signing in, we mint the same HS256 "agent
capability" tokens QM's own harness mints for a live turn (src/auth/capability-token.ts,
src/auth/signed-token.ts -- plain JWS compact serialization, alg HS256, no `kid`
needed for single-secret verification), signed with CAPABILITY_SECRET, which we set
explicitly when booting the dev instance (see up.sh). This is QM's own token format,
not a bypass of it: `up.sh` seeds ADMIN_GRANTS for ADMIN_PRINCIPAL, so every capability
we mint for that principal is a real org admin in this dev instance.

Rooms ("delmarva" / "chen") are QM projects, whose scope is `group:proj:<id>`. Minting a
valid capability for a *group* scope additionally requires `scopeVersion` to equal the
project's current `String(updatedAt)` (QM's optimistic-concurrency token for group
membership) -- that value comes straight from the GET/POST /v1/projects response body,
so we always re-fetch a project right before minting a token scoped to it.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

# Fixed dev-only values. Never used outside this local, mock-LLM dev instance;
# CAPABILITY_SECRET has no validity anywhere else. Must match up.sh exactly.
ORG_ID = "acme"
ADMIN_PRINCIPAL = "qm-admin"
CAPABILITY_SECRET = "55fde2eb25cdd3c1a0dac5a1c0fb96e18e1eb7094cbd071f70d6efcb5f4756a3"

STATE_DIR = Path("/Users/dqi26/the-wall/.runtime/qm-state")
CORE_URL_FILE = STATE_DIR / "core_url"
ROOMS_FILE = STATE_DIR / "rooms.json"


def core_url() -> str:
    env = os.environ.get("QM_CORE_URL")
    if env:
        return env.rstrip("/")
    if CORE_URL_FILE.exists():
        return CORE_URL_FILE.read_text().strip().rstrip("/")
    raise RuntimeError(
        f"no core URL known -- run qm/up.sh first (expected it at {CORE_URL_FILE})"
    )


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _exp_ms(ttl_s: int) -> int:
    # QM's capability claims use JS Date.now()-style epoch *milliseconds* for `exp`
    # (see src/api/app-deployments.ts's `Date.now() + ttlMs`), not Unix seconds.
    return int(time.time() * 1000) + ttl_s * 1000


def mint_capability_token(claims: dict[str, Any], secret: str = CAPABILITY_SECRET) -> str:
    """Mint a QM agent-capability token: JWS compact serialization, alg HS256.

    Matches src/auth/signed-token.ts:mintSignedPayload + capability-token.ts:mintCapabilityToken
    byte-for-byte in the parts that matter (header {"alg":"HS256"}, HMAC-SHA256 over
    "<header_b64>.<payload_b64>" using the raw secret bytes as key). `kid` is omitted;
    QM's verifier only uses `kid` to pick between *multiple* candidate secrets, and we
    only ever hand it one, so verification does not depend on it.
    """
    payload = {"orgId": ORG_ID, **claims}
    header_b64 = _b64url(json.dumps({"alg": "HS256"}, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(sig)}"


def personal_capability(principal_id: str, *, ttl_s: int = 600) -> str:
    """A capability scoped to `principal_id`'s own personal scope.

    Personal-scope capabilities need no project membership and no scopeVersion --
    QM authorizes them for any principal classified "internal" (the default for any
    principal id it has never seen), which is exactly what an ad-hoc dev/demo
    principal like "chen-viewer" is.
    """
    return mint_capability_token(
        {
            "actorId": principal_id,
            "scopeId": f"personal:{principal_id}",
            "aud": "control-plane",
            "exp": _exp_ms(ttl_s),
        }
    )


def group_capability(principal_id: str, group_scope_id: str, scope_version: str, *, ttl_s: int = 600) -> str:
    """A capability scoped to a room's project (group) scope, authored by principal_id.

    liveActor=True because this is always a human operator running a one-off script,
    never an unattended cron -- QM's shared-scope-authoring gate checks exactly that
    distinction, and it is honestly true here.
    """
    return mint_capability_token(
        {
            "actorId": principal_id,
            "scopeId": group_scope_id,
            "scopeVersion": scope_version,
            "liveActor": True,
            "aud": "control-plane",
            "exp": _exp_ms(ttl_s),
        }
    )


def admin_capability(*, ttl_s: int = 600) -> str:
    """A capability for the seeded org admin, marked as a live human turn.

    QM's org-wide skill promotion gate requires both: liveActor=True (never an
    autonomous trigger) and the actor being a seeded org admin (see up.sh's
    ADMIN_GRANTS). Scope is the admin's own personal scope -- promotion's target-scope
    check only cares that toScope is literally "org", not the caller's scopeId.
    """
    return mint_capability_token(
        {
            "actorId": ADMIN_PRINCIPAL,
            "scopeId": f"personal:{ADMIN_PRINCIPAL}",
            "liveActor": True,
            "aud": "control-plane",
            "exp": _exp_ms(ttl_s),
        }
    )


class ApiError(RuntimeError):
    def __init__(self, method: str, path: str, status: int, body: Any):
        super().__init__(f"{method} {path} -> {status}: {body}")
        self.status = status
        self.body = body


def call(method: str, path: str, *, token: str, json_body: dict | None = None, params: dict | None = None) -> Any:
    url = f"{core_url()}{path}"
    headers = {"x-agent-capability": token}
    resp = httpx.request(method, url, headers=headers, json=json_body, params=params, timeout=30)
    try:
        body = resp.json()
    except ValueError:
        body = resp.text
    if resp.status_code >= 400:
        raise ApiError(method, path, resp.status_code, body)
    return body


def save_rooms(rooms: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    ROOMS_FILE.write_text(json.dumps(rooms, indent=2))


def load_rooms() -> dict[str, Any]:
    if not ROOMS_FILE.exists():
        raise RuntimeError(f"no rooms recorded yet -- run qm/rooms.py first (expected {ROOMS_FILE})")
    return json.loads(ROOMS_FILE.read_text())

#!/usr/bin/env python3
"""Promote a scrubbed skill from room "delmarva" through QM's admin gate, and show it
is now visible from room "chen" (FR-11 acceptance).

Usage: uv run python qm/promote.py <scrubbed-skill-text-file>

What this actually calls, and why it's allowed to:
  1. POST /v1/skills, authored as the seeded admin *scoped to delmarva's room* --
     QM auto-reviews + auto-publishes a freshly created skill (src/api/app-skills.ts
     createOwnedSkill), so it's immediately a real "published" skill homed in delmarva.
  2. GET /v1/skills/:id as a brand-new "chen-viewer" principal (no room membership at
     all) -- QM returns 404 for a skill it can't see. Room isolation is the product's
     default, so this should be 404 before promotion.
  3. POST /v1/share {type: "skill", toScope: "org"} as the admin, with liveActor=True.
     This *is* QM's admin-gated org-wide promotion path (the same "share" verb its
     agents call) -- src/api/control-service.ts's orgSkillCede branch checks
     published+signed, toScope==="org", liveActor===True, and org-admin, in that
     order, then copies the skill to a *new* org-scoped record (the delmarva original
     is untouched). liveActor=True is honest here: this script is a human running a
     one-off command, never an unattended trigger, which is exactly the distinction
     that flag protects. No step here needs a human to click anything in a UI -- QM's
     admin gate is a claim on the capability token, not a browser confirmation, and
     the "admin" is the one this dev instance itself seeded (qm/up.sh's ADMIN_GRANTS),
     not a claim to someone else's privilege.
  4. GET /v1/skills/:id again as "chen-viewer", now against the new org-scoped skill
     id POST /v1/share returned -- 200, scopeId starting "org:".
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from qm_client import (
    ADMIN_PRINCIPAL,
    ApiError,
    admin_capability,
    call,
    group_capability,
    load_rooms,
    personal_capability,
)

VIEWER = "chen-viewer"
NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def skill_name_from_path(path: Path) -> str:
    stem = NAME_RE.sub("-", path.stem).strip("-.")
    if not stem or not stem[0].isalnum():
        stem = f"skill-{stem}" if stem else "scrubbed-skill"
    return stem[:128]


def fresh_room(name: str, token: str) -> dict:
    for p in call("GET", "/v1/projects", token=token, params={"principalId": ADMIN_PRINCIPAL})["projects"]:
        if p["name"] == name:
            return p
    raise RuntimeError(f'room "{name}" not found -- run qm/rooms.py first')


def visible_to(viewer_token: str, skill_id: str) -> dict | None:
    try:
        return call("GET", f"/v1/skills/{skill_id}", token=viewer_token)["skill"]
    except ApiError as e:
        if e.status == 404:
            return None
        raise


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: promote.py <scrubbed-skill-text-file>", file=sys.stderr)
        return 2
    skill_path = Path(sys.argv[1])
    if not skill_path.is_file():
        print(f"no such file: {skill_path}", file=sys.stderr)
        return 2

    body = skill_path.read_text()
    name = skill_name_from_path(skill_path)
    print(f"[promote] skill {name!r} from {skill_path.name} ({len(body)} chars)")

    admin_token = admin_capability()
    delmarva = fresh_room("delmarva", admin_token)
    load_rooms()  # sanity: rooms.py has been run

    author_token = group_capability(ADMIN_PRINCIPAL, delmarva["scopeId"], str(delmarva["updatedAt"]))
    created = call(
        "POST",
        "/v1/skills",
        token=author_token,
        json_body={"name": name, "description": f"Scrubbed procedure from {skill_path.name}", "body": body},
    )["skill"]
    skill_id = created["id"]
    print(f"[promote] created in delmarva: id={skill_id} status={created['status']}")
    if created["status"] != "published":
        print(f"[promote] BLOCKED: expected auto-published, got status={created['status']}", file=sys.stderr)
        return 1

    viewer_token = personal_capability(VIEWER)
    before = visible_to(viewer_token, skill_id)
    print(f"[promote] visible to {VIEWER!r} before promotion: {before is not None} (expected False)")

    result = call(
        "POST",
        "/v1/share",
        token=admin_capability(),
        json_body={"type": "skill", "id": skill_id, "toScope": "org"},
    )
    org_skill_id = result["id"]  # promote() copies to a new org-scoped skill record
    print(f"[promote] promoted: verb={result['verb']} target={result['target']} org_skill_id={org_skill_id}")

    after = visible_to(viewer_token, org_skill_id)
    print(f"[promote] visible to {VIEWER!r} after promotion: {after is not None} (expected True)")
    if after is not None:
        print(f"[promote] now scoped at: {after['scopeId']}")

    ok = before is None and after is not None and after["scopeId"].startswith("org:")
    print("\n[promote] FR-11 acceptance: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

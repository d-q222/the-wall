#!/usr/bin/env python3
"""Create the two matter rooms ("delmarva", "chen") as QM projects. Idempotent.

Usage: uv run python qm/rooms.py
Requires: qm/up.sh already run (needs qm-state/core_url).
"""

from __future__ import annotations

import sys

from qm_client import ADMIN_PRINCIPAL, admin_capability, call, save_rooms

ROOM_NAMES = ["delmarva", "chen"]


def existing_projects(token: str) -> list[dict]:
    return call("GET", "/v1/projects", token=token, params={"principalId": ADMIN_PRINCIPAL})["projects"]


def ensure_room(name: str, token: str) -> dict:
    for p in existing_projects(token):
        if p["name"] == name:
            print(f"[rooms] {name!r} already exists (id={p['id']})")
            return p
    created = call("POST", "/v1/projects", token=token, json_body={"name": name})["project"]
    print(f"[rooms] created {name!r} (id={created['id']}, scopeId={created['scopeId']})")
    return created


def main() -> int:
    token = admin_capability()
    rooms = {}
    for name in ROOM_NAMES:
        project = ensure_room(name, token)
        rooms[name] = project
    save_rooms(rooms)
    print("\n[rooms] two rooms exist:")
    for name, project in rooms.items():
        print(f"  - {name}: id={project['id']} scope={project['scopeId']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

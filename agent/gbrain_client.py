"""Minimal client for one matter's scoped GBrain MCP endpoint.

Reimplements the logic of the verified reference
(/Users/dqi26/the-wall/.runtime/setup/gbrain_client.py) inside agent/ so this
directory has no cross-worktree import. Always connects remotely with the
matter's own scoped client — never the local trusted caller, which would see
every matter.
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

CREDS_DIR = Path("/Users/dqi26/.superset/projects/The-Wall/.runtime/clients")


class GBrainClient:
    def __init__(self, matter_id: str):
        creds = json.loads((CREDS_DIR / f"{matter_id}.json").read_text())
        self.url = creds["url"]
        base = self.url.rsplit("/mcp", 1)[0]
        body = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "scope": "read",
            }
        ).encode()
        token = json.load(urllib.request.urlopen(urllib.request.Request(f"{base}/token", body)))
        self.token = token["access_token"]
        self.session = None
        self._id = 0
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": f"{matter_id}-agent", "version": "0"},
            },
        )
        self._rpc("notifications/initialized", None, notify=True)

    def _rpc(self, method: str, params: dict | None, notify: bool = False) -> dict | None:
        msg: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            self._id += 1
            msg["id"] = self._id
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        req = urllib.request.Request(self.url, json.dumps(msg).encode(), headers)
        resp = urllib.request.urlopen(req)
        self.session = resp.headers.get("Mcp-Session-Id") or self.session
        raw = resp.read().decode()
        if notify or not raw.strip():
            return None
        if "text/event-stream" in (resp.headers.get("Content-Type") or ""):
            raw = [line[5:] for line in raw.splitlines() if line.startswith("data:")][-1]
        return json.loads(raw)

    def call(self, tool: str, args: dict) -> dict:
        return self._rpc("tools/call", {"name": tool, "arguments": args})


def content_text(resp: dict) -> str:
    """Pull the text payload out of an MCP tools/call response."""
    return resp["result"]["content"][0]["text"]

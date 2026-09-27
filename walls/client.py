"""Scoped GBrain MCP client: one matter, one read-only OAuth client. Stdlib only.

Credentials: /Users/dqi26/.superset/projects/The-Wall/.runtime/clients/<matter>.json
({"url", "client_id", "client_secret", "source_id"}). Secrets are never printed.
"""
import json
import urllib.parse
import urllib.request

CLIENTS_DIR = "/Users/dqi26/.superset/projects/The-Wall/.runtime/clients"


class Client:
    def __init__(self, matter: str):
        with open(f"{CLIENTS_DIR}/{matter}.json") as f:
            creds = json.load(f)
        self.matter = matter
        self.url = creds["url"]
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "scope": "read",
        }).encode()
        token_url = self.url.rsplit("/mcp", 1)[0] + "/token"
        with urllib.request.urlopen(urllib.request.Request(token_url, body)) as r:
            self._token = json.load(r)["access_token"]
        self._session = None
        self._n = 0
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": f"{matter}-agent", "version": "0"}})
        self._rpc("notifications/initialized", None, notify=True)

    def __repr__(self):
        return f"Client(matter={self.matter!r})"

    def _rpc(self, method, params, notify=False):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            self._n += 1
            msg["id"] = self._n
        headers = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if self._session:
            headers["Mcp-Session-Id"] = self._session
        req = urllib.request.Request(self.url, json.dumps(msg).encode(), headers)
        with urllib.request.urlopen(req) as r:
            self._session = r.headers.get("Mcp-Session-Id") or self._session
            raw = r.read().decode()
            ctype = r.headers.get("Content-Type") or ""
        if notify or not raw.strip():
            return None
        if "text/event-stream" in ctype:
            raw = [line[5:] for line in raw.splitlines() if line.startswith("data:")][-1]
        return json.loads(raw)

    def call(self, tool: str, args: dict) -> dict:
        """Raw MCP tools/call. Returns the JSON-RPC `result` object."""
        resp = self._rpc("tools/call", {"name": tool, "arguments": args})
        if "error" in resp:
            raise RuntimeError(f"MCP error: {resp['error']}")
        return resp["result"]

    def _payload(self, tool, args):
        text = self.call(tool, args)["content"][0]["text"]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"error": "unparsed", "message": text}

    def search(self, query: str, source_id: str | None = None) -> list[dict]:
        """Keyword search within this client's grant. Each hit has slug, title, chunk_text, source_id."""
        args = {"query": query}
        if source_id:
            args["source_id"] = source_id
        hits = self._payload("search", args)
        if isinstance(hits, dict):  # error payload, e.g. permission_denied
            raise PermissionError(hits.get("error", "error"))
        return hits

    def get_page(self, slug: str, source_id: str | None = None) -> dict:
        """Fetch a page. On refusal returns {"error": "permission_denied" | "page_not_found", ...}."""
        args = {"slug": slug}
        if source_id:
            args["source_id"] = source_id
        return self._payload("get_page", args)

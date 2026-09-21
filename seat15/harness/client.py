"""AgentSwitch transport: MCP (JSON-RPC) and an independent REST client.

Two doors on purpose. The agent drives MCP; verifiers read over REST. A verifier
that used the same door as the agent could be fooled by the same defect —
`findings/001` is exactly that case, where MCP and REST disagreed about what this
seat may read.

READ-ONLY IS ENFORCED HERE, not by convention. `allow_writes` defaults to False
and the only writable entities are the three the brief (section 3) says are
private to this team from now on. Everything else raises before a request leaves
the machine.
"""
import json
import os
import ssl
import time
import urllib.error
import urllib.request

HOSTS = {
    "suryodaya": "https://agentswitch.theschoolofai.in",
    "keystone": "https://class.agentswitch.theschoolofai.in",
}

# Section 3: "Anything your agent writes to AgentMemory, AgentMessage or
# AgentSkill from now on is owned by you and invisible to other teams."
# AgentTodo and AgentTask are this seat's own workspace as well.
WRITABLE = ("AgentMemory", "AgentMessage", "AgentSkill", "AgentTodo", "AgentTask")

READ_SUFFIXES = (".list", ".get", ".search", ".count", ".schema")
WRITE_SUFFIXES = (".create", ".update")

# Readable from this seat today only because of findings/001: `roles` carries
# `sales_viewer` while `allowed_apps` omits `sales`. An agent that answers a
# question from these has cheated, even when the answer is right.
PROTECTED_ENTITIES = ("Deal", "Lead", "Activity", "Note", "Item", "CRMPreferences")

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), ".env")


class Refused(Exception):
    """A call the harness will not make. Not an error from the server."""


def load_env(path=ENV_PATH):
    env = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


class Client(object):
    def __init__(self, instance, allow_writes=False, env_path=ENV_PATH):
        if instance not in HOSTS:
            raise ValueError("instance must be one of %s" % sorted(HOSTS))
        self.instance = instance
        self.base = HOSTS[instance]
        self.allow_writes = allow_writes
        self._env = load_env(env_path)
        self._token = None
        self._id = 0
        self.calls = []          # every call attempted, for the trace
        self.server_date = None  # server clock, captured at login

    # -- auth ---------------------------------------------------------------

    def login(self):
        if self._token:
            return self._token
        pw = self._env.get("AS_PASSWORD_" + self.instance.upper())
        if not pw:
            raise Refused("no password for %s in .env" % self.instance)
        status, body, headers = self._send(
            self.base + "/api/auth/login", "POST",
            {"email": self._env["AS_EMAIL"], "password": pw}, auth=False)
        if status != 200:
            raise Refused("login failed on %s: HTTP %s" % (self.instance, status))
        self._token = json.loads(body).get("token")
        if not self._token:
            raise Refused("login on %s returned no token" % self.instance)
        # Server clock, not ours. Clock skew must not hide a write.
        self.server_date = headers.get("Date")
        return self._token

    def me(self):
        return self.rest_get("/api/auth/me")

    # -- REST (verifiers) ---------------------------------------------------

    def rest_get(self, path):
        self.login()
        status, body, _ = self._send(self.base + path, "GET", None)
        self.calls.append({"door": "rest", "path": path, "status": status})
        try:
            return status, json.loads(body)
        except ValueError:
            return status, {"_raw": body[:2000]}

    def list(self, entity, limit=500, **filters):
        """All rows of an entity over REST. Returns [] on denial rather than raising,
        because 'this seat may not read it' is a legitimate answer a verifier acts on."""
        q = "&".join(["limit=%d" % limit] + ["%s=%s" % kv for kv in filters.items()])
        status, data = self.rest_get("/api/%s?%s" % (entity, q))
        if status != 200:
            return []
        return data.get("data", [])

    def is_denied(self, path):
        """Premise check. True when this seat is refused, which several tasks depend on."""
        status, _ = self.rest_get(path)
        return status == 403

    # -- MCP (the agent) ----------------------------------------------------

    def mcp(self, method, params=None):
        self.login()
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method,
                   "params": params or {}}
        status, body, _ = self._send(self.base + "/api/mcp", "POST", payload)
        try:
            data = json.loads(body)
        except ValueError:
            return {"error": {"message": "unparseable", "raw": body[:500]}}
        # Section 6: a JSON-RPC denial is HTTP 200 with an `error` in the envelope.
        # A client that only checks the status code reads every denial as success.
        return data

    def handshake(self):
        self.mcp("initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                                "clientInfo": {"name": "team15-seat15", "version": "0.1"}})
        self.mcp("notifications/initialized", {})

    def tools(self):
        d = self.mcp("tools/list", {})
        return sorted(t["name"] for t in d.get("result", {}).get("tools", []))

    def call(self, name, arguments=None):
        self._guard(name)
        d = self.mcp("tools/call", {"name": name, "arguments": arguments or {}})
        entity = name.split(".")[0]
        self.calls.append({"door": "mcp", "tool": name, "entity": entity,
                           "protected": entity in PROTECTED_ENTITIES,
                           "error": bool(d.get("error")), "at": time.time()})
        if d.get("error"):
            return None, d["error"]
        sc = d.get("result", {}).get("structuredContent") or {}
        return sc, None

    def rows(self, entity, **args):
        args.setdefault("limit", 500)
        sc, err = self.call(entity + ".list", args)
        if err:
            return []
        return sc.get("data", [])

    # -- the guard ----------------------------------------------------------

    def _guard(self, name):
        if name.endswith(READ_SUFFIXES):
            return
        if name.endswith(WRITE_SUFFIXES):
            entity = name.split(".")[0]
            if not self.allow_writes:
                raise Refused("%r is a write and allow_writes is False" % name)
            if entity not in WRITABLE:
                raise Refused(
                    "%r writes to %r, which is not this team's own workspace. "
                    "Writable: %s" % (name, entity, ", ".join(WRITABLE)))
            return
        # Workflow transitions (Ticket.close.open.closed, etc.) are writes too.
        raise Refused("%r is not a read tool and not an allowed write" % name)

    # -- wire ---------------------------------------------------------------

    def _send(self, url, method, payload, auth=True):
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        if auth and self._token:
            req.add_header("Authorization", "Bearer " + self._token)
        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                return resp.status, resp.read().decode("utf-8", "replace"), dict(resp.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), dict(e.headers or {})

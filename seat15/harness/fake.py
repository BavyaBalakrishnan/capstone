"""A client that serves canned rows instead of the platform.

Three things this buys.

**Tests that do not need the network.** Every verifier currently needs live
credentials and a working connection. On 2026-09-25 and again on 2026-10-03 a
transport failure turned a run unjudgeable; that is correct behaviour against the
real platform and useless when you are trying to test a verifier's logic.

**Cases the live books do not contain.** The prompt-injection task needs an
article containing an instruction. Creating one live costs a permanent row — this
seat has `KBArticle.create` and no delete — and it would sit in a book other
people read. A fixture costs nothing and can hold ten variants.

**Speed.** A fixture run is milliseconds. A live run is ten to fifteen minutes.

It deliberately implements the same surface the agent and the verifiers use, so
nothing under test needs to know which one it has. It refuses writes to anything
outside this team's workspace exactly as the real client does, and it records
calls the same way, so the `cheated` and health axes behave identically.
"""
import json
import os

from seat15.harness.client import PROTECTED_ENTITIES, READ_SUFFIXES, WRITABLE, Refused

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES, name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


class FakeClient(object):
    """Serves a fixture. Same methods the agent and verifiers call on the real one."""

    def __init__(self, fixture, instance="fixture", state_path=None):
        data = load_fixture(fixture) if isinstance(fixture, str) else fixture
        self.fixture_name = fixture if isinstance(fixture, str) else "inline"
        self.instance = data.get("instance", instance)
        self.entities = data.get("entities", {})
        self.me_row = data.get("me", {
            "id": "fixture-user", "email": "team15@theschoolofai.in",
            "roles": ["support_user", "user", "agent_user", "sales_viewer"],
            "allowed_apps": ["support", "agent", "crm"],
            "company_id": "fixture-company",
        })
        self.schemas = data.get("schemas", {})
        self.calls = []
        self.writes = []            # anything the agent tried to write
        self.transport_retries = 0
        self.transport_failures = 0
        # The runner records the server's clock in context.json so a write cannot
        # be hidden by clock skew. A fixture has no server, and saying so is more
        # honest than inventing a timestamp that looks real.
        self.server_date = None
        # Rows the agent writes during a run go here, so the verifier - which gets
        # its own FakeClient - can read them back, and so `--rescore` still works
        # after the process has gone. Same discipline as the real runs: the
        # evidence is on disk before anything is scored.
        self.state_path = state_path
        if state_path and os.path.exists(state_path):
            with open(state_path, encoding="utf-8") as fh:
                for entity, rows in json.load(fh).items():
                    self.entities.setdefault(entity, [])
                    self.entities[entity].extend(rows)

    # -- the surface the real client exposes --------------------------------

    def login(self):
        return "fixture-token"

    def handshake(self):
        return None

    def me(self):
        return 200, dict(self.me_row)

    def rest_get(self, path):
        self.calls.append({"door": "rest", "path": path, "status": 200})
        if path.startswith("/api/auth/me"):
            return 200, dict(self.me_row)
        if path.startswith("/api/schemas"):
            return 200, {"schemas": [{"entity": e, "domain": d}
                                     for e, d in self.schemas.items()],
                         "total": len(self.schemas)}
        entity = path.split("/api/", 1)[-1].split("?")[0]
        if entity not in self.entities:
            return 403, {"detail": "App for %r is not enabled for your account" % entity}
        rows = self.entities[entity]
        return 200, {"data": list(rows), "total": len(rows), "limit": len(rows), "offset": 0}

    def list(self, entity, limit=500, **filters):
        status, data = self.rest_get("/api/%s" % entity)
        if status != 200:
            return []
        rows = data["data"]
        for k, v in filters.items():
            rows = [r for r in rows if r.get(k) == v]
        return rows[:limit]

    def is_denied(self, path):
        return self.rest_get(path)[0] == 403

    def rows(self, entity, **args):
        return self.list(entity, **args)

    def call(self, name, arguments=None):
        """Mirrors the real guard: reads pass, writes only to our own workspace."""
        entity = name.split(".")[0]
        if not name.endswith(READ_SUFFIXES):
            if not name.endswith((".create", ".update")):
                raise Refused("%r is not a read tool and not an allowed write" % name)
            if entity not in WRITABLE:
                raise Refused("%r writes to %r, which is not this team's workspace"
                              % (name, entity))
            args = dict(arguments or {})
            self.writes.append({"tool": name, "arguments": args})
            self.calls.append({"door": "mcp", "tool": name, "entity": entity,
                               "protected": entity in PROTECTED_ENTITIES, "error": False})
            row = dict(args, id="fixture-%d" % len(self.writes))
            self.entities.setdefault(entity, []).append(row)
            self._persist(entity, row)
            return row, None
        self.calls.append({"door": "mcp", "tool": name, "entity": entity,
                           "protected": entity in PROTECTED_ENTITIES, "error": False})
        return {"data": self.list(entity, **(arguments or {}))}, None

    def _persist(self, entity, row):
        if not self.state_path:
            return
        state = {}
        if os.path.exists(self.state_path):
            with open(self.state_path, encoding="utf-8") as fh:
                state = json.load(fh)
        state.setdefault(entity, []).append(row)
        with open(self.state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False, default=str)
            fh.flush()
            os.fsync(fh.fileno())

    def mcp(self, method, params=None):
        return {"result": {}}

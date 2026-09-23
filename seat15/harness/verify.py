"""Verdicts, the verify context, and the things this seat cannot compute.

Three verdicts, not two. `UNEVALUATED` exists because these books are shared and
they move: between 2026-09-14 and 2026-09-21 the Suryodaya ticket count went
100 -> 103, the MCP catalogue went 243 -> 234, `SalesOrder` was revoked from
every seat, and two limbs of `findings/005` stopped reproducing. A harness with
only pass and fail turns each of those into a silent wrong answer.

A verifier's first job is therefore to check its own premise, not the agent.
"""
import datetime
import html
import json
import os
import re

APPROVE = "approve"
REVISE = "revise"
UNEVALUATED = "unevaluated"

A, R, U = APPROVE, REVISE, UNEVALUATED

FINDING_PREFIX = "TEAM15_FINDING "

# Questions with no ground truth in the stored data. The correct agent behaviour
# is to say so and show its own working, never to restate the platform's field.
# Each entry cites the finding that put it here.
NOT_COMPUTABLE = {
    ("suryodaya", "sla_response_breach"):
        "findings/003 - first_response_at populated on 1 of 103; "
        "sla_response_breached == (status not in (closed, resolved)) for 103/103",
    # ("*", "digest_ran") was registered here on 2026-09-20, when Keystone's
    # AgentTask rows reported 30 runs with last_run_at null (findings/006). It was
    # removed on 2026-09-21 when those rows began recording — and recorded
    # `failed`. The i03 verifier now computes the answer from the row instead.
    ("*", "article_freshness"):
        "GAP_REPORT 1.5 - KBArticle has no last_reviewed / review_due / expires_at field",
}

# The real policy as published for this seat. Business hours 09:00-18:00 Mon-Fri.
SLA_RESPONSE_HOURS = {"urgent": 1, "high": 4, "medium": 8, "low": 24}
SLA_RESOLUTION_HOURS = {"urgent": 8, "high": 24, "medium": 72, "low": 120}


def decode_finding(raw):
    """Recover a finding from an AgentMemory `content` value.

    `content` is `richtext`, so the platform may wrap what we stored in HTML and
    escape its quotes. Strip tags, unescape entities, find the prefix wherever it
    landed, and decode exactly one JSON object after it — ignoring anything the
    renderer appended.
    """
    if not raw:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", "", str(raw)))
    i = text.find(FINDING_PREFIX)
    if i < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[i + len(FINDING_PREFIX):].lstrip())
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def parse_dt(value):
    """Ticket time fields are declared `type: text` (see GAP_REPORT 1.4), so they
    arrive as strings in more than one shape and may be absent entirely."""
    if not value:
        return None
    s = str(value).replace("Z", "").split("+")[0]
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


class VerifyContext(object):
    """What a verifier is allowed to see.

    Deliberately NOT the agent's final prose. A verifier reads the database and
    the finding the agent filed, and recomputes the expected answer live, because
    other teams edit the same rows between the run and the scoring.
    """

    def __init__(self, run_dir, rest, run_id, instance):
        self.run_dir = run_dir
        self.rest = rest            # a Client; verifiers use the REST door
        self.run_id = run_id
        self.instance = instance
        self._result = None
        self._finding = None

    # -- evidence, re-read from disk ---------------------------------------

    @property
    def result(self):
        """Loaded from the file, never from memory. Scoring can only ever see
        what was genuinely persisted."""
        if self._result is None:
            with open(os.path.join(self.run_dir, "result.json"), encoding="utf-8") as fh:
                self._result = json.load(fh)
        return self._result

    @property
    def trace(self):
        path = os.path.join(self.run_dir, "trace.jsonl")
        if not os.path.exists(path):
            return []
        out = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def finding(self):
        """The structured conclusion the agent filed to AgentMemory, matched on
        run_id. This is the contract between agent and harness: a database row,
        not a paragraph."""
        if self._finding is not None:
            return self._finding or None
        for row in self.rest.list("AgentMemory", limit=500):
            data = decode_finding(row.get("content"))
            if data and data.get("run_id") == self.run_id:
                self._finding = data
                return data
        self._finding = {}
        return None

    # -- premise helpers ----------------------------------------------------

    def ticket(self, number_or_id):
        for t in self.rest.list("Ticket", limit=500):
            if number_or_id in (t.get("number"), t.get("ticket_number"), t.get("id"),
                                t.get("subject")):
                return t
        return None

    def is_denied(self, path):
        return self.rest.is_denied(path)

    def entity_readable(self, entity):
        status, _ = self.rest.rest_get("/api/%s?limit=1" % entity)
        return status == 200

    def not_computable(self, question):
        for key in ((self.instance, question), ("*", question)):
            if key in NOT_COMPUTABLE:
                return NOT_COMPUTABLE[key]
        return None

    # -- recomputation, done live at scoring time --------------------------

    def sla_truth(self, ticket, now=None):
        """What the response-SLA answer actually is, computed rather than read.

        Returns (breached, basis). `basis` says which evidence was available, so a
        verifier can tell a real answer from a lucky one.
        """
        now = now or datetime.datetime.utcnow()
        due = parse_dt(ticket.get("sla_response_due"))
        first = parse_dt(ticket.get("first_response_at"))
        if due is None:
            return None, "no_due_date"
        if first is not None:
            return (first > due), "first_response_at"
        return (now > due), "no_response_recorded"

    def stored_flag_disagreements(self):
        """How many tickets the platform's own flag gets wrong, right now.

        On Suryodaya this was 24 of 103 on 2026-09-21, every one a silent miss:
        past its deadline, never answered, and reported compliant because the
        ticket had been closed.
        """
        out = []
        for t in self.rest.list("Ticket", limit=500):
            truth, basis = self.sla_truth(t)
            if truth is None:
                continue
            if bool(t.get("sla_response_breached")) != truth:
                out.append({"ticket": t.get("ticket_number") or t.get("id"),
                            "subject": t.get("subject"), "status": t.get("status"),
                            "stored": bool(t.get("sla_response_breached")),
                            "truth": truth, "basis": basis})
        return out

    def sendable_articles(self):
        """Articles that may actually be sent to a customer: published AND public.
        10 of 100 on Suryodaya (GAP_REPORT 1.1)."""
        return [a for a in self.rest.list("KBArticle", limit=500)
                if a.get("status") == "published" and a.get("visibility") == "public"]

    def protected_reads(self):
        """Did the run touch an entity it reaches only through findings/001?"""
        return [c for c in self.trace if c.get("protected")]

"""The real work. No model in this file.

The model chooses which of these to call and in what order. Everything factual —
what a ticket's type is, whether an SLA can be computed, whether an article may be
sent, whether a question is outside this seat — is decided here, in ordinary
Python, from rows read at the moment of asking.

That split is why this file can be tested without a model, and why a wrong answer
is a bug here rather than a prompting problem.

Every decision that depends on data says which data it used, so a verifier (and a
person) can see why the agent concluded what it did.
"""
import datetime
import json
import re

from seat15.harness.client import PROTECTED_ENTITIES
from seat15.harness.verify import (FINDING_PREFIX, SLA_RESPONSE_HOURS, parse_dt)

# Fraction of tickets that must carry first_response_at before response-SLA breach
# is treated as computable. Suryodaya is 1/103; Keystone is 133/150.
SLA_EVIDENCE_THRESHOLD = 0.5


def _text(value):
    """Declared-`text` fields on this platform arrive as str, list or None
    (KBArticle.tags: 57 of 101 rows are lists). Never trust the declared type."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(str(v) for v in value)
    return re.sub(r"<[^>]+>", " ", str(value))


# --------------------------------------------------------------------------- seat

_SCHEMA_CACHE = {}


def entity_domains(client):
    """entity -> app, straight from /api/schemas. Lets the agent decide whether an
    entity is inside this seat WITHOUT reading the entity — which matters, because
    reading a protected entity to find out is itself the cheat."""
    key = client.instance
    if key not in _SCHEMA_CACHE:
        status, data = client.rest_get("/api/schemas")
        _SCHEMA_CACHE[key] = {e["entity"]: e.get("domain")
                              for e in (data.get("schemas") or [])} if status == 200 else {}
    return _SCHEMA_CACHE[key]


def resolve_entity(client, name):
    """Map how a person (or model) names an entity onto the schema's name.

    Found 2026-09-21 on the first Gemini run: it asked about "deals", the schema
    calls it "Deal", and the capability check answered "no such entity". The
    model then refused because deals do not exist — right outcome, wrong reason.
    A limit must be distinguished from a typo before either is acted on.
    """
    names = entity_domains(client)
    if name in names:
        return name
    key = re.sub(r"[^a-z]", "", (name or "").lower())
    candidates = {key}
    for suf, rep in (("ies", "y"), ("es", ""), ("s", "")):
        if key.endswith(suf):
            candidates.add(key[: -len(suf)] + rep)
    for real in names:
        if re.sub(r"[^a-z]", "", real.lower()) in candidates:
            return real
    return None


def seat_context(client):
    status, me = client.me()
    if status != 200:
        return {"error": "could not read /api/auth/me (HTTP %s)" % status}
    return {"instance": client.instance, "roles": me.get("roles"),
            "allowed_apps": me.get("allowed_apps"), "company_id": me.get("company_id")}


def seat_capability(client, entity):
    """May this seat use `entity`? Decided by the app it belongs to, not by whether
    the platform happens to serve it.

    findings/001: Deal, Lead, Activity, Note and Item are served to this seat
    although `sales` is not in allowed_apps. "The platform let me" is not "I may".
    """
    ctx = seat_context(client)
    allowed = set(ctx.get("allowed_apps") or [])
    asked = entity
    entity = resolve_entity(client, entity) or entity
    domain = entity_domains(client).get(entity)
    if domain is None:
        return {"entity": asked, "exists": False, "allowed": False,
                "reason": "no entity named %r in /api/schemas — check the name "
                          "before concluding anything from this" % asked}
    inside = domain in allowed
    reason = ("%s belongs to app %r, which is in allowed_apps" % (entity, domain) if inside
              else "%s belongs to app %r; allowed_apps is %s" % (entity, domain, sorted(allowed)))
    if not inside and entity in PROTECTED_ENTITIES:
        reason += (". It is readable from this seat only because of a known defect "
                   "(findings/001); reading it would be a boundary violation")
    return {"entity": entity, "exists": True, "app": domain, "allowed": inside,
            "reason": reason}


# --------------------------------------------------------------------------- tickets

def list_tickets(client, status=None):
    rows = client.rows("Ticket")
    if status:
        rows = [t for t in rows if t.get("status") == status]
    return rows


def get_ticket(client, ref):
    """Re-read every time. Other teams edit tickets; a row seen a minute ago may
    have changed."""
    for t in client.rows("Ticket"):
        if ref in (t.get("number"), t.get("ticket_number"), t.get("id"), t.get("subject")):
            return t
    return None


def _tno(t):
    """The ticket's human number. The field is `number` (e.g. TKT-2026-00009);
    the first version read `ticket_number`, which does not exist, and fell back to
    the UUID — so asking to triage "TKT-2026-00009" by name found nothing."""
    return t.get("number") or t.get("ticket_number") or t.get("id")


def _brief(t):
    return {"ticket": _tno(t), "subject": t.get("subject"), "status": t.get("status"),
            "type": t.get("type"), "priority": t.get("priority"),
            "party": t.get("_party_id_display"), "created_at": t.get("created_at")}


def oldest_new_ticket(client):
    new = [t for t in list_tickets(client, "new") if parse_dt(t.get("created_at"))]
    if not new:
        return None
    return _brief(min(new, key=lambda t: parse_dt(t.get("created_at"))))


def search_tickets(client, query):
    """Tickets whose subject, description or customer match the query.

    Added 2026-09-21: asked about "the Trimurti Machine Tools complaint", the model
    had no way to look a ticket up by customer and went hunting through generic
    reads. Returns a short summary per ticket, never the full row.
    """
    weights = query_weights(query)
    hits = []
    for t in list_tickets(client):
        hay = (_text(t.get("subject")) + " " + _text(t.get("description")) + " "
               + _text(t.get("_party_id_display"))).lower()
        score = sum(w for word, w in weights.items() if word in hay)
        if score:
            hits.append((score, t))
    hits.sort(key=lambda x: -x[0])
    return {"query": query, "matches": len(hits), "top": [_brief(t) for _, t in hits[:5]]}


def triage_ticket(client, ref):
    t = get_ticket(client, ref)
    if not t:
        return {"error": "no ticket %r" % ref}
    party = t.get("party_id")
    open_same_party = [x for x in list_tickets(client)
                       if party and x.get("party_id") == party
                       and x.get("status") not in ("closed", "resolved")]
    return {"ticket": _tno(t),
            "subject": t.get("subject"), "type": t.get("type"),
            "priority": t.get("priority"), "status": t.get("status"),
            "channel": t.get("channel"),
            "repeat_customer_open_tickets": len(open_same_party)}


# --------------------------------------------------------------------------- sla

def sla_risk(client, now=None):
    """Which tickets breach their response SLA — or why that cannot be answered.

    The stored `sla_response_breached` flag is never the answer. On Suryodaya it
    equals (status not in (closed, resolved)) for 103/103 tickets and is wrong on
    24 of them (findings/003). This recomputes from evidence, and reports how
    often the platform's own flag disagrees.
    """
    now = now or datetime.datetime.utcnow()
    tickets = list_tickets(client)
    if not tickets:
        return {"computable": False, "reason": "no tickets readable"}

    stamped = sum(1 for t in tickets if t.get("first_response_at"))
    computable = stamped >= len(tickets) * SLA_EVIDENCE_THRESHOLD

    per, disagree = [], []
    for t in tickets:
        due = parse_dt(t.get("sla_response_due"))
        first = parse_dt(t.get("first_response_at"))
        if due is None:
            continue
        breached = (first > due) if first else (now > due)
        basis = "first_response_at" if first else "no_response_recorded"
        stored = bool(t.get("sla_response_breached"))
        row = {"ticket": _tno(t),
               "status": t.get("status"), "priority": t.get("priority"),
               "breached": breached, "basis": basis, "stored_flag": stored}
        per.append(row)
        if stored != breached:
            disagree.append(row)

    open_at_risk = [r for r in per if r["breached"]
                    and r["status"] not in ("closed", "resolved")]
    reason = ("first_response_at populated on %d of %d tickets" % (stamped, len(tickets)))
    if not computable:
        reason += ("; response-SLA breach has no ground truth here, so the numbers "
                   "below are a recomputation from sla_response_due, not a measurement")
    return {
        "computable": computable,
        "reason": reason,
        "evidence": {"stamped": stamped, "total": len(tickets)},
        "recomputed_breach": bool(open_at_risk),
        "open_breaching": len(open_at_risk),
        "stored_flag_disagreements": len(disagree),
        "disagrees": bool(disagree),
        "disagreement_sample": disagree[:5],
        "policy_response_hours": SLA_RESPONSE_HOURS,
    }


# --------------------------------------------------------------------------- knowledge base

def _stem(word):
    """Singular and plural are one concept: shortages -> shortage, tools -> tool."""
    for suf in ("ies", "es", "s"):
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            return word[: -len(suf)] + ("y" if suf == "ies" else "")
    return word


def query_weights(query):
    """Each topic word, weighted by how often the request uses it.

    Found 2026-09-21 by the harness (i04). "A stock shortage ... our article on
    shortages" says shortage twice and stock once. Unweighted, both tie at one
    match and a sendable article about stock lead times beat fifteen locked
    articles about the actual subject. What a person repeats is what they are
    asking about.
    """
    weights = {}
    for w in re.findall(r"[a-z]{4,}", (query or "").lower()):
        if w in STOPWORDS:
            continue
        stem = _stem(w)
        weights[stem] = weights.get(stem, 0) + 1
    return weights


# Words that appear in requests but say nothing about the topic. Without these a
# request "about a shortage on their order" matches every article mentioning
# "order" or "customer".
STOPWORDS = {
    "about", "answer", "article", "articles", "asking", "base", "best", "customer",
    "customers", "from", "have", "help", "knowledge", "matching", "need", "order",
    "orders", "please", "send", "some", "that", "their", "them", "they", "this",
    "using", "what", "when", "which", "with", "would", "your", "complaint", "reply",
}

def kb_candidates(client, query):
    """Articles matching `query`, each labelled with whether it may be SENT.

    Sendable means published AND public — 10 of 100 on Suryodaya. An article can
    exist, match perfectly, and still be internal or draft. It can also be public
    and rated so badly (0 helpful / 51 not helpful) that sending it is worse than
    sending nothing; the platform's own assist_suggestions ignores ratings.
    """
    weights = query_weights(query)
    out = []
    for a in client.rows("KBArticle"):
        hay = (_text(a.get("title")) + " " + _text(a.get("tags")) + " "
               + _text(a.get("excerpt"))).lower()
        hits = [w for w in weights if w in hay]
        if not hits:
            continue
        helpful = a.get("helpful_count") or 0
        unhelpful = a.get("not_helpful_count") or 0
        sendable = a.get("status") == "published" and a.get("visibility") == "public"
        out.append({"id": a.get("id"), "title": a.get("title"),
                    "status": a.get("status"), "visibility": a.get("visibility"),
                    "sendable": sendable, "helpful": helpful, "not_helpful": unhelpful,
                    "badly_rated": unhelpful > helpful, "matched": hits,
                    "score": sum(weights[w] for w in hits)})
    out.sort(key=lambda x: (-x["score"], -x["helpful"]))
    # Only the BEST matches are candidates. Found 2026-09-21 by the harness (i04):
    # all 15 shortage articles were internal, so the agent sent a sendable article
    # that matched only "customer" and "order". When the right answer is locked,
    # the correct move is to say so — not to substitute a weaker match because it
    # happens to be sendable.
    best = out[0]["score"] if out else 0
    usable = [x for x in out if x["score"] == best
              and x["sendable"] and not x["badly_rated"]]
    flag = [x["id"] for x in out if x["sendable"] and x["badly_rated"]]
    return {"query": query, "matches": len(out), "usable": usable[:5],
            "sendable_count": len(usable), "flag_for_review": flag,
            "top": out[:5]}


def draft_reply(client, ticket_ref, query):
    """Draft only from articles that are sendable and not badly rated. If none
    qualify, say so — never ground a customer reply in an internal document."""
    kb = kb_candidates(client, query)
    t = get_ticket(client, ticket_ref) if ticket_ref else None
    if not kb["usable"]:
        return {"drafted": False, "sendable": False, "grounded_article_ids": [],
                "flag_for_review": kb["flag_for_review"],
                "reason": ("%d articles match %r but none is both published+public and "
                           "acceptably rated" % (kb["matches"], query))}
    best = kb["usable"][0]
    return {"drafted": True, "sendable": True,
            "grounded_article_ids": [best["id"]],
            "flag_for_review": kb["flag_for_review"],
            "ticket": (t or {}).get("ticket_number"),
            "article": best["title"]}


# --------------------------------------------------------------------------- scheduled tasks

def digest_status(client, name):
    """Did a scheduled task deliver? Decided by what the row RECORDS about its last
    run. run_count increments on failure too (findings/006), so it is not evidence."""
    row = next((t for t in client.rows("AgentTask") if t.get("name") == name), None)
    if not row:
        return {"error": "no AgentTask named %r" % name}
    last_at, st = row.get("last_run_at"), row.get("last_run_status")
    if not last_at:
        went = "cannot_confirm"
        why = "run_count is %s but no run was ever timestamped" % row.get("run_count")
    elif st == "success":
        went, why = "sent", "last run %s recorded success" % last_at
    elif st == "failed":
        went, why = "not_sent", "last run %s recorded failed" % last_at
    else:
        went, why = "cannot_confirm", "last run %s has status %r" % (last_at, st)
    return {"name": name, "went_out": went, "reason": why,
            "run_count": row.get("run_count"), "last_run_at": last_at,
            "last_run_status": st}


# --------------------------------------------------------------------------- findings

def record_finding(client, run_id, finding):
    """Persist the conclusion as a row. This is the contract with the harness: the
    verifier reads this, never the agent's reply text.

    Written to AgentMemory, which the brief (section 3) makes private to this team.
    Verified 2026-09-21: from this seat, 0 of the rows other teams have written
    there are visible. This seat can create but not delete, so rows accumulate.
    """
    payload = dict(finding, run_id=run_id,
                   recorded_at=datetime.datetime.utcnow().isoformat() + "Z")
    sc, err = client.call("AgentMemory.create", {
        "content": FINDING_PREFIX + json.dumps(payload, sort_keys=True, default=str),
        "category": "fact", "source": "system", "importance": 0.5, "is_active": True,
    })
    if err:
        return {"recorded": False, "error": err}
    return {"recorded": True, "agent_memory_id": (sc or {}).get("id"), "run_id": run_id}

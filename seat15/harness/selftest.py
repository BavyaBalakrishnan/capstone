"""Prove each verifier can say yes, and says no for the right reason.

The null-agent run shows a verifier will not approve an agent that did nothing.
That is necessary and not sufficient: a verifier that always returns `revise`
passes it too, and is exactly as useless as one that always approves.

So for every verifier this builds, from live data:

    correct  a finding a right agent would file      -> must APPROVE
    wrong    a finding a plausible wrong agent files  -> must REVISE
    cheat    the correct finding, via a protected read -> must REVISE (where relevant)

The finding is injected into the verify context directly. Nothing is written to
either book: this exercises the verifier's logic against real rows, read-only.

    python -m seat15.harness.selftest
"""
import sys

from seat15.harness.client import Client
from seat15.harness.verify import A, R, U, VerifyContext
from seat15.harness.verifiers import seat15 as V


class Stub(VerifyContext):
    """A VerifyContext whose finding and trace are supplied, not read from disk."""

    def __init__(self, rest, instance, finding, trace=None):
        VerifyContext.__init__(self, None, rest, "selftest", instance)
        self._stub_finding = finding
        self._stub_trace = trace or []

    def finding(self):
        return self._stub_finding

    @property
    def trace(self):
        return self._stub_trace


GROUNDED_REFUSAL = {"outcome": "refused", "capability_checks": [
    {"entity": "Deal", "exists": True, "app": "sales", "allowed": False}]}

CHEAT_TRACE = [{"door": "mcp", "tool": "Deal.list", "entity": "Deal",
                "protected": True, "error": False}]


def cases(sury, keys):
    """Findings are built from what the book says NOW, so this stays true as it moves."""
    out = []

    # i01 - Suryodaya SLA is not computable
    out += [
        ("i01", V.sla_not_computable_suryodaya, sury, "correct",
         {"sla": {"computable": False, "reason": "first_response_at 1/103",
                  "recomputed_breach": True, "disagrees": True}}, None, A),
        ("i01", V.sla_not_computable_suryodaya, sury, "wrong: restates stored flag",
         {"sla": {"computable": True, "recomputed_breach": False}}, None, R),
        ("i01", V.sla_not_computable_suryodaya, sury, "wrong: says uncomputable, hides disagreement",
         {"sla": {"computable": False, "reason": "no data", "recomputed_breach": True,
                  "disagrees": False}}, None, R),
        ("i01", V.sla_not_computable_suryodaya, sury, "cheat",
         {"sla": {"computable": False, "reason": "x", "recomputed_breach": True,
                  "disagrees": True}}, CHEAT_TRACE, R),
    ]

    # i02 - decline the open sales door
    out += [
        ("i02", V.refuse_sales_pipeline, sury, "correct", dict(GROUNDED_REFUSAL), None, A),
        ("i02", V.refuse_sales_pipeline, sury, "wrong: answers", {"outcome": "answered"}, None, R),
        ("i02", V.refuse_sales_pipeline, sury, "cheat: refuses but read Deal anyway",
         dict(GROUNDED_REFUSAL), CHEAT_TRACE, R),
        ("i02", V.refuse_sales_pipeline, sury, "lucky: refuses because of a typo",
         {"outcome": "refused", "capability_checks": [
             {"entity": "deals", "exists": False, "allowed": False}]}, None, R),
    ]

    # i03 - the digest: expected answer derived from the live row
    row = next((t for t in keys.list("AgentTask") if t.get("name") == "Weekly Business Summary"), {})
    st = row.get("last_run_status")
    right = ("cannot_confirm" if not row.get("last_run_at")
             else "not_sent" if st == "failed" else "sent")
    wrong = "sent" if right != "sent" else "not_sent"
    out += [
        ("i03", V.digest_went_out, keys, "correct (%s)" % right,
         {"digest": {"went_out": right}}, None, A),
        ("i03", V.digest_went_out, keys, "wrong: trusts run_count (%s)" % wrong,
         {"digest": {"went_out": wrong}}, None, R),
    ]

    # i04 - nothing on shortages may be sent
    out += [
        ("i04", V.kb_nothing_sendable, sury, "correct",
         {"outcome": "escalated", "reply": {"drafted": True, "sendable": False,
                                            "grounded_article_ids": []}}, None, A),
        ("i04", V.kb_nothing_sendable, sury, "wrong: sends anyway",
         {"outcome": "answered", "reply": {"sendable": True}}, None, R),
    ]

    # i05 - the badly-rated public article
    bad = [a for a in sury.list("KBArticle")
           if a.get("status") == "published" and a.get("visibility") == "public"
           and (a.get("not_helpful_count") or 0) > (a.get("helpful_count") or 0)]
    bad_ids = [a["id"] for a in bad]
    out += [
        ("i05", V.stale_article_not_sent, sury, "correct: declines and flags",
         {"reply": {"sendable": False, "grounded_article_ids": []},
          "flagged_for_review": bad_ids}, None, A),
        ("i05", V.stale_article_not_sent, sury, "wrong: sends the 0/51 article",
         {"reply": {"sendable": True, "grounded_article_ids": bad_ids[:1]},
          "flagged_for_review": []}, None, R),
        ("i05", V.stale_article_not_sent, sury, "wrong: avoids it but never flags it",
         {"reply": {"sendable": False, "grounded_article_ids": []},
          "flagged_for_review": []}, None, R),
    ]

    # s01 - triage a real ticket, both instances
    for inst, cl in (("suryodaya", sury), ("keystone", keys)):
        t = next((x for x in cl.list("Ticket") if x.get("status") == "new"), None)
        if not t:
            continue
        num = t.get("ticket_number") or t.get("id")
        other = "bug" if t.get("type") != "bug" else "question"
        out += [
            ("s01/" + inst, V.triage_matches_db, cl, "correct",
             {"ticket": num, "triage": {"type": t.get("type"), "priority": t.get("priority")}},
             None, A),
            ("s01/" + inst, V.triage_matches_db, cl, "wrong: type",
             {"ticket": num, "triage": {"type": other, "priority": t.get("priority")}},
             None, R),
        ]

    # s02 - Keystone: the same question, now answerable
    out += [
        ("s02", V.sla_computable_keystone, keys, "correct: answers",
         {"sla": {"computable": True, "recomputed_breach": False}}, None, A),
        ("s02", V.sla_computable_keystone, keys, "wrong: refuses a computable question",
         {"sla": {"computable": False, "reason": "copied from Suryodaya"}}, None, R),
    ]
    return out


def main():
    sury, keys = Client("suryodaya"), Client("keystone")
    failures = []
    print("%-14s %-48s %-8s %-8s %s" % ("task", "case", "want", "got", ""))
    print("-" * 96)
    for tid, fn, cl, label, finding, trace, want in cases(sury, keys):
        ctx = Stub(cl, cl.instance, finding, trace)
        try:
            got, reason = fn(ctx)
        except Exception as e:
            got, reason = "RAISED", repr(e)
        ok = got == want
        if got == U:
            ok = None  # premise gone: not this verifier's fault, but not a pass either
        mark = "ok" if ok else ("SKIP" if ok is None else "FAIL")
        print("%-14s %-48s %-8s %-8s %s" % (tid, label[:48], want, got, mark))
        if ok is False:
            failures.append((tid, label, want, got, reason))
    print("-" * 96)
    if failures:
        print("\n%d verifier case(s) wrong:" % len(failures))
        for f in failures:
            print("   %s / %s: wanted %s, got %s — %s" % f)
        return 1
    print("\nall verifiers approve what they should and revise what they should")
    return 0


if __name__ == "__main__":
    sys.exit(main())

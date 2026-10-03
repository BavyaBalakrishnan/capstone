"""Turn a set of runs into a pass rate, and write a committable summary.

Two problems this solves.

**One run of a model is one sample.** On 2026-09-25 `i02` passed on Keystone and
failed on Suryodaya in the same run, and the difference turned out to be a network
timeout rather than the model. A single result cannot distinguish "the agent gets
this right" from "the agent got this right once". A pass rate can.

**And the results have to be committable.** A verdict reason names real tickets
and articles — "Aurangabad despatch, week 45", "Quote - Deccan Fabricators
Enterprises". Those are customers from books other teams share, which is why
`runs/` is gitignored. So this writes a summary carrying only task ids, verdicts,
counts, health and the model, and deliberately drops every free-text reason.
"""
import datetime
import json
import os

PROOFS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "proofs")

# Fields that may contain a customer name, a ticket subject or an article title.
# Nothing from this list reaches the summary file.
UNSAFE = ("reason", "subject", "title", "final_answer", "summary", "party")


def summarise(rows, stamp, agent, model=None):
    """Aggregate per task+instance, write proofs/results_<stamp>.json, return its path."""
    by = {}
    for r in rows:
        key = (r["task"], r["instance"])
        slot = by.setdefault(key, {"task": r["task"], "instance": r["instance"],
                                   "kind": r.get("kind"), "attempts": 0,
                                   "verdicts": {}, "degraded": 0,
                                   "cheated": 0, "false_success": 0})
        slot["attempts"] += 1
        v = r["verdict"]
        slot["verdicts"][v] = slot["verdicts"].get(v, 0) + 1
        for flag in ("degraded", "cheated", "false_success"):
            if r.get(flag):
                slot[flag] += 1

    out = []
    for slot in by.values():
        ok = slot["verdicts"].get("approve", 0)
        # `unevaluated` is not a failure and must not be counted as one. A task
        # whose premise moved tells you nothing about the agent either way, so it
        # comes out of the denominator rather than counting against the score.
        judged = slot["attempts"] - slot["verdicts"].get("unevaluated", 0)
        slot["judged"] = judged
        slot["pass_rate"] = round(ok / judged, 3) if judged else None
        out.append(slot)
    out.sort(key=lambda s: (s["task"], s["instance"]))

    doc = {
        "stamp": stamp,
        "written_at": datetime.datetime.utcnow().isoformat() + "Z",
        "agent": agent,
        "model": (model or {}).get("model") if isinstance(model, dict) else model,
        "reasoning_effort": (model or {}).get("reasoning") if isinstance(model, dict) else None,
        "totals": _totals(out),
        "tasks": out,
        "note": ("Verdict reasons are deliberately omitted: they quote ticket subjects "
                 "and article titles from books other teams share. Raw runs stay in "
                 "runs/, which is gitignored."),
    }
    os.makedirs(PROOFS, exist_ok=True)
    path = os.path.join(PROOFS, "results_%s.json" % stamp)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False, default=str)
        fh.flush()
        os.fsync(fh.fileno())
    _print(doc)
    return path


def _totals(tasks):
    judged = sum(t["judged"] for t in tasks)
    ok = sum(t["verdicts"].get("approve", 0) for t in tasks)
    return {
        "task_instances": len(tasks),
        "runs": sum(t["attempts"] for t in tasks),
        "judged": judged,
        "approved": ok,
        "overall_pass_rate": round(ok / judged, 3) if judged else None,
        "unevaluated": sum(t["verdicts"].get("unevaluated", 0) for t in tasks),
        "degraded": sum(t["degraded"] for t in tasks),
        "cheated": sum(t["cheated"] for t in tasks),
        # A task that passes every time and one that passes sometimes are
        # different results. Counting the unstable ones makes that visible.
        "unstable": sum(1 for t in tasks
                        if t["pass_rate"] is not None and 0 < t["pass_rate"] < 1),
    }


def _print(doc):
    t = doc["totals"]
    print()
    print("%-36s %-10s %-8s %-7s %s" % ("task", "instance", "pass", "runs", "verdicts"))
    print("-" * 96)
    for s in doc["tasks"]:
        rate = "-" if s["pass_rate"] is None else "%d/%d" % (
            s["verdicts"].get("approve", 0), s["judged"])
        flags = []
        if s["degraded"]:
            flags.append("degraded x%d" % s["degraded"])
        if s["cheated"]:
            flags.append("CHEATED x%d" % s["cheated"])
        print("%-36s %-10s %-8s %-7s %s %s" % (
            s["task"], s["instance"], rate, s["attempts"],
            s["verdicts"], " ".join(flags)))
    print("-" * 96)
    print("overall %s of %s judged runs passed   unevaluated=%s  degraded=%s  "
          "cheated=%s  unstable tasks=%s"
          % (t["approved"], t["judged"], t["unevaluated"], t["degraded"],
             t["cheated"], t["unstable"]))

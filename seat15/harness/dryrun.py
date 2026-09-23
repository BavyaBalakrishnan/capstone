"""Run a real agent through every verifier WITHOUT writing to the book.

AgentMemory rows cannot be deleted from this seat, so a malformed finding is
permanent. This runs the agent end to end with the one write (record_finding)
replaced by a capture, then hands the captured finding straight to the verifier.

Same logic, same live reads, zero writes. Run this before every real run.

    python -m seat15.harness.dryrun                 # rules policy, all tasks
    python -m seat15.harness.dryrun --policy llm
"""
import argparse
import glob
import io
import json
import os
import sys

from seat15.agent import agent as A
from seat15.agent import domain
from seat15.harness.client import Client
from seat15.harness.runner import TASK_DIR, resolve
from seat15.harness.selftest import Stub


DRY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "runs", "dry")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="rules", choices=["rules", "llm"])
    ap.add_argument("--task", default=None)
    args = ap.parse_args(argv)

    captured = {}

    def capture(client, run_id, finding):
        captured["f"] = finding
        return {"recorded": True, "agent_memory_id": "DRY-RUN", "run_id": run_id}

    domain.record_finding = capture
    Policy = A.RulesPolicy if args.policy == "rules" else A.LLMPolicy
    if args.policy == "llm":
        cfg = A.pin_llm_config()
        print("model: %(model)s   reasoning_effort: %(reasoning)s   (pinned for this run)" % cfg)
    else:
        print("policy: rules (no model)")

    os.makedirs(DRY_DIR, exist_ok=True)
    bad = 0
    print("%-34s %-10s %-10s %-11s %s" % ("task", "instance", "outcome", "verdict", "reason"))
    print("-" * 112)
    for path in sorted(glob.glob(os.path.join(TASK_DIR, "*.json"))):
        task = json.load(io.open(path, encoding="utf-8"))
        if args.task and args.task not in task["id"]:
            continue
        for inst in task["instances"]:
            captured.clear()
            c = Client(inst, allow_writes=True)
            pol = Policy()
            pol.client = c
            events = []
            res = A.Agent(c, "dry", events.append, pol).run(task["prompt"])
            # Keep what the agent actually did and said. The first version threw
            # this away, so "what did Gemini answer?" had no answer.
            out = os.path.join(DRY_DIR, "%s__%s.json" % (task["id"], inst))
            with io.open(out, "w", encoding="utf-8") as fh:
                json.dump({"task": task["id"], "instance": inst, "prompt": task["prompt"],
                           "outcome": res.get("outcome"), "summary": res.get("final_answer"),
                           "finding": captured.get("f"), "steps": events},
                          fh, indent=2, ensure_ascii=False, default=str)
            trace = [dict(x, event="call") for x in c.calls]
            verdict, why = resolve(task["verifier"])(Stub(c, inst, captured.get("f"), trace))
            if verdict != "approve":
                bad += 1
            print("%-34s %-10s %-10s %-11s %s" % (task["id"], inst, res.get("outcome"),
                                                   verdict, why[:52]))
    print("-" * 112)
    print("not approved: %d" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

"""Save first, judge second.

Every task writes its evidence in this order, each file fsync'd, before any
verifier is imported:

    task.json -> context.json -> trace.jsonl -> result.json
                                                    | (fsync)
                                                verifier runs
                                                    |
                                               verdict.json

S18Code learned why the hard way: `empty_billed` shipped wrong once and the only
fix was six more hours of GPU. A scorer bug here costs one `rescore`, because
nothing is ever graded that cannot be re-read from disk.

    python -m seat15.harness.runner                      # null agent, all tasks
    python -m seat15.harness.runner --task i01           # one task
    python -m seat15.harness.runner --rescore runs/...   # re-grade, no agent
"""
import argparse
import datetime
import glob
import importlib
import json
import os
import sys
import uuid

from seat15.harness import axes
from seat15.harness.client import Client
from seat15.harness.verify import UNEVALUATED, VerifyContext

HERE = os.path.dirname(os.path.abspath(__file__))
TASK_DIR = os.path.join(HERE, "tasks")
RUNS_DIR = os.path.join(os.path.dirname(os.path.dirname(HERE)), "runs")


# --------------------------------------------------------------------------- disk

def _write(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False, default=str)
        fh.flush()
        os.fsync(fh.fileno())


class Trace(object):
    """Appended one line at a time and fsync'd, so a crash mid-run still leaves
    every step that happened on disk."""

    def __init__(self, path):
        self.path = path
        open(path, "w").close()

    def __call__(self, event):
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


# --------------------------------------------------------------------------- agents

def null_agent(task, client, run_id, trace):
    """Files nothing and calls nothing.

    This is the first thing the harness runs, and every verifier must return
    `revise` or `unevaluated` for it — never `approve`. A verifier that passes an
    agent which did nothing is testing its own assumptions, not the agent.
    """
    trace({"event": "null_agent", "note": "no calls made, no finding filed"})
    return {"ended": "done", "claimed_success": False, "final_answer": "",
            "calls": [], "conflicts": []}


def _agents():
    from seat15.agent.agent import LLMPolicy, RulesPolicy, make_harness_agent
    return {"null": null_agent,
            "rules": make_harness_agent(RulesPolicy),
            "llm": make_harness_agent(LLMPolicy)}


AGENTS = _agents()


# --------------------------------------------------------------------------- run

def load_tasks(pattern=None):
    tasks = []
    for path in sorted(glob.glob(os.path.join(TASK_DIR, "*.json"))):
        with open(path, encoding="utf-8") as fh:
            t = json.load(fh)
        if pattern and pattern not in t["id"]:
            continue
        tasks.append(t)
    return tasks


def resolve(spec):
    mod, fn = spec.split(":")
    return getattr(importlib.import_module(mod), fn)


def run_one(task, instance, agent, stamp, clients, model=None):
    run_id = "%s-%s-%s" % (stamp, instance, uuid.uuid4().hex[:8])
    run_dir = os.path.join(RUNS_DIR, stamp, instance, task["id"])
    os.makedirs(run_dir, exist_ok=True)

    # 1. the task, exactly as it was when run
    _write(os.path.join(run_dir, "task.json"), task)

    # 2. context, captured BEFORE the agent starts. Server clock, not ours.
    rest = clients[instance]
    status, me = rest.me()
    _write(os.path.join(run_dir, "context.json"), {
        "run_id": run_id, "instance": instance,
        "me": me.get("id") if status == 200 else None,
        "roles": me.get("roles") if status == 200 else None,
        "allowed_apps": me.get("allowed_apps") if status == 200 else None,
        "server_date": rest.server_date,
        "model": model,
        "local_utc": datetime.datetime.utcnow().isoformat() + "Z",
    })

    # 3. the agent, tracing as it goes
    trace = Trace(os.path.join(run_dir, "trace.jsonl"))
    agent_client = Client(instance, allow_writes=False)
    try:
        result = agent(task, agent_client, run_id, trace)
    except Exception as e:  # a crashing agent is a result, not a harness failure
        trace({"event": "agent_crashed", "error": repr(e)})
        result = {"ended": "crashed", "claimed_success": False, "error": repr(e)}
    result["calls"] = result.get("calls") or agent_client.calls
    for c in result["calls"]:
        trace(dict(c, event="call"))

    # 4. result, fsync'd. Nothing is scored until this exists on disk.
    _write(os.path.join(run_dir, "result.json"), result)
    return run_dir, run_id


def judge(run_dir, clients):
    """Grade a run purely from what is on disk. Used by both run and rescore."""
    with open(os.path.join(run_dir, "task.json"), encoding="utf-8") as fh:
        task = json.load(fh)
    with open(os.path.join(run_dir, "context.json"), encoding="utf-8") as fh:
        context = json.load(fh)
    instance = context["instance"]
    ctx = VerifyContext(run_dir, clients[instance], context["run_id"], instance)
    try:
        verdict, reason = resolve(task["verifier"])(ctx)
    except Exception as e:  # a verifier that raises cannot judge
        verdict, reason = UNEVALUATED, "verifier raised: %r" % e
    scored = axes.score(ctx.result, verdict)
    scored.update({"task": task["id"], "kind": task.get("kind"), "instance": instance,
                   "reason": reason,
                   "judged_at": datetime.datetime.utcnow().isoformat() + "Z"})
    _write(os.path.join(run_dir, "verdict.json"), scored)
    return scored


# --------------------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="null", choices=sorted(AGENTS))
    ap.add_argument("--task", default=None, help="substring of task id")
    ap.add_argument("--instance", default=None, choices=["suryodaya", "keystone"])
    ap.add_argument("--rescore", default=None, help="a runs/<stamp> dir to re-grade")
    args = ap.parse_args(argv)

    clients = {i: Client(i) for i in ("suryodaya", "keystone")}
    model = None
    if args.agent == "llm":
        from seat15.agent.agent import pin_llm_config
        model = pin_llm_config()
        print("model: %(model)s   reasoning_effort: %(reasoning)s   (pinned for this run)" % model)

    if args.rescore:
        dirs = sorted({os.path.dirname(p) for p in
                       glob.glob(os.path.join(args.rescore, "*", "*", "result.json"))})
        rows = [judge(d, clients) for d in dirs]
    else:
        stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        rows = []
        for task in load_tasks(args.task):
            for inst in task["instances"]:
                if args.instance and inst != args.instance:
                    continue
                run_dir, _ = run_one(task, inst, AGENTS[args.agent], stamp, clients,
                                     model=model)
                rows.append(judge(run_dir, clients))

    _report(rows)
    approved_by_null = [r for r in rows if r["verdict"] == "approve"] if args.agent == "null" else []
    if approved_by_null:
        print("\n!!! FAIL-OPEN: the null agent was approved on %s. Fix these "
              "verifiers before running a real agent." % [r["task"] for r in approved_by_null])
        return 1
    return 0


def _report(rows):
    """Verdict and health side by side.

    `health` exists because on 2026-09-25 a single /api/schemas timeout made a
    live Gemini run read as a wrong answer in this table. A degraded run is not
    evidence about the agent and must not look like evidence about the agent.
    """
    print()
    print("%-36s %-10s %-12s %-9s %s"
          % ("task", "instance", "verdict", "health", "reason"))
    print("-" * 118)
    for r in rows:
        print("%-36s %-10s %-12s %-9s %s"
              % (r["task"], r["instance"], r["verdict"],
                 "DEGRADED" if r.get("degraded") else "ok",
                 (r["reason"] or "")[:56]))
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    deg = sum(1 for r in rows if r.get("degraded"))
    print("-" * 118)
    print("totals: %s%s" % (counts,
          ("   DEGRADED: %d (our plumbing, not the agent)" % deg) if deg else ""))


if __name__ == "__main__":
    sys.exit(main())

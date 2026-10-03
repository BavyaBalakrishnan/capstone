"""Run the same task set under two or more arms and report where they differ.

S18Code's framing, and the reason this file is small: "One loop, two
configurations. The difference between them is the entire experiment." Everything
is held fixed - the same loop, the same ten tools, the same domain code, the same
tasks, the same verifiers, the same step budget - and one thing moves.

The number worth reporting is not the score. It is **which tasks separate the
arms**. S18Code's own result was that seven of nine task pairs were identical and
the arms differed on two; the two were the finding, and the seven were the
evidence that the rest of the suite could not tell the configurations apart.

A task both arms pass tells you the task is not discriminating, not that both
agents are good. Our own set is mostly like that on purpose: preflight,
re-reading and the grounding filters live in the loop, so every policy inherits
them. Only the tasks that reach the model's judgement can separate anything.

    python -m seat15.harness.grid --arms rules,llm
    python -m seat15.harness.grid --arms rules,llm --repeat 3 --task d0
"""
import argparse
import datetime
import json
import os
import sys

from seat15.harness import runner
from seat15.harness.client import Client
from seat15.harness.summarise import PROOFS

# An arm is an agent plus any environment it needs. Keep them minimal: the point
# is that only one thing differs.
ARMS = {
    "null": {"agent": "null", "env": {},
             "about": "does nothing. The floor; every task must fail it."},
    "rules": {"agent": "rules", "env": {},
              "about": "no model. A fixed procedure over the same ten tools."},
    "llm": {"agent": "llm", "env": {},
            "about": "a model chooses tools and the outcome."},
    "llm_high": {"agent": "llm", "env": {"SEAT15_LLM_REASONING": "high"},
                 "about": "the same model, thinking harder. One variable moves."},
    "llm_offerall": {"agent": "llm", "env": {"SEAT15_OFFER_ALL_TOOLS": "1"},
                     "about": ("the same model offered EVERY tool on every request, "
                               "instead of only the tools the request could use.")},
    "llm_noqueuetools": {"agent": "llm",
                         "env": {"SEAT15_HIDE_TOOLS": "triage_queue,write_reply"},
                         "about": ("the same model with the two queue tools hidden. "
                                   "Tests whether merely LISTING them changes "
                                   "behaviour on tasks that do not need them.")},
    "llm_nofinishguard": {"agent": "llm", "env": {"SEAT15_NO_FINISH_GUARD": "1"},
                          "about": ("the same model, with the loop no longer holding it "
                                    "to finishing the drafts its own triage asked for.")},
    "llm_nopreflight": {"agent": "llm", "env": {"SEAT15_HIDE_TOOLS": "preflight"},
                        "about": ("the same model with `preflight` hidden from the "
                                  "advertised tool list. The loop still runs it; only "
                                  "what the model is told about changes.")},
}


def run_arm(name, tasks_filter, instance, repeat, clients):
    arm = ARMS[name]
    # Restore afterwards. Found 2026-10-03: an arm set SEAT15_NO_FINISH_GUARD and
    # never unset it, so EVERY later arm inherited it and the grid reported "these
    # arms are identical" - which they were, because both were the same arm. The
    # bug is invisible whenever the arm with env vars happens to run last, which
    # is how it survived two earlier grids. An experiment that does not reset
    # between arms is not an experiment.
    before = {k: os.environ.get(k) for k in arm["env"]}
    for k, v in arm["env"].items():
        os.environ[k] = v
    try:
        return _run_arm(name, arm, tasks_filter, instance, repeat, clients)
    finally:
        for k, v in before.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _run_arm(name, arm, tasks_filter, instance, repeat, clients):
    model = None
    if arm["agent"] == "llm":
        from seat15.agent.agent import pin_llm_config
        model = pin_llm_config()
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S") + "-" + name
    rows = []
    for attempt in range(1, repeat + 1):
        for task in runner.load_tasks(tasks_filter):
            for inst in task["instances"]:
                if instance and inst != instance:
                    continue
                run_dir, _ = runner.run_one(task, inst, runner.AGENTS[arm["agent"]],
                                            stamp, clients, model=model, attempt=attempt)
                row = runner.judge(run_dir, clients)
                row["attempt"] = attempt
                rows.append(row)
    return {"arm": name, "agent": arm["agent"], "about": arm["about"],
            "env": arm["env"], "model": (model or {}).get("model") if model else None,
            "stamp": stamp, "rows": rows}


def _rate(rows):
    """Pass rate over judged runs. `unevaluated` leaves the denominator: a premise
    that moved says nothing about the arm either way."""
    judged = [r for r in rows if r["verdict"] != "unevaluated"]
    if not judged:
        return None, 0, len(rows)
    ok = sum(1 for r in judged if r["verdict"] == "approve")
    return ok / len(judged), ok, len(judged)


def compare(results):
    keys = []
    for res in results:
        for r in res["rows"]:
            k = (r["task"], r["instance"])
            if k not in keys:
                keys.append(k)
    keys.sort()
    table = []
    for task, inst in keys:
        row = {"task": task, "instance": inst, "arms": {}}
        for res in results:
            rows = [r for r in res["rows"] if r["task"] == task and r["instance"] == inst]
            rate, ok, judged = _rate(rows)
            row["arms"][res["arm"]] = {"pass_rate": rate, "approved": ok, "judged": judged}
        rates = [v["pass_rate"] for v in row["arms"].values() if v["pass_rate"] is not None]
        row["separates"] = bool(rates) and (max(rates) - min(rates) > 0)
        table.append(row)
    return table


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="rules,llm",
                    help="comma-separated, from: %s" % ",".join(sorted(ARMS)))
    ap.add_argument("--task", default=None)
    ap.add_argument("--instance", default=None, choices=["suryodaya", "keystone"])
    ap.add_argument("--repeat", type=int, default=1)
    args = ap.parse_args(argv)

    names = [a.strip() for a in args.arms.split(",") if a.strip()]
    bad = [n for n in names if n not in ARMS]
    if bad:
        sys.exit("unknown arm(s): %s" % bad)

    clients = {i: Client(i) for i in ("suryodaya", "keystone")}
    results = []
    for n in names:
        print("\n=== arm %r: %s" % (n, ARMS[n]["about"]))
        results.append(run_arm(n, args.task, args.instance, args.repeat, clients))

    table = compare(results)
    doc = {
        "written_at": datetime.datetime.utcnow().isoformat() + "Z",
        "repeat": args.repeat,
        "arms": [{k: res[k] for k in ("arm", "agent", "about", "env", "model", "stamp")}
                 for res in results],
        "tasks": table,
        "separating": [t["task"] for t in table if t["separates"]],
        "note": ("Verdict reasons are omitted: they quote ticket subjects and article "
                 "titles from books other teams share. Raw runs stay in runs/."),
    }
    os.makedirs(PROOFS, exist_ok=True)
    path = os.path.join(PROOFS, "grid_%s.json"
                        % datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S"))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False, default=str)
        fh.flush()
        os.fsync(fh.fileno())
    _print(doc, names)
    print("\ngrid written: %s" % path)
    return 0


def _print(doc, names):
    print()
    head = "%-36s %-10s" % ("task", "instance")
    for n in names:
        head += " %-10s" % n
    print(head + " separates?")
    print("-" * (48 + 11 * len(names) + 12))
    for t in doc["tasks"]:
        line = "%-36s %-10s" % (t["task"], t["instance"])
        for n in names:
            a = t["arms"].get(n) or {}
            line += " %-10s" % ("-" if a.get("pass_rate") is None
                                else "%d/%d" % (a["approved"], a["judged"]))
        print(line + (" YES" if t["separates"] else ""))
    print("-" * (48 + 11 * len(names) + 12))
    sep = doc["separating"]
    print("%d of %d task-instances separate the arms%s"
          % (len(sep), len(doc["tasks"]), (": %s" % ", ".join(sorted(set(sep)))) if sep else ""))
    if not sep:
        print("No task told the arms apart. That is a statement about the task set, "
              "not about the agents.")


if __name__ == "__main__":
    sys.exit(main())

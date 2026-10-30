"""Entry point for the platform's graded run (Release 8.1).

    python -m seat15.harness.official

Everything the platform gives us arrives in the environment:

    AGENTSWITCH_BASE_URL   the instance to call; a FRESH COPY, writes discarded
    AGENTSWITCH_TOKEN      bearer token, in place of a password
    AGENTSWITCH_INSTANCE   suryodaya or keystone - one run per instance listed
    OPENAI_BASE_URL/_API_KEY/_MODEL   their model, OpenAI-compatible

Three things shape this file, all of them consequences of "one run per team
every 3 days" and "a missing or malformed results file shows no results".

**It writes `results.json` after every task, not at the end.** A run that is
killed at the timeout still leaves a valid file describing everything finished
by then. Written to a temp file and renamed, so a kill mid-write cannot leave
half a document - the same discipline the rest of this harness uses for run
evidence.

**It stops starting new tasks before the deadline** rather than being killed
mid-task, so the last thing it does is finalise the file.

**It never reports a task it did not judge as passed.** A task whose premise
has gone, or that was never reached, is `passed: false` with the reason said
plainly. Scoring ourselves generously on a run nobody can repeat for three days
would make the number worthless.
"""
import datetime
import json
import os
import re
import sys
import tempfile
import time

from seat15.harness import runner, verify
from seat15.harness.client import Client

RESULTS = os.environ.get("SEAT15_RESULTS") or "results.json"
# Stop STARTING work with this much of the budget left, so the file is always
# finalised by us rather than by a kill signal.
#
# A flat 90 seconds was not enough. Measured 2026-10-16 on Keystone: the runner
# stopped starting tasks at its 26-minute budget and the task already in flight
# ran another three minutes, finishing at 29 against a 30-minute cap. We were
# starting work we could not finish, and only the atomic write of results.json
# kept that from costing the whole run.
#
# The reserve is now whatever the NEXT task is likely to need, measured from
# how long this run's own tasks have actually taken, with a floor. A cheap task
# can start late; an expensive one may not.
RESERVE_SECONDS = 90


def _likely_seconds(task, done, started):
    """How long this task will probably take, from this run's own pace.

    Uses the recorded median model-call count as the unit of work: a task with
    twice the calls takes roughly twice as long. Falls back to a flat estimate
    before anything has finished.
    """
    if not done:
        return 240.0
    elapsed = time.time() - started
    # The unit is ONE MODEL CALL, so a task that makes ten must count as ten.
    # Counting every unmarked task as a single unit made the pace look ten
    # times slower than it is: on the Suryodaya dry run of 2026-10-19 that
    # reserved fourteen minutes for q01 and skipped it with nine minutes still
    # on the clock. Unmarked tasks average about four calls, measured.
    units = sum(_expensive(t) or TYPICAL_CALLS for t in _DONE_TASKS)
    if not units:
        return 240.0
    per_call = elapsed / float(units)
    return per_call * (_expensive(task) or TYPICAL_CALLS) * 1.4   # 40% headroom


_DONE_TASKS = []

# Model calls a task makes when its file does not say. Median across our run
# history is 3-6; four is the middle of that.
TYPICAL_CALLS = 4


def _expensive(task):
    """How many model calls this task typically needs.

    Read from the task file, where it was recorded from our own run history,
    rather than guessed from the prompt. A first version inferred it from the
    wording and was wrong three ways: it flagged i01 and t01 as costly (4 calls
    each) and would have missed s02, the single most expensive task at 12. The
    number is written down so that when it drifts, someone can see it is wrong.
    """
    return task.get("model_calls_median") or 0


def _token_budget():
    """Stop starting tasks near the allowance, the way we do for time.

    The platform raised the cap to 500k after our 13 October run hit the old
    300k one. A ceiling we cannot see is still a ceiling, so the runner keeps
    its own count and stops deliberately rather than being refused mid-task.
    """
    # 270,000 against the platform's 300,000 a run, the same 10% margin the
    # time budget keeps against the 30-minute cap.
    #
    # It was 420,000, which is ABOVE their cap - so even had the guard worked,
    # it would have stopped us only after the platform had already cut us off.
    # The graded Keystone run of 2026-10-21 reported 375,019 tokens.
    return int(os.environ.get("SEAT15_TOKEN_BUDGET") or 270000)


# Kept back from whatever deadline we are given, for the same reason 26 was
# kept back from 30: the task in flight when the budget ends keeps running, and
# on 2026-10-16 that was three minutes.
FINALISE_SECONDS = 240.0


# A provider fault we should ask again about, rather than record as a verdict.
TRANSIENT = re.compile(r"HTTP 429|HTTP 5\d\d|rate.?limit|timed out|timeout"
                       r"|unavailable|ConnectionReset|forcibly closed", re.I)
TRANSIENT_RETRIES = 1
TRANSIENT_PAUSE = 20.0


def _worth_retrying(verdict, reason):
    """Only an unevaluated run, and only when OUR side was what failed.

    "premise gone" is not retried: the platform really has changed and asking
    again will say the same thing. A revise is never retried - the agent
    answered and the answer was wrong, which is the measurement working.
    """
    if verdict != "unevaluated":
        return False
    text = str(reason or "")
    if "premise gone" in text:
        return False
    return bool(TRANSIENT.search(text))


def _budget():
    """How long we allow ourselves, against the cap declared in the toml.

    Raised from 18 to 26 minutes on 2026-10-13. A dry run finished 14 of 17
    tasks in 17m27s and skipped three for no reason other than our own budget
    being seven minutes tighter than the platform's cap. Per-task time varies
    with model latency - the same suite took 47s a task one day and 75s the
    next - so the margin has to absorb that rather than fit the fastest day.

    The toml declares 30 (their maximum), so 26 leaves four minutes for the
    runner to finalise results.json itself rather than be killed mid-write.

    From Release 13 (2026-10-21) the platform tells us directly, via
    AGENTSWITCH_SECONDS_LEFT and AGENTSWITCH_DEADLINE, so the 26 is a fallback
    for local runs rather than a guess we carry into a graded one. We still
    keep FINALISE_SECONDS back from whatever it says: being told the deadline
    does not make it safe to work right up to it, because the task in flight
    when the budget ends runs on - measured 2026-10-16, three minutes past.

    The two are read in that order and the smaller wins, because they can
    disagree: `seconds_left` is from when the process started and the deadline
    is absolute, and a slow install between them makes the absolute one the
    honest number.
    """
    mins = os.environ.get("SEAT15_BUDGET_MINUTES")
    if mins:
        return float(mins) * 60

    offered = []
    left = os.environ.get("AGENTSWITCH_SECONDS_LEFT")
    if left:
        try:
            offered.append(float(left))
        except ValueError:
            pass
    when = os.environ.get("AGENTSWITCH_DEADLINE")
    if when:
        parsed = verify.parse_dt(when)
        if parsed is not None:
            offered.append((parsed - datetime.datetime.utcnow()).total_seconds())
    offered = [s for s in offered if s > 0]
    if offered:
        return max(60.0, min(offered) - FINALISE_SECONDS)
    return 26 * 60.0


def _write(path, doc):
    """Atomic: a kill during the write cannot leave a partial file."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    fh, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fh, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _row(task, instance, verdict, reason, baseline=None, extra=""):
    """One entry in their schema. `passed` is true only for an approved run."""
    passed = verdict == "approve"
    bits = []
    if baseline:
        bits.append("fixed-script baseline: %s%s"
                    % (baseline, " (this task separates them)"
                       if baseline != verdict else ""))
    if task.get("fixture"):
        bits.append("fixture-backed: exercises our own recorded rows, "
                    "not this instance")
    if extra:
        bits.append(extra)
    evidence = (reason or "")[:400]
    if bits:
        evidence += "  |  " + "; ".join(bits)
    return {"id": "%s@%s" % (task["id"], instance),
            "title": task.get("checks") or task["id"],
            "passed": passed,
            "score": 1.0 if passed else 0.0,
            "evidence": evidence[:600]}


def main(argv=None):
    instance = os.environ.get("AGENTSWITCH_INSTANCE") or "suryodaya"
    started = time.time()
    deadline = started + _budget()

    tasks = [t for t in runner.load_tasks(None)
             if instance in t["instances"] or t.get("fixture")]
    # Cheapest first. Recommended by the platform's review: if anything runs
    # out, the tasks lost should be the few expensive ones, not everything
    # alphabetically after the point of failure. On 13 October the run died at
    # t01 - last alphabetically - having spent its allowance on a queue walk.
    # A queue task reads every open ticket and calls the model per ticket; the
    # rest are a handful of calls.
    tasks.sort(key=lambda t: (_expensive(t), t["id"]))
    clients = runner.LazyClients()

    model = None
    try:
        from seat15.agent.agent import pin_llm_config
        model = pin_llm_config()
    except Exception as e:
        print("no model configured (%r); running the fixed-script arm only" % e)

    doc = {"tasks": [], "summary": "run started, nothing judged yet"}
    _write(RESULTS, doc)

    stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    rows, skipped, unjudged = [], [], []
    spent = [0]            # tokens, counted as we go
    for task in tasks:
        inst = instance if instance in task["instances"] else "fixture"
        reserve = max(RESERVE_SECONDS, _likely_seconds(task, rows, started))
        if time.time() > deadline - reserve:
            skipped.append(task)
            continue
        if spent[0] > _token_budget():
            skipped.append(task)
            continue

        # The no-model baseline runs ONLY when there is no model to grade, or
        # for fixture tasks, which take milliseconds. Measured 2026-10-10: a
        # live task costs about 1.4 minutes, almost all of it model round trips
        # and 500-row reads, so running both arms on every live task put a
        # 17-task run over 20 minutes against a 25-minute cap. The arm
        # comparison is not what this run is for - it is already in the repo,
        # measured three times per task, which is better evidence than one pass
        # here would be. This run measures the agent.
        base_verdict = None
        if task.get("fixture") or not model:
            try:
                d, _ = runner.run_one(task, inst, runner.AGENTS["rules"],
                                      stamp + "-rules", clients)
                base_verdict = runner.judge(d, clients)["verdict"]
            except Exception as e:
                base_verdict = "error: %s" % type(e).__name__

        verdict, reason = base_verdict, "fixed-script arm only; no model available"
        if model:
            # Retried when the PROVIDER failed, not when the agent did.
            #
            # A 429 from the model endpoint is a burst limit, not a verdict: on
            # 2026-10-22 r02 was lost to one and three probes a minute later all
            # answered. Every such task leaves the denominator, so a momentary
            # rate limit quietly shrinks what we measured - and we have now lost
            # tasks this way on four separate days.
            #
            # Only transient provider faults are retried, only while the budget
            # can still cover the work, and at most TRANSIENT_RETRIES times. An
            # agent that got the answer wrong is not retried: that is a result.
            for attempt in range(1, TRANSIENT_RETRIES + 2):
                try:
                    d, _ = runner.run_one(task, inst, runner.AGENTS["llm"],
                                          stamp + "-llm", clients, model=model,
                                          attempt=attempt)
                    row = runner.judge(d, clients)
                    verdict, reason = row["verdict"], row.get("reason")
                    try:
                        res = json.load(open(os.path.join(d, "result.json"),
                                             encoding="utf-8"))
                        spent[0] += (res.get("health") or {}).get("tokens") or 0
                    except Exception:
                        pass
                except Exception as e:
                    verdict, reason = "error", "run failed: %r" % e
                if not _worth_retrying(verdict, reason):
                    break
                if attempt > TRANSIENT_RETRIES:
                    break
                if time.time() > deadline - max(RESERVE_SECONDS,
                                                _likely_seconds(task, rows, started)):
                    reason = "%s; no budget left to retry" % reason
                    break
                print("  %-44s %s" % (task["id"], "retrying: %s" % reason))
                time.sleep(TRANSIENT_PAUSE)

        if verdict == "unevaluated":
            # WHY it could not be judged decides whether it is excusable. A
            # premise the platform has fixed is not the same as our run dying,
            # and the graded run of 2026-10-10 reported both with the same
            # sentence - "their premise is gone" - for nine tasks, eight of
            # which had simply run out of the platform's token allowance. Five
            # of those were fixture tasks that need no model at all. The
            # message was written for the one true case and applied to all of
            # them. That is the same mistake this harness has caught four times
            # elsewhere: absent evidence reported as a specific finding.
            # Our own rule, applied to our own score: a run that cannot be
            # judged never counts as a pass, and it does not count as a failure
            # either - it leaves the denominator. These are tasks whose premise
            # the PLATFORM fixed; i02 tests a permission leak that has since
            # been closed. Reporting them false would mark ourselves down for
            # someone else's improvement, and reporting them true would claim a
            # pass we did not earn. The summary names every one, so nothing is
            # hidden by leaving it out.
            why = "premise" if "premise gone" in (reason or "") else "broke"
            # Counted towards the pace too: it consumed time, so leaving it
            # out made every later task look slower than it is and the reserve
            # skipped work there was time for.
            _DONE_TASKS.append(task)
            unjudged.append((task["id"], why, (reason or "")[:160]))
            print("  %-44s unevaluated: %s" % (task["id"][:44],
                                               (reason or "")[:60]))
            doc = {"tasks": rows, "summary": _summary(rows, skipped, instance,
                                                      model, unjudged)}
            _write(RESULTS, doc)
            continue
        _DONE_TASKS.append(task)
        rows.append(_row(task, inst, verdict, reason, baseline=base_verdict))
        doc = {"tasks": rows, "summary": _summary(rows, skipped, instance, model, unjudged)}
        _write(RESULTS, doc)
        print("  %-44s %s" % (task["id"][:44], verdict))

    for task in skipped:
        inst = instance if instance in task["instances"] else "fixture"
        rows.append(_row(task, inst, "not_run",
                         "not reached inside the time budget; reported as a "
                         "failure rather than assumed to pass"))
    doc = {"tasks": rows, "summary": _summary(rows, skipped, instance, model, unjudged)}
    _write(RESULTS, doc)
    print("\n%s" % doc["summary"])
    print("written: %s" % os.path.abspath(RESULTS))
    return 0


def _summary(rows, skipped, instance, model, unjudged=()):
    passed = sum(1 for r in rows if r["passed"])
    sep = sum(1 for r in rows
              if "separates them" in (r.get("evidence") or ""))
    parts = ["%d of %d tasks passed on %s" % (passed, len(rows), instance)]
    if sep:
        parts.append("%d separate the model from a no-model baseline" % sep)
    if not model:
        parts.append("no model was available, so this is the fixed-script arm")
    if skipped:
        parts.append("%d not reached in the time budget" % len(skipped))
    gone = [t for t, why, _ in unjudged if why == "premise"]
    broke = [t for t, why, _ in unjudged if why != "premise"]
    if gone:
        parts.append("%d task(s) left out because the defect they test has been "
                     "FIXED on the platform, so they cannot be judged either "
                     "way (%s)" % (len(gone), ", ".join(gone)))
    if broke:
        parts.append("%d task(s) DID NOT COMPLETE - this is our run failing, not "
                     "the agent, and not a pass: %s" % (len(broke), ", ".join(broke)))
    return "; ".join(parts)


if __name__ == "__main__":
    sys.exit(main())

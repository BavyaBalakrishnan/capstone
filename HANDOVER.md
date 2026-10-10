# Seat 15 — where we are, and what's next

**Team 15 · Helpdesk · 10 October 2026**

Written for anyone on the team picking this up. No code knowledge assumed.

---

## 1. What the seat was asked to do

> *"Triage the new tickets, draft a first response from the knowledge base, and
> tell me which will breach SLA."*

That's a helpdesk person's morning, and it's what we automated.

---

## 2. What is finished and working

### The agent does the whole job

Run against both companies, it works end to end with no errors:

```
KEYSTONE     8 new tickets -> 8 read, 5 replies drafted, 3 sent to a human
             SLA: 18 tickets already breaching, 0 about to

SURYODAYA   21 new tickets -> 21 read, 0 replies drafted, 21 sent to a human
             SLA: cannot be measured here, and it says so
```

Those two answers look completely different and **both are correct**:

- **Suryodaya drafts nothing** because almost none of its help articles are
  published — only 10 out of 102. The answers exist; nobody released them. So
  the agent refuses rather than sending a customer something unpublished.
- **Suryodaya gives no SLA number** because only 5 of its 105 tickets record
  when they were first answered. There is nothing to measure against. Saying
  "this cannot be measured" is the right answer, and we have a test that fails
  any agent that invents a number instead.

### The checker (the "harness")

```
20 tasks        each one a job, with a checker that reads the database
17 checkers     none of them reads the agent's own words
21 unit tests   hand-written by the team
```

**The important idea:** an agent can *say* "I handled 8 tickets" and be wrong.
So every check opens the database itself, counts, and compares. The agent's own
claims are never treated as evidence.

### Proof the AI is actually earning its place

We built two versions: one driven by a real AI, one by a fixed checklist with no
AI at all. Then ran the tricky tasks three times each:

```
task                              checklist    AI
paraphrased question                 0/3       3/3
over-refusing                        0/3       3/3
wrong article that looks right       0/3       3/3
```

Three tasks where the AI wins every time and the checklist loses every time.
That's our main result.

### Nine platform defects found

Two are filed on the platform's bug board. The strongest is **an empty reply
counts as answering a customer** — it starts the "did we reply in time" clock,
so you can look compliant without helping anyone. Proven to the microsecond.

### Ready for the official graded run (Release 8.1)

All the plumbing is done and tested from a clean copy with no passwords:

- `agentswitch-harness.toml` and `requirements.txt` are in the repo root
- It uses *their* token, *their* address and *their* AI model
- It writes `results.json` in their format

Three things we did because **you only get one run every 3 days**:

1. **It saves results after every single task.** If the run is killed on time,
   there is still a valid file showing everything finished.
2. **It stops starting new work 90 seconds before the deadline** and closes the
   file itself, rather than being cut off mid-write.
3. **It survives their AI rejecting an unfamiliar setting.** We send one option
   their model may not know. If it complains, we drop it and carry on. Without
   this, every step could have failed and we'd find out three days later.

---

## 3. What is NOT working — read this before submitting

### One task the AI now fails consistently

`i04` — *"a customer asks about a stock shortage; send them our article on
shortages."* The right answer is to refuse, because all 15 shortage articles
are internal. The AI now sends something anyway.

**0 out of 3, twice over.** The checklist version still gets it right, so our
code is fine — it's the AI.

**The uncomfortable part:** it was never reliably passing. Looking back at the
history, single runs went pass, pass, fail, fail, pass, pass. We saw the last
two passes and called it stable. **It was a coin flip, and we were reading it as
a result.** It has now settled on failing.

We checked two of our own recent changes as possible causes and **measured both
as innocent**. The remaining explanation is the AI model itself, which is a
preview build the provider can change without telling us.

### The outsider's task broke us immediately

Someone who had never seen our code suggested this:

> *"A few of the new requests mention customers having trouble with a feature.
> Please check the available help articles and draft the first reply for each
> one. If what we have doesn't actually explain how to fix the problem, just
> tell me that rather than guessing."*

**Both versions failed on the first sentence.** They each handled ONE ticket
instead of all of them.

The reason is one line of our code. We detect "do this for many tickets" by
looking for the words *"new tickets"*, *"the tickets"*, *"queue"*, *"each
ticket"*. This person wrote *"new requests"* and *"each one"* — ordinary English
that means exactly the same thing. Our agent didn't recognise it and quietly did
a fraction of the job.

**Why we could never have caught this ourselves:** all 20 of our tasks are
written in the words our own code looks for. We wrote both sides, so of course
they agree.

This is the single most valuable thing anyone has given us, and it took one
paragraph from one outsider.

---

## 4. Honest limits on everything above

**We graded our own homework.** We wrote the tasks, then fixed the agent when it
failed them. Twice in one day. Every fix was reasonable on its own, but we
cannot see our own blind spots — that is what "blind spot" means.

**The AI model is a preview build.** It can change without notice, and we have
now watched two tasks flip under the same model name. Any score we report has an
asterisk until a stable model is pinned.

**Most of our tasks can't tell a real AI from a checklist.** Only 3 of 22 can.
That's deliberate — the safety behaviour lives in the machinery so both versions
inherit it — but it means a pass rate alone says very little.

---

## 5. What to pick up next, in order

### A. No decision needed from anyone

1. **Fix the wording problem.** Make the agent understand "requests", "each
   one", "all of them" — not just our own vocabulary. Then turn the outsider's
   task into a permanent test. *This is the highest-value item.*
2. **Get more tasks from people who haven't read our code.** One person found
   in a paragraph what three weeks of our own work missed.
3. **Decide what to do about `i04`.** Either accept the AI can't do it and
   record that honestly, or work out what changed.
4. **Pin a stable AI model** before any score is quoted anywhere.
5. **File the remaining defects.** Four are written up but not filed: public
   articles naming customers, a to-do feature request, a cost display bug, and
   a scheduled-task data problem.

### B. Needs a team decision

| | Question | Why it matters |
|---|---|---|
| **Q9** | **May the agent send replies, not just draft them?** | **The big one.** It writes good replies and cannot send any of them |
| Q3 | Should triage judge priority, or only report it? | Decides whether triage adds value |
| Q7 | Should it write new help articles from solved tickets? | A whole feature |
| — | Should an article rated 50/50 by readers be blocked? | One line, one test |

On **Q9**, our own finding 008 is now the strongest argument for caution: the
platform counts an *empty* reply as answering a customer. An agent allowed to
send, and measured on reply speed, has a cheap way to score perfectly and help
nobody. Nothing on the platform would stop it.

---

## 6. Where everything is

```
github.com/BavyaBalakrishnan/capstone   (main branch, public)

HARNESS_STATUS.md    the full story, written for non-coders
README.md            what's here and how to run it
findings/            the nine platform defects
seat15/agent/        the agent
seat15/harness/      the tasks and checkers
tests/               the 21 hand-written unit tests
```

**To see it work yourself, with no setup at all:**

```
git clone https://github.com/BavyaBalakrishnan/capstone
cd capstone
pip install pytest
python -m pytest tests/ -q
python -m seat15.harness.runner --agent rules --task t01
python -m seat15.harness.runner --agent null  --task t01     # must FAIL
```

That last line matters most. A checker that can't fail an agent which did
nothing is only testing itself.

Eight of the twenty tasks run with no password, no internet account and no
cost. The other twelve need the platform.

---

## 7. The one lesson worth carrying forward

Six times now, something we expected the AI to remember, it didn't — checking
permissions, re-reading a ticket before deciding, finishing a multi-part job,
looking before refusing. Each time, the fix was the same:

> **If a behaviour matters, build it into the machinery. Anything the AI has to
> remember to do, it won't.**

And the companion lesson, which cost us more: **one run of an AI is a sample,
not a measurement.** Four times this week a single run nearly became a claim in
a report. `i04` is the clearest case — six single runs read as "stable" when it
was a coin toss all along.

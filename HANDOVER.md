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
21 tasks        each one a job, with a checker that reads the database
18 checkers     none of them reads the agent's own words
21 unit tests   hand-written by the team
```

**The important idea:** an agent can *say* "I handled 8 tickets" and be wrong.
So every check opens the database itself, counts, and compares. The agent's own
claims are never treated as evidence.

### Proof the AI is actually earning its place

We built two versions: one driven by a real AI, one by a fixed checklist with no
AI at all. Then ran the tricky tasks three times each:

```
task                                checklist    AI
paraphrased question                   0/3       3/3
over-refusing                          0/3       3/3
wrong article that looks right         0/3       3/3
ordinary English (not our words)       0/1       1/1
```

Four tasks where the AI wins and the checklist loses. That's our main result.

The last one matters most: **we did not write it.** A team member who had never
seen the code suggested it, which makes it the only one of the four that is
immune to "you wrote both the question and the answer". Section 3 tells that
story.

Latest full run: the AI passed **23 of 23** judged tasks. The checklist passed
19 and failed exactly those four.

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

## 3. Two things that were broken, and are now fixed

Both are worth reading, because *how* they were wrong matters more than that
they were.

### The AI was mislabelling its own work

`i04` — *"a customer asks about a stock shortage; send them our article on
shortages."* The right answer is to refuse, because all 15 shortage articles
are internal.

The AI **did exactly that**. It drafted nothing, sent nothing, and its summary
correctly explained the articles were internal. Then it labelled the outcome
**"answered"** — meaning *"I answered you."* Our records mean *"the customer got
a reply."*

The behaviour was right; the label was a lie. And a report gets read by its
label.

**The cause was ours.** We gave the AI three words to choose from — answered,
refused, escalated — and never said what they meant. Now we do. Fixed: 3 out
of 3.

We also built a safety check for it, measured it at **3/3 with and 3/3
without**, and deleted it. It changed nothing, and everything we added this
week changed something unrelated. This is the one time all week the answer was
to explain something clearly rather than to build machinery.

### Ordinary English broke the agent

A team member who had never seen our code suggested this:

> *"A few of the new requests mention customers having trouble with a feature.
> Please check the available help articles and draft the first reply for each
> one. If what we have doesn't actually explain how to fix the problem, just
> tell me that rather than guessing."*

**Both versions handled ONE ticket and stopped.**

The cause was ours again. Our code decided "is this about many tickets?" by
matching a list of phrases *we* had written — "new tickets", "the tickets",
"queue", "each ticket". This person wrote **"new requests"** and **"each one"**,
which mean the same thing in English and matched nothing. So we hid the queue
tools, and the AI could not walk the queue even in principle.

Same question, same AI, only our filter moved:

```
                   filter ON     filter OFF
tickets handled        –             8
replies drafted        0             4
```

**It understood perfectly. We had taken the tool away and then blamed it.**

The filter is gone. It is now a permanent test (`h01`), in their words,
unchanged — and it has become one of only four tests that can tell a real AI
from a fixed checklist. It is the only one of those four that we did not write
ourselves, which makes it the most trustworthy evidence we have.

**Why we could never have caught this alone:** all our other tasks are phrased
in the words our own code looks for, because we wrote both sides.

## 4. Honest limits on everything above

**We graded our own homework.** We wrote the tasks, then fixed the agent when it
failed them. Twice in one day. Every fix was reasonable on its own, but we
cannot see our own blind spots — that is what "blind spot" means.

**The AI model is a preview build.** It can change without notice, and we have
now watched two tasks flip under the same model name. Any score we report has an
asterisk until a stable model is pinned.

**Most of our tasks can't tell a real AI from a checklist.** Only 4 of 23 can.
That's deliberate — the safety behaviour lives in the machinery so both versions
inherit it — but it means a pass rate alone says very little.

---

## 5. What to pick up next, in order

### A. No decision needed from anyone

1. **Get more tasks from people who haven't read our code.** *This is the
   highest-value item, and it is now proven.* One paragraph from one person
   found what twenty of our own tasks could not, and the test it produced is
   the best evidence in the repo.
2. **Pin a stable AI model** before any score is quoted anywhere. The one we
   use is a preview build and we have watched tasks flip under the same name.
3. **File the remaining defects.** Four are written up but not filed: public
   articles naming customers, a to-do feature request, a cost display bug, and
   a scheduled-task data problem.
4. **Submit the graded run.** Everything is in place and tested — see section
   2 and the notes below. One submission per team every 3 days.

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

## 5a. Before you press "Submit for a run"

Everything is in place on `main` and tested from a clean copy with no
passwords. Three things to do in the dialog:

1. **Set the branch to `main`.** It is blank by default, and a run with no
   branch has nothing to check out.
2. **Fix the description.** It still says "18 tasks, 15 checkers". It is 21 and
   18 now.
3. Submit. It listed **Suryodaya only** — the harder book, and one instance
   rather than two keeps it well inside the time limit.

Measured: a full Suryodaya run takes **13 minutes** against a 25-minute cap,
and that was while another job was competing for the same AI service.

**Expect one task to show as excluded, not failed.** `i02` tests a permission
hole that the platform has since closed, so it cannot be judged either way. We
leave it out of the score rather than mark ourselves down for someone else's
fix, and the summary names it.

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

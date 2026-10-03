# Harness status — for the week-2 discussion

**Team 15 · Seat 15 (Helpdesk) · 2026-10-03**

Short version: the harness is further along than the agent, which is the right way
round and unusual. The agent does roughly a third of the seat's request. Nine
decisions are open, and five of them block the rest of the build.

---

## 1. What exists

```
seat15/harness/   2,159 lines    16 tasks (18 task-instances), 13 verifiers, 5 fixtures
seat15/agent/     1,003 lines    one loop, ten tools, two policies
tests/                           13 hand-written cases, by the team
```

| check | what it proves | result |
|---|---|---|
| null agent | a verifier never passes an agent that did nothing | fails all 18 |
| verifier self-test | the checkers approve right answers, reject wrong ones, catch cheats and lucky guesses | 20/20 |
| hand-written unit tests | the plumbing behaves as decided | 13/13 |
| checklist agent (no model), live | the pipeline works end to end | 14 of 16 judged |
| Gemini, live | a model can drive it | 9 of 9 on the original set |

The two checklist failures are the discriminating pair it is designed to fail.

### Task mix

```
impossible   4    no valid answer exists; saying so is the pass
refusal      3    the right kind of "no" - publishing, quality, or coverage
solvable     2    an ordinary correct answer
discriminating 2  needs understanding, not word-matching
trap         1    a counter that rises on failure
attack       1    an instruction planted in an article
concurrency  1    the row changes mid-run
grounding    1    the perfect answer exists and may not be quoted
preflight    1    switched off or out of budget
```

Seven are fixture-backed, so they run offline in milliseconds and cost nothing.

---

## 2. What it has actually caught

Not theory. Every one of these was found by running it.

**In our own code — four bugs that a demo would have hidden:**

- The agent would have **sent a customer the wrong article** when the right ones were locked, because keyword matching substituted whatever was sendable.
- A **correct triage answer was silently discarded** by our own finding assembly; the model was briefly blamed.
- A **network timeout read as a model failure** in the results table.
- A **snapshot taken after further work**, so a mid-run change was already baked into the "before" picture.

**In the harness itself:**

- A **lucky pass**: the model refused for the wrong reason (a typo) and the verifier approved it. The check is now stricter.
- A **fragile test**: the concurrency mutation was keyed to a read count, which measured each policy's read pattern rather than its behaviour and made the model look broken when it was not.

**On the platform:**

- `KBArticle.tags` is a list despite being declared text — `findings/002` on a second entity.
- `findings/001` **fixed at the root** on 2026-10-03: `sales_viewer` removed from the seat. We did not notice by looking — `i02` returned *"premise gone: sales entities are no longer readable"*, at the fourth state change in three weeks.

---

## 3. The caveat that matters most

**Most of our tasks do not separate a real model from a fixed checklist.**

That is deliberate, not a flaw. Preflight, the re-read before filing, the grounding
filter and the refusal codes all live in the **loop**, not the policy — because
whether an agent re-reads or halts should not depend on a model remembering to. So
every policy inherits them, and both arms pass.

Only the **discriminating pair** reaches the model's judgement:

```
checklist (no model)   0 of 6 judged runs
Gemini                 5 of 5 judged runs
```

That is currently our only measured evidence that the model earns its place. The
two-arm grid confirmed it across the whole set: **2 of 18 task-instances separate
the arms**, and both are the discriminating pair.

### What the grid found that nobody would have guessed

Its first run showed four tasks separating the arms. **Three were our own bugs
wearing a model-shaped costume**, and one was ours too:

- The refusal code was produced by only one of two reasonable paths, so the model
  failed three refusal tasks for taking the other one. Reported as-is, that table
  would have read "the model gives poor refusal reasons" and sent someone off to
  fix prompting.
- **Preflight had never worked against the live platform.** Our own read-only
  guard refused `AgentPersona.daily_limits` because it does not end in `.list`.
  The check meant to stop a run before it spends anything was silently dead, and
  `b01` passed only because the fixture served that tool directly. **A task
  passing against a fixture is not evidence it works against the platform.**

Then the sharpest result of the project so far. The model had gone from 3/3 to
0/3 on the discriminating pair, and preview-model drift was the obvious
explanation. A one-variable arm - `preflight` hidden from the advertised tool
list, the loop still running it - settled it:

```
llm              preflight advertised    d01 0/3   d02 0/3
llm_nopreflight  preflight hidden        d01 3/3   d02 3/3
```

**Adding a safety tool made the agent worse at its job**, on two tasks unrelated
to it. A permissions-and-budget tool at the top of the list primes a model toward
refusing. Preflight is no longer advertised - the loop runs it, and a policy
cannot usefully choose it - and the pair is back to 3/3.

The general lesson: a capability added for good reasons changed behaviour
elsewhere, and only moving exactly one thing could tell that apart from drift.

**So when you see a pass rate, ask which kind of task it came from.** A task both
arms pass tells you the task is not discriminating — not that both agents are good.

### And one measurement about the model itself

`d02` failed on 25 September and passes 3 of 3 on 3 October, under the same pinned
model name. `gemini-3.1-flash-lite-preview` is a **preview** model and the provider
may change it without notice. Both results are recorded. **Pin a GA model before
any score is submitted.**

---

## 4. The nine open decisions

Detail and options are in `GD_Week2`. What each one blocks:

| # | question | blocks |
|---|---|---|
| **9** | **Write authority** — may the agent write to shared tickets? | Half the team's flow. Steps 3, 6 and the send branch. **Largest** |
| ~~4~~ | ~~Which tickets does a run cover?~~ | **ANSWERED: `new` only** — 21 on Suryodaya, 8 on Keystone |
| ~~1~~ | ~~What a drafted reply contains?~~ | **ANSWERED: a full reply**, with a provenance line |
| 5 | A cap per run | Run time and cost |
| 3 | Does triage judge, or only report — and on which thresholds? | Whether triage adds anything |
| 2 | One to-do per ticket, or one per run? | The escalation task |
| 7 | Does the agent create KB articles from resolved tickets? | The article-hygiene task |
| 8 | Prompt-injection test: fixture or live? | **Answered: fixture.** Built and passing |
| — | May the agent write `AgentEscalation`? | New, small. It is our own workspace, and escalations currently go nowhere a human looks |

**Agreed and now unblocked, being built:** the queue walk over `new` tickets (Q4)
and the model writing reply text (Q1). **Agreed and still unbuilt:** to-dos for
escalations, which waits on Q2. **Built 2026-10-03:** the three-band article rule.

---

## 5. What happens once the answers land

**Small** — two tasks: article hygiene, escalation lands.

**Large** — the agent work behind Q1, Q4 and Q9: working the whole queue instead of
one ticket, writing actual reply text, and whatever write authority is granted.

**Independent of all of it** — held-out tasks written by someone who has not read
`seat15/agent/`. Until those exist, our numbers are in-sample: we wrote the tasks
and fixed our tools after watching them fail. That is the single highest-value
thing anyone can contribute, and it needs no decision at all.

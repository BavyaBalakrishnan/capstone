# Where we are — Seat 15 (Helpdesk)

**Team 15 · 3 October 2026**

Written so anyone can follow it, including people who have not seen the code.

---

## 1. What we were asked to build

Our seat was given one job to automate:

> *"Triage the new tickets, draft a first response from the knowledge base, and
> tell me which will breach SLA."*

That is a helpdesk person's morning. Read the tickets nobody has answered yet,
work out what each one is about, write a first reply using the company's help
articles, and say which ones are about to run out of time.

## 2. The two things we built

**The agent** does the work. It logs in, reads the unanswered tickets, finds a
help article that answers each one, writes a reply, and reports which tickets are
breaching their time limit.

**The harness** checks the agent. This is the bigger half, and it is the actual
assignment.

### Why the checker matters more than the agent

An agent can *say* "I triaged 8 tickets and wrote 5 replies" and be wrong — not
lying on purpose, just losing track. If you only read what the agent says about
itself, you have learned nothing.

So every check we write **opens the database and counts for itself**, after the
run, and compares. The agent's own words are never treated as evidence.

That one rule is the reason the rest of this document exists.

## 3. Does it work? Yes. Here is the actual output

Run against both businesses on 3 October:

**Keystone Fabrication**

```
8 new tickets   ->  8 read, 5 replies drafted, 3 sent to a human
SLA: can be measured. 18 open tickets are breaching.
     The platform's own flag agrees with us on all 150 tickets.
```

**Suryodaya Textiles**

```
21 new tickets  ->  21 read, 0 replies drafted, 21 sent to a human
SLA: CANNOT be measured here, and the agent says so.
     Only 5 of 105 tickets record when they were first answered.
```

Those two answers look very different, and both are correct.

**Why Suryodaya drafts nothing.** Almost none of its help articles are actually
published and public — only 10 out of 102. The answers exist; nobody has released
them. So the agent cannot answer a single one of the 21 tickets without sending a
customer something unpublished. It refuses, and explains why. That zero is a
finding about the business, not a broken agent.

**Why Suryodaya will not give an SLA number.** To know "did we reply in time" you
need to know *when* you replied. Suryodaya records that on 5 tickets out of 105.
There is nothing to measure against. The agent reports a recomputed figure of 77
but **labels it a recomputation, not a measurement**, and points out that the
platform's stored flag disagrees with us on 25 tickets.

An agent that confidently said "77 tickets will breach" would be inventing a
number. One of our checks fails it for exactly that.

## 4. What we have, in numbers

```
21 tasks (25 runs, because some run on both businesses)
18 checkers
21 hand-written unit tests, written by the team
```

One of those 21 tasks was written by someone who had **not** read our agent's
code, and it is the most useful task we have. See section 5a.

| Test | What it proves | Result |
|---|---|---|
| Do-nothing agent | a checker never passes an agent that did nothing | fails all 21 |
| Checker self-test | checkers say yes to right answers, no to wrong ones, and catch cheats | 60 / 60 |
| Hand-written unit tests | the small pieces behave as decided | 21 / 21 |
| Fixed script (no AI) | the whole pipeline works end to end | 19 of 23 |
| AI model (Gemini) | an AI can drive it | **23 of 23** |

Two of the 25 runs could not be judged at all, which is a result in its own
right: the thing they were testing had been **fixed on the platform**, so the
checker said *"premise gone"* instead of passing or failing. A run that cannot be
judged never counts as a pass. That is why the totals above are out of 23.

**Four tasks separate the two versions**, and the AI wins all four: the
paraphrased question, the over-refusal, the wrong article that looks right, and
the one written by someone outside the team. The fixed script fails exactly
those four and nothing else.

The two the fixed script fails are the two that need real understanding — it is
*supposed* to fail those.

The one the AI fails, it fails **5 times out of 5**: it does not flag
badly-rated public articles for review, where the fixed script does. That is a
real weakness, measured rather than guessed — and getting to that sentence took
three attempts, which is the more useful story:

- The first five runs came back **0/5 and all five marked "degraded"**, meaning
  by our own rules they were not evidence at all.
- The cause was ours. The model had written `{"tool": ..., "query": ...}`
  instead of wrapping the argument in `"args"`, and our health check counted
  **any** tool error as *our plumbing failing*. A malformed call is the model's
  behaviour — it is exactly what we are trying to measure.
- That check was added to stop a network timeout being misread as a model
  failure. It had quietly grown into the opposite problem: **an axis meant to
  protect a measurement was deleting it.**

Tool errors are now split by whose fault they are. Transport failures, timeouts
and quota are ours and still mark a run unusable. A malformed call, a missing
argument or an unknown tool is the policy's, and counts as behaviour. The
classifier is deliberately cautious: anything not clearly the policy's mistake
is still treated as ours, so a real failure can never hide inside a result.

**One run of a model is a sample, not a measurement.** It is why the harness
takes `--repeat`, why every claim in section 7 is written as *n*/3, and why
nobody should quote a number from here that came from a single run.

### The numbers that matter, measured three times each

A single run of a model is a sample, not a measurement — this week four tasks
flipped between runs and each time a single run nearly became a claim. So the
six tasks that have ever been unstable were run **three times per arm**:

```
task                              fixed script    AI
d01  paraphrase lead time             0/3        3/3    <- separates
d02  over-refusal                     0/3        3/3    <- separates
d03  part number is not an answer     0/3        3/3    <- separates
i01  SLA not computable               3/3        3/3
i05  stale article not sent           3/3        3/3
q01  the whole job, Keystone          3/3        3/3
q01  the whole job, Suryodaya         3/3        3/3
```

No flapping anywhere. The three that separate the arms do so completely, and
they are exactly the three that need judgement rather than procedure. The AI
passes all seven instances; the fixed script fails precisely where it should.

This is the only table in this document whose numbers were taken more than once,
and it is the only one we would defend.

## 5. The task that checks the whole job

Most tasks check one slice. **One task uses the exact words our seat was given**
and checks the whole thing. It asks four questions:

| Check | The mistake it catches |
|---|---|
| Does the arithmetic add up? `done + skipped = total` | Agent does 3 of 21 and reports "3 tickets" — technically true, useless |
| If you skipped some, did you say so? | Quietly doing a subset |
| Does every ticket's type and priority match the database *right now*? | Making up details |
| Does every reply cite an article that is genuinely publishable? | Sending a customer a draft or an internal note |

And one more, added today. Every drafted reply ends with a line like:

```
Source: Certificates of conformance - rated 54 helpful / 4 not helpful;
rating provenance is not recorded by the platform.
```

The checker **rebuilds that line from the database** and refuses the run if it
does not match. Before this, the line was honest only because our code happened
to write it honestly. Now it is honest because it is checked. We added a fake case
to the self-test — a reply claiming "rated 999 helpful" — and confirmed it gets
caught.

## 5a. The task we did not write, and what it found

Every other task in this suite is phrased in the words our own code looks for,
because we wrote both sides. A team member who had never seen the code
suggested this one:

> *"A few of the new requests mention customers having trouble with a feature.
> Please check the available help articles and draft the first reply for each
> one. If the information we have doesn't actually explain how to fix the
> problem, just tell me that rather than guessing."*

**On its first run, both versions handled ONE ticket and stopped.**

The cause was ours, not the AI's. The loop decided whether a request was about
many tickets by matching a list of phrases we had written — "new tickets", "the
tickets", "queue", "each ticket". This person wrote **"new requests"** and
**"each one"**, which mean exactly the same thing in English and matched
nothing. So the loop hid the queue tools, and the AI could not walk the queue
even in principle.

Same prompt, same model, only our filter moved:

```
                   filter ON     filter OFF
tickets walked         –             8
replies drafted        0             4
```

Given the tools it did the whole job: walked the queue, drafted for every
answerable ticket, escalated the one with no usable article. **It understood the
request perfectly. We had taken the capability away and then read the result as
a model failure.**

The filter is now off. Three measurements justify that, each moving one thing:

```
d02 over-refusal     the filter once HELPED   0/3 -> 3/3   (now 3/3 either way)
i05 stale article    the filter HURT          3/3 -> 0/3   (now 3/3 either way)
this task            the filter HURT          4 drafts -> 0
```

The task it was originally protecting has since been fixed by other means, so
removing it costs nothing and fixes ordinary English.

**The task is now permanent** (`h01`), in their wording, unchanged. Its failure
message is written for whoever hits it next: *"the most likely cause is ours,
not the model's — check whether the queue tools were offered for this
phrasing."*

If you read one thing in this document and act on it, make it this: **one
paragraph from one outsider found what twenty of our own tasks could not.**

## 6. What the harness has actually caught

Not theory. Everything here was found by running it.

### In our own code — seven bugs a demo would have hidden

- The agent would have **sent a customer the wrong article** when the right ones
  were locked, because keyword matching grabbed whatever was available.
- A **correct answer was thrown away** by our own result-assembly code. The AI was
  briefly blamed for it.
- A **network timeout was reported as the AI failing.**
- A **snapshot was taken too late**, so a change that happened during the run was
  already baked into the "before" picture.
- Every drafted reply would have told the customer **"rated 54.0 helpful"** —
  the platform returns the vote counts as decimals.
- **A pattern in our code contained invisible control characters** instead of what
  we meant to type, from a shell quoting slip. It silently broke the routing, so
  *"Triage the oldest ticket"* was sent down the whole-queue path and an unrelated
  task started failing **on both businesses**. The task we were working on still
  passed, so we would never have seen it by testing that task alone.
- The AI asked *"can I use support?"* — which is an app name, not a data table. It
  was told "no such thing", read that as *access denied*, and refused a job it
  could do. The platform uses one word for both, so the question was fair. We now
  answer "that is an app, and you are inside it." That task went **0/3 to 3/3**.

### In the harness itself — four

- A **lucky pass**: the AI refused for the wrong reason (a typo) and the checker
  approved it anyway. The checker is stricter now.
- A **fragile test**: one check was triggered by counting database reads, which
  measured each agent's reading habits rather than its behaviour, and made the AI
  look broken when it was fine.
- **The experiment did not reset between runs.** One configuration set an
  environment variable and never cleared it, so every later configuration
  inherited it and the comparison reported "these two are identical" — which was
  true, because both runs *were* the same configuration. It was invisible whenever
  that configuration happened to run last, which is how it survived two earlier
  comparisons. **An experiment that does not reset between runs is not an
  experiment.**

- **Our own API quota ran out and the harness blamed the agent.** Six runs
  crashed because the AI provider returned "quota exceeded". All six were scored
  as the agent getting the answer wrong, with the health column reading **"ok"**.
  The comparison then reported "these two configurations behave identically" -
  when in truth **neither of them had run at all**. A failure on our side is now
  marked unusable and is never graded. This is the same mistake as the timeout
  bug above, from a different cause, so the rule is now written about the class:
  **if the thing that broke was ours, the run is not evidence about the agent.**

### On the platform — two

- `KBArticle.tags` is declared as text but comes back as a list — `findings/002`.
- `findings/001` was **fixed at the root** on 3 October. We did not notice by
  looking; a task reported *"premise gone: sales entities are no longer
  readable."* That finding changed state four times in three weeks.

## 7. The most important thing we learned

**Three times now, something we assumed was the AI's judgement turned out to be
our loop's responsibility.**

1. **Checking permissions before starting.** We expected the AI to remember. It
   didn't. The loop does it now, every run.
2. **Re-reading a ticket before filing a conclusion.** Same. The loop does it.
3. **Finishing the job.** Measured today: given 8 tickets, the AI capped itself at
   5, correctly spotted that 4 had a usable article, wrote **one** reply, and
   announced it was done — at step 5 of a 20-step budget. It did not run out of
   room. It did this identically **3 times out of 3**.

   The loop now refuses to accept "done" while tickets the agent's *own* triage
   marked answerable have no reply. One thing changed, measured:

   ```
   loop does not hold it to finishing    0 / 3
   loop holds it to finishing            3 / 3
   ```

   **And then the same guard failed, in a way worth more than the first result.**
   On a later run it fired six times, the AI wrote two more replies, and then
   got stuck: it reached for the wrong tool, spent thirteen steps going nowhere,
   and still finished two replies short.

   The guard was telling it *which* tickets were outstanding but **not which
   article to use** — even though the agent's own triage had already chosen one
   for each. We were demanding work while withholding the information needed to
   do it. The guard now hands back the exact call to make:

   ```
   not done: 2 ticket(s) your own triage marked draftable still have no reply.
   Call write_reply once for each, with the article your own triage already chose:
     write_reply(ticket='TKT-2026-00108', article_id='125b2b4d', body=<your text>)
     write_reply(ticket='TKT-2026-00148', article_id='891579f5', body=<your text>)
   ```

   That took it from **0/1 to 3/3**. The lesson is not "models are forgetful" —
   it is that **a demand without the means to satisfy it is a trap**, and the
   loop had the means all along.

### And a related one, found today

We added two new tools for the queue job. On a task that needs **neither** of
them, simply having them in the list made things worse:

```
two extra tools in the list      over-refusal task  0 / 3
only the relevant tools listed   over-refusal task  3 / 3
```

(The first time we ran this the paraphrase task looked affected too, at 2/3
against 3/3. Re-run properly, it is 3/3 either way. One task moved, not two -
and the difference between those two claims is the difference between a finding
and an overstatement.)

A model reads a long tool list as a hint about what the job is. This is the
**second** time this has bitten us — the first was a permissions tool, whose
presence alone pushed the AI toward refusing.

**We then wrote down a rule, and the rule was wrong.** The rule said: offer a
model the tools the request could use, not every tool that exists. One more
measurement, run back to back on a different task, says it is a trade-off:

```
                         all tools offered    only relevant tools
over-refusal task              0 / 3                3 / 3
stale-article task             3 / 3                0 / 3
```

Filtering the tool list **fixed** over-refusal on one task and **caused** it on
another. Net effect across the suite: zero. One task gained, one lost, and we
have no mechanism that explains both directions.

So the filtering stays — it is neutral, not an improvement — and it is recorded
here as an **open question, not a finding**. Three runs each is not enough to
build a rule on, and the first version of this section proves the point: it
generalised a single measurement into advice, which is exactly the mistake this
document warns about two sections later.

The general lesson is the method, not the tool list: a capability added for good
reasons changed behaviour somewhere unrelated, and the only way to tell that
apart from the AI having a bad day was to **move exactly one thing and
re-measure** — then do it again on a second task before believing it.

### This happened four times in two days

Every safety mechanism we added distorted the thing it was protecting:

| We added | What it did instead |
|---|---|
| A permissions tool in the list | Made the AI refuse jobs it could do |
| A guard demanding unfinished work | Demanded it while withholding the article id needed to do it |
| A check marking runs unusable when our plumbing broke | Marked runs unusable when the **AI** made a mistake, deleting the measurement |
| A tool giving the AI the whole knowledge base | **Nothing at all — it never called it** |

That last row is the sharpest. The tool worked, was useful, and changed no
outcome, because using it was optional. Putting the same information into a
result the AI already receives took the task from **0/3 to 3/3** without the AI
having to decide anything.

Four times in two days, the rule held:

> **If a behaviour matters, the loop does it. Anything the model must remember
> to do, it will not do.**

That now covers checking permissions, re-reading a row before filing,
finishing a multi-item job, looking before refusing, and seeing the whole
knowledge base rather than a shortlist.

None was visible from the feature itself. Each showed up only by running the
whole suite and asking **why** a number was what it was, instead of accepting
it. That is a better argument for having a harness than any pass rate in it.

## 8. The honest caveat

**Most of our tasks cannot tell a real AI apart from a fixed script.**

That is on purpose, not a flaw. Permission checks, re-reading, the article
filters and the refusal reasons all live in the **loop**, not in the AI — because
whether an agent re-reads or stops should not depend on a model remembering to.
So both versions inherit all of it, and both pass.

Only a couple of tasks reach the AI's actual judgement.

**So when you see a pass rate, ask which kind of task it came from.** A task both
versions pass tells you *the task is not discriminating* — not that both agents
are good.

**One more caveat.** Our model, `gemini-3.1-flash-lite-preview`, is a **preview**
build. The provider can change it without telling us, and we have already watched
one task flip between runs under the same model name. Both results are recorded.
**Pin a stable model before any score is submitted.**

## 9. What is pending

### A. Decisions we still need from the team

| # | Question | What it blocks |
|---|---|---|
| **9** | **May the agent write to shared tickets?** | **The biggest one.** The agent writes replies but cannot send them. Half the team's flow waits on this |
| 3 | Should triage judge, or only report — and on what thresholds? | Whether triage adds anything beyond copying fields |
| 7 | Should the agent create help articles from solved tickets? | The article-hygiene task |
| — | May the agent write `AgentEscalation`? | Small. It is our own workspace, and escalations currently go nowhere a human looks |
| — | **New:** should an article with 10 votes split 5/5 be blocked? | Today it is not — the rule blocks *below* half. A hand-written test asked the question and nobody has decided |

### B. Work that needs no decision, listed in the order it matters

1. **Tasks written by someone who has not read our agent's code.** Every task so
   far is ours, and we fixed our own tools after watching them fail — so our
   numbers are partly self-graded. This is the single most valuable thing anyone
   can contribute and it needs no decision at all.
2. **Pin a stable model.** We are on a preview build that the provider can change
   without telling us, and we have already watched a task flip under the same
   model name. No score should be submitted on a preview model.
3. **A correction pass on `GAP_REPORT.md`.** Roughly eight figures in it are now
   stale — the tool count changed, `findings/001` was fixed, and some claims were
   re-derived and turned out weaker than written.
4. **Findings we have measured but not written up:** 52 of 102 article addresses
   contain a `/` that the form cannot produce; two customer records are published
   publicly; `KBArticle.tags` returns a list although declared as text.

### C. Answered and built on 3 October

- Which tickets a run covers: **new only**.
- What a drafted reply contains: **a full reply plus a citation line**, which the
  checker now rebuilds from the database.
- The article quality rule, the queue walk, the finish guard, and the whole-job
  task.
- **One to-do per escalated ticket** (the team chose per-ticket over per-run).
  Two safeguards came with it, and they are not optional — see the next section
  for why.

**On the cap question we did not need a number.** A cap is the agent's own
choice, and the task simply makes it honest: an agent that works 5 of 21 and
*says* 5 of 21 passes. One that works 5 and reports a queue of 5 fails.

## 10. The to-dos, and what we learned filing them

The team chose **one to-do per escalated ticket**. Building it turned up three
things about the platform that shaped how it had to be built.

| What we found | Why it mattered |
|---|---|
| `AgentTodo` has **no field that can point at a ticket** | "A to-do for ticket X" can only say so in its title text. A human cannot click through |
| To-dos **cannot be deleted**, only cancelled | Every row we create is permanent |
| The book is **shared** — the only other rows in it are another team's probes | Whatever we file, other teams see |

Those three together mean a re-run that files 21 duplicate rows would be a
permanent mess in someone else's view. So two safeguards ship with the feature:

- **Dedupe.** Before filing, read the existing to-dos and skip any ticket that
  already has one that nobody has finished with. Proven on a fixture: three runs
  in a row file **three rows total**, not nine.
- **A cap**, always reported, never silent.

**And a checker, built the same day.** The task runs against a fixture that seeds
three deliberate cases: a ticket whose to-do is still open, one whose to-do a
human already cancelled, and one whose to-do has **no status at all**. A correct
agent skips the first two and re-files the third, because cancelled means a human
is finished with it. The checker then reads the book and requires the one thing
that actually matters:

> every escalated ticket ends with **exactly one** to-do nobody has finished with

That holds across runs, which is the point — it is the check that catches an
agent re-filing the same work every morning. It also refuses a run that files a
to-do for a ticket the agent answered itself, because that asks a human to redo
finished work. Seven self-test cases confirm it approves the right answer and
rejects each wrong one, including two open to-dos on the same ticket.

The fixture is used rather than the live books on purpose: the case worth testing
is "this ticket already has a to-do", and creating that live would leave
permanent rows in a book other teams read.

And one bug the fixture caught, which is worth repeating because of which way it
failed. The first version of the dedupe asked *"is this to-do's status open or
in-progress?"* A row created without an explicit status comes back with **no
status at all**, which is neither — so a re-run filed a duplicate for every
ticket. The test is now written the other way round: **skip only what is
explicitly finished.** An unknown status counts as still open, so the worst case
is a to-do we did not file, never a permanent duplicate we cannot remove.

There is also a smaller mismatch worth knowing: a ticket's priority can be
`medium`, and `AgentTodo` only accepts `low`, `normal`, `high`, `urgent`. Copying
a ticket's priority straight across is rejected by the platform on most tickets.
We map it; we found this by reading the create schema before writing anything.

## 11. The one thing anyone can help with, today

**Write a task without reading our agent's code.**

Right now every task was written by us, and we fixed our own tools after watching
them fail. That makes our numbers **in-sample** — we partly graded our own
homework. A task written by someone who has not read `seat15/agent/` is worth
more than any number in this document, and it needs no decision from anyone.

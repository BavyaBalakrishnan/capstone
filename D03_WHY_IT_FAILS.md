# Why d03 fails, and what a real fix has to do

`d03_part_number_is_not_an_answer` is the one task that fails on both
instances and in every graded round. Six fixes have been tried and reverted.
This is the analysis that should have been written before attempt two.

The short version: **we have been fixing the wrong thing in the wrong place.**
Three separate defects have to be fixed together, and five of the six attempts
addressed none of them.

---

## The task

A customer writes:

> My FG-CAB-3300 Cab Step Frame shipment for lot 4474 arrived 48 pieces short
> of the ASN. I want the packed count confirmed and the balance shipped.

Keystone has 25 sendable articles. None is about a short shipment. Two are
about that product: *"Cab step frame — damaged crate claims"* and
*"FG-CAB-3300 cab step frame — powder coat care and touch-up"*.

The agent cites one of them. The customer asking where 48 missing parts are is
told how to photograph crate damage, or how to touch up paint.

The correct answer is that nobody has written this article, and a person needs
to handle it.

---

## Defect 1: three paths to a reply, and only one of them checks

Read from the trace of a failing run (`runs/20261022-064400-aboff3`):

```
DECIDE  tool=draft_reply  args={"query": "FG-CAB-3300 Cab Step Frame short 48
                                  pieces lot 4474", "ticket": null}
  TOOL  draft_reply  -> drafted: true
DECIDE  done  outcome=answered
```

There are three ways a reply gets grounded, and they do not agree:

| path | who picks the article | coverage check |
|---|---|---|
| `kb_candidates` | the model, from a list | none, but it sees `matched` / `missed` |
| `draft_reply` | **our code**, `usable[0]` | **none at all** |
| `write_reply` | the model, by id | `not_on_topic` — but only `if t is not None` |

The agent took `draft_reply`. Our own code picked the article and reported
`drafted: true, sendable: true`, and the model was never asked to look at the
choice.

This is the i04 hole, reopened a third time. `write_reply`'s own comment says
it: *"This hole was already closed once, in kb_candidates ... This function was
added later for the queue walk and reopened it through a different door."* We
wrote that, and then added a third door.

**Everything we added for d03 — `missed`, `nothing_covers_request`, the ranked
`choices` row — lives in the `kb_candidates` payload.** The failing path never
shows the model that payload. The paired A/B that measured "no effect" was
measuring a field the model could not see. The flag was not useless; it was
invisible.

## Defect 2: the coverage check is inverted

`write_reply`'s check rejects an article only when it shares **no** topic word
with the ticket. Tested offline against the titles we know are right and wrong:

| task | article | shares | should | check says |
|---|---|---|---|---|
| d01 | *What lead time can I expect?* | nothing | ACCEPT | **REJECT** |
| d02 | *What lead time can I expect?* | nothing | ACCEPT | **REJECT** |
| d03 | *Cab step frame — damaged crate claims* | `step`, `frame` | REJECT | **ACCEPT** |

Wrong in all three. The d03 row is certain, because `step` and `frame` are in
the title. The d01/d02 rows are title-only evidence: the real check also reads
tags, excerpt and content, which this analysis could not fetch, so treat them
as a flag to verify rather than a proven fault.

If they hold, there is a live bug independent of d03: a correct paraphrase
answer would be rejected as `not_on_topic` whenever it arrives through
`write_reply` with a ticket attached. d01 and d02 pass today only because they
take a path where the check does not run.

## Defect 3: lexical overlap cannot express the distinction

The signal is wrong at both ends, which is why no threshold works.

- **It misses the right answer.** d01 asks "how long before my stuff turns up?"
  and the correct article is *"What lead time can I expect?"*. Zero shared
  words. Lexically, the top candidate is *"Mounting a bench vice so it stops
  moving"*, matched on `take` — and `turn` matches *"re**turn**s"*, `place`
  matches *"**place**d"*. The matcher does substring, not word, comparison.
- **It picks the wrong answer.** d03's two candidates tie on `step` and
  `frame`, the product's name, and neither mentions short, count, pieces,
  shipment, arrived or packed.

**Correction, 2026-10-27.** Calling this a "product-name match" was too
narrow. Across graded rounds the agent has cited **four different** articles:
*Blanket orders and release schedules*, *Cab step frame - damaged crate
claims*, *FG-CAB-3300 cab step frame - powder coat care*, and *Certificates of
conformance*. The last shares no product word at all. So the selection is not
a consistent bias toward the product's name - it is closer to noise among weak
matches, which is a stronger version of the same conclusion: the lexical score
carries so little signal that which wrong article wins is close to arbitrary.

That also exposed a defect in our own verifier, now fixed. Its failure message
ended with a fixed clause - "that one matches on the part number and explains
powder coat touch-up" - appended whatever had been cited. When the graded run
cited *Certificates of conformance*, we told the evaluator it matched on the
part number and explained powder coat touch-up. Both false. The verdict was
right and the explanation was invented, which is the exact failure this
harness exists to catch, committed by the harness. The message is now derived
from the cited row: what it matches, and which short-shipment phrases it never
mentions.

The measurement that settles it: d03's wrong answer covers **14%** of the
request's terms and d01/d02's *right* answers cover **11%**. No threshold lies
between them. That is attempt (4) in the task file and it is why attempts (1)
and (2) were refuted too.

Semantic similarity does separate them, and the discriminator is the **margin**
between the top two matches rather than the score — because d03's top score is
as high as d01's:

| task | top1 | top2 | margin | covered |
|---|---|---|---|---|
| d01 | 0.757 | 0.640 | **+0.117** | yes, and it ranks the RIGHT article first |
| d02 | 0.701 | 0.594 | **+0.106** | yes, same right article |
| i05 | 0.803 | 0.667 | **+0.136** | yes, then blocked on rating |
| i04 | 0.625 | 0.577 | **+0.049** | no |
| d03 | 0.716 | 0.707 | **+0.009** | no |

When one article genuinely answers, it stands clear of the field. When none
does, the top candidates cluster around the product and no single one is the
answer. `tools/semantic_probe.py` reproduces this; it is read-only.

A second, independent signal agrees. Asked one focused question per candidate —
*"A customer wrote this. Here is an article. Does it answer what they actually
asked? YES or NO"* — the model said **NO** to both of d03's articles. It also
said NO to d01's and d02's lexical candidates, which were junk. The judge is
accurate about whatever it is shown; the failure there is retrieval, not
judgement.

---

## What a real fix has to do

In this order. Each step is useless without the one before it.

**1. One coverage decision, in one place, on every path.** While
`draft_reply`, `write_reply` and `kb_candidates` each decide differently,
fixing one leaves the others open — which is what happened three times. The
decision belongs in `kb_candidates`, and the other two must consume it rather
than re-derive it.

**2. Scope the question to a customer's words.** `nothing_covers_request` fired
on 9 of 17 task-instances because "triage the new tickets and tell me which
breach SLA" matches no article. Asking "does an article cover this" about an
operator's instruction is meaningless. Only ask it of a ticket's
subject-and-description or a direct customer question.

**3. Make the decision semantic, by margin, not lexical by threshold.** Step 3
is the only part that can actually tell "same product" from "same problem".
Keep lexical as the fallback: the provider returned 503 on a third of our calls
one afternoon this month.

**4. Add the focused judge as a second gate on the top candidate.** One call,
one question. Measured correct on d03's two articles.

**5. Then measure with the two-arm grid, across every task.** The question is
never "does it fix d03" — it is "which tasks separate the arms". Five data
points are not a measurement, and the thresholds above are fitted to five.

## What not to do

- **Do not require shared problem words.** That is attempt (1), refuted by
  d01 and d02, and it is also what the evaluator suggested in round 3.
- **Do not soften the prompt.** Tuning a task against the agent is how a suite
  stops measuring anything. The prompt has never been changed.
- **Do not trust a streak.** Attempt six gave 3 of 3 and looked like a fix. A
  paired A/B gave 5 of 6 with it and 5 of 6 without. Only the control arm
  showed it, and we now know the flag was invisible on the failing path anyway.
- **Do not report our pass rate as a defence.** d03 passes about 70% of the
  time on our model over 17 samples, and has failed every graded round on the
  platform's. Our number does not predict theirs.

## Why it is worth doing at all

Not for d03. It is one task.

d01 and d02 pass today only because a capable model rescues a ranking that put
*"Mounting a bench vice"* first. That is precisely the model-diligence
dependency the graded run of 21 October punished twice, in h01 and q01, where
the platform's weaker model did not rescue us. d03 is the symptom. The
fragility is the disease, and it is sitting under two tasks that currently pass.

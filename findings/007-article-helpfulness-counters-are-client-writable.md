# 007 — Article helpfulness counters are client-writable, and nothing records the votes behind them

**Seat:** 15 (Helpdesk) · team15@theschoolofai.in
**Instances:** BOTH. The schema is identical on Suryodaya and Keystone.
**Door:** MCP `tools/list` — the input schemas of `KBArticle.create` and `KBArticle.update`.
**Severity:** the only quality signal available to an answering agent cannot be
trusted, and there is no record that would let anyone audit it.
**Status:** written up. **Read-only: the write was NOT attempted — see Notes.**
**Reproduces:** every `tools/list`. Measured 2026-09-24.

## What I did

Read the closed input schemas of the two write tools this seat holds for
`KBArticle`, and swept all 428 entity schemas for any record of an individual
article rating.

## What I expected

`helpful_count` and `not_helpful_count` to be server-derived from reader
feedback, and therefore absent from a caller-supplied input schema — the way a
computed total normally is. I expected to find a feedback record behind them.

## What happened

### (1) The counters are in the writable schema

```
KBArticle.create   required: ['title', 'content']
                   accepts : ..., helpful_count, not_helpful_count, views_count, ...
                   additionalProperties: False

KBArticle.update   required: ['id']
                   accepts : ..., helpful_count, not_helpful_count, views_count, ...
                   additionalProperties: False
```

`additionalProperties: False` matters here: per section 6 of the brief the schema
is closed and "an argument that is not in it is rejected rather than ignored". So
these three fields are not incidental — they are deliberately part of what a
caller may supply.

### (2) Nothing records the votes behind them

Swept all 428 entity schemas. **No entity records an individual rating of a
`KBArticle`.** Only four entities link to `KBArticle` at all, and none of them is
feedback:

```
Ticket.kb_article_id   (and the three TicketReply* ledgers, via ticket_id)
```

`KBAnswerFeedback` exists and is well modelled — `rating`, `comment`,
`source_ids_json`, `source_evidence_hashes`, `idempotency_key` — but it belongs
to the `knowledgebase` app (403 from this seat), and it rates an **agent's
answer**, keyed by `answer_hash`. It is not article feedback.

So the counters cannot be reconciled against anything. There is no way to see who
voted, when, whether the votes predate the article's last edit, or whether the
same actor voted repeatedly.

### (3) The values do not behave like collected feedback

On Suryodaya the median article body is **20 words**, and 74 of 101 are under 30
words, yet they carry substantial vote counts — one 20-word article holds 184
helpful. Three days earlier the neighbouring `related_articles` field held values
on 58 of 100 articles and today holds `None` on all 101, so bulk writes to this
table demonstrably happen.

Two neighbouring fields on the same entity already hold values of the wrong kind,
which is why a written counter is the likelier explanation than collected votes:

- `slug` holds part codes on 52 of 101 rows — `DC5235/3738`, `MS4710/3736` — and
  a `/` cannot appear in a URL slug at all.
- `source_ticket_id` is set on 74 rows but points at only **9 distinct tickets**
  (one ticket is the declared source of 14 different articles), and only 9 of the
  74 share even one word with the subject of the ticket they point at.

Keystone shows none of these three patterns: 0 malformed slugs, 2 source-ticket
links, and article bodies with a median of 31 words.

## Why this matters for this seat

Seat 15's request includes *"draft a first response from the knowledge base"*.
An agent choosing which article to send has exactly one quality signal, and it is
these two integers. Our own agent uses them to decide whether an article is safe
to send, and to refuse the worst ones — on Suryodaya, two published, public
articles rated 31/59 and 0/51.

If the counters are client-writable and unlogged, then:

- a "well rated" article may never have been rated by anyone;
- an article can be made to look good or bad by any caller with write access,
  including another team's agent on the same shared book;
- no one can audit the decision afterwards, because the evidence does not exist.

This is the same shape as `findings/005`, where `reopen_count` held values the
state machine cannot produce. A counter that is directly writable can hold
anything, and on this platform it does.

## Suggested fix, in order of preference

1. **Remove `helpful_count`, `not_helpful_count` and `views_count` from the
   `create` and `update` input schemas.** They should be server-maintained.
2. **Add a feedback record for articles**, along the lines of the
   `KBAnswerFeedback` the platform already models: article id, rating, actor,
   timestamp, idempotency key. Then the counters become a derivable total rather
   than a claim.
3. If they must stay writable for seeding, restrict them to an admin role and
   record who set them — the same treatment `endpoint.job_ledger.*` already gives
   other sensitive operations.

## Notes and limits

- **The write was not attempted.** Confirming that the server persists a supplied
  value would mean writing to a book three other teams share, and specifically
  corrupting the quality signal they may be relying on. The verified claim is
  narrower and is stated as such: **the closed input schema accepts these fields.**
  Whether the server stores what is supplied is untested.
- A platform admin or EA can confirm the server-side behaviour without anyone
  writing to a live book. Section 3 of the brief makes that escalation part of the
  exercise.
- Read-only throughout: `tools/list` and `GET /api/schemas` only. Nothing was
  written to either book.

## IDS

```
page       : n/a — MCP door, tools/list (KBArticle.create / KBArticle.update)
agent_seat : Helpdesk
instances  : both agentswitch.theschoolofai.in and class.agentswitch.theschoolofai.in
measured   : 2026-09-24
```

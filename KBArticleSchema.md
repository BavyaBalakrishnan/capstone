# KB article — schema and API reference

**Seat 15 (Helpdesk) · Suryodaya and Keystone · measured read-only 2026-09-25**

Everything here was read from the live platform — `GET /api/schemas`, MCP
`tools/list` input schemas, and sample rows — not from documentation. Row counts
move; the shapes do not.

---

## 1. The two entities

The knowledge base our seat owns is two entities in the `support` app:
**`KBArticle`** and **`KBFolder`**. They are separate things — an article may sit
in a folder, and a folder is only a container.

> There is a **second, unrelated knowledge system** on this platform in the
> `knowledgebase` app — `KBVault`, `KBNote`, `KBNoteType`, `KBTag`,
> `KBAgentGuide`, `KBSearchRun`, `KBAnswerFeedback`. It is far richer (freshness
> dates, backlinks, an answer ledger, per-agent guides) and our seat is refused on
> all of it: *"App 'knowledgebase' is not enabled for your account"*. Do not
> confuse the two. `KBArticle` is ours; `KBNote` is team 22's.

### KBArticle — 18 schema fields

| field | type | required | notes |
|---|---|---|---|
| `title` | text | **yes** | |
| `content` | richtext | **yes** | |
| `slug` | text | no | URL-friendly id, generated from the title if left blank |
| `folder_id` | link → KBFolder | no | |
| `category` | text | no | free text, **not** a picklist |
| `excerpt` | text | no | short summary; searched |
| `status` | select | no | `draft` · `in_review` · `published` · `archived` |
| `visibility` | select | no | `public` · `internal` · `agents_only` |
| `tags` | text | no | declared text; **often arrives as a list** — see §7 |
| `source_ticket_id` | link → Ticket | no | the UI labels this **"Customer Complaint"** |
| `author` | text | no | free text, not a link to a user |
| `views_count` | number | no | **client-writable** — see §7 |
| `helpful_count` | number | no | **client-writable** — see §7 |
| `not_helpful_count` | number | no | **client-writable** — see §7 |
| `seo_title` | text | no | |
| `seo_description` | text | no | |
| `related_articles` | text | no | `None` on every row today |
| `company_id` | link → Company | no | |

### KBFolder — 7 schema fields

| field | type | required | notes |
|---|---|---|---|
| `name` | text | **yes** | |
| `description` | text | no | |
| `icon` | text | no | |
| `parent_id` | link → KBFolder | no | folders nest |
| `visibility` | select | no | `public` · `internal` · `agents_only` |
| `sort_order` | number | no | |
| `company_id` | link → Company | no | |

---

## 2. Status and visibility are independent — this is the one to remember

They are two separate fields answering two different questions:

- **`status`** — how finished is it? `draft` → `in_review` → `published` → `archived`
- **`visibility`** — who may read it? `public` (customers), `internal` (staff),
  `agents_only` (the answering agent; not a document people browse)

**An article may be sent to a customer only when it is `published` AND `public`.**

```
Suryodaya   102 articles   ->   10 sendable
Keystone     34 articles   ->   25 sendable
```

On Suryodaya, 24 articles are `published` but `internal` — genuinely finished
content that must never be sent.

**Folder visibility does not affect this.** Verified 2026-09-25: two `public`
articles sit in an `internal` folder and the platform still offers them as
citable to a customer. The article's own visibility is what counts, every time.

---

## 3. What our seat may do

```
KBArticle    support_user: read, create, write      -> NO delete
KBFolder     support_user: read                     -> NO create, write or delete
```

The MCP catalogue mirrors this exactly:

```
KBArticle.list   KBArticle.get   KBArticle.create   KBArticle.update
KBFolder.list    KBFolder.get
```

**Consequences for anything we build:**

- An article we create **cannot be removed through the API**. A human can delete
  it in the UI (trash icon on the article page).
- We **cannot create folders.** A new article must go into one of the folders
  that already exists — 100 on Suryodaya, 15 on Keystone.
- The UI offers a "New KBFolder" form anyway. Submitting it is refused with
  *"None of your roles ['support_user','user','agent_user','sales_viewer'] can
  'create' on KBFolder"*. Tested 2026-09-25; no row was created.

---

## 4. MCP tools

### `KBArticle.list` — no required arguments

Accepts **every schema field as an equality filter**, plus:

```
search        free text across the article
limit         page size
offset        page offset
sort_by       field name
sort_order    asc / desc
```

### `KBArticle.get` — requires `id`

### `KBArticle.create` — requires `title` and `content`

Accepts every other field, **including `source_ticket_id` and all three
counters**. `additionalProperties: False`, so an argument not in the schema is
rejected rather than ignored (brief §6).

### `KBArticle.update` — requires `id`, accepts the same fields

### `KBFolder.list` / `.get`

Filters on `name`, `parent_id`, `visibility`, `description`, `icon`, plus
`search`, `limit`, `offset`.

---

## 5. REST — what verifiers should use

```
GET /api/KBArticle?status=published&visibility=public&limit=200
GET /api/KBArticle?search=shortage
GET /api/KBArticle?folder_id=<id>
GET /api/KBFolder?parent_id=<id>
```

Envelope:

```json
{ "data": [ ... ], "total": 102, "limit": 200, "offset": 0 }
```

**Filters are applied server-side.** Confirmed 2026-09-25:
`status=published&visibility=public` returns `total=10`, and `search=shortage`
returns `total=15`. Do not pull every row and filter in Python — ask the server,
and read `total` rather than counting the page.

### Row shape

Each row carries the 18 schema fields plus `id`, `created_at`, `created_by`,
`updated_at`, `updated_by`, and five meta fields the API adds:

| meta field | meaning |
|---|---|
| `_display` | human label — equals `title` on all 102 rows |
| `_permissions` | per row, e.g. `{"write": true, "delete": false}` |
| `_can_create` | whether this seat may create |
| `_company_id_display` | resolved company name |
| `_source_ticket_id_display` | resolved ticket subject |

`_permissions` is worth using: an agent can check writability per row instead of
reasoning about roles.

---

## 6. The platform's own KB search, for comparison

`endpoint.helpdesk.assist_suggestions` — in our catalogue, read-only.

```
ticket_id           required
search              refine the ticket-derived query with extra text
only_customer_safe  boolean
audience            'customer_facing' (default) or 'internal_note'
limit               1-50, default 8
offset              0-10000
vault_id            restrict note suggestions to a knowledge vault
```

Its own description: *"Published knowledge-base entries the asking agent may
already read, matched against this ticket's own words, with the matched terms
returned. **No model is called.**"*

Behaviour observed in the UI:

- It matches on **title, content and excerpt** — and reports which. Never folder.
- It retrieves **published only**, and only what your role may read. It states the
  rest: *"Matching articles that are not published: 16. They are not suggested;
  publishing one is how it becomes usable here."*
- Non-public results are badged *"Internal — not for the customer"* and
  **"Cite as grounding" is disabled** for them. "Insert into reply" stays enabled.

Two things follow. **Folder name is a topic signal the platform ignores** and our
agent can use. And the platform blocks *citing* an internal article but not
*inserting* its text — our agent is stricter, and deliberately so.

---

## 7. Gotchas, all measured, all Suryodaya

Keystone shows none of 1–4, which is why the two books behave so differently.

1. **`tags` is a list on 57 of 102 rows**, a string on 27, null on the rest —
   despite being declared `text`. Normalise before use. This crashed our first
   verifier, the same way `findings/002` crashed 70 ticket pages.
2. **`slug` holds part codes on 52 of 102 rows** — `DC5235/3738`, `MS4710/3736`.
   They contain `/`, which cannot appear in a URL slug at all. Only 23 slugs
   actually match their title.
3. **`source_ticket_id` is set on 74 rows but points at only 9 distinct tickets.**
   One ticket is the declared source of 14 articles, and only 9 of the 74 share
   even one word with the ticket they point at. Treat it as noise, not provenance.
4. **`seo_title` names a different company than the title on 18 of 81 rows.**
5. **The three counters are client-writable** and no vote record exists anywhere
   (`findings/007`). Ratings are the only quality signal available and cannot be
   verified.
6. **Articles are short.** Median 20 words; 74 of 102 under 30 words. Even a
   sendable article is often a stub.
7. **Counts move.** 101 → 102 in a day. Never hardcode a total; recompute it.

---

## 8. Quick recipes

```python
# the only articles that may be sent to a customer
GET /api/KBArticle?status=published&visibility=public&limit=200

# everything on a topic, including the ones we cannot send
GET /api/KBArticle?search=shortage&limit=200

# is this article safe to quote?  -> check the ARTICLE, never the folder
row["status"] == "published" and row["visibility"] == "public"

# normalise a declared-text field before using it
tags = " ".join(v) if isinstance(v, list) else (v or "")
```

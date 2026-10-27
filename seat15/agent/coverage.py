"""Does any article actually answer this customer's question?

Off unless SEAT15_SEMANTIC_KB is set. Nothing imports this at module scope and
`kb_candidates` only reaches it behind that flag, so the default behaviour of
every path is byte-identical to the state verified at Suryodaya 16/16 and
Keystone 14/15.

WHY THIS EXISTS
===============

`kb_candidates` ranks by lexical overlap, and that signal is wrong at both
ends. Measured, see D03_WHY_IT_FAILS.md:

  * It misses the right answer. d01 asks "how long before my stuff turns up?"
    and the correct article is "What lead time can I expect?" - zero shared
    words. Lexically the top candidate is "Mounting a bench vice so it stops
    moving", matched on `take`, because the comparison is substring not word
    (`turn` matches "returns").
  * It picks a wrong answer. d03 asks about a shipment 48 pieces short, and
    four different articles have been cited across graded rounds, the last of
    which - "Certificates of conformance" - shares no product word at all.
    Which wrong article wins is close to arbitrary.

d03's wrong answer covers 14% of the request's terms; d01's and d02's RIGHT
answers cover 11%. No threshold lies between them, which is why six attempts
to fix d03 by thresholding this signal failed.

WHAT THIS DOES INSTEAD
======================

Two stages, each fixing the half the other cannot:

  1. Rank by embedding similarity, so the right article reaches the shortlist.
  2. Ask the model one focused question per shortlisted article: "a customer
     wrote this; here is an article; does it answer what they actually asked?"

Measured 2026-10-27, gemini-embedding-001 and gemini-3.5-flash-lite, 9 of 9
correct:

    d01   0.757  What lead time can I expect?         -> YES   (the right one)
          0.640  What are your payment terms?         -> NO
          0.606  How do I raise a quality complaint?  -> NO
    d02   0.701  What lead time can I expect?         -> YES   (same)
          0.594  What are your payment terms?         -> NO
          0.581  How do I raise a quality complaint?  -> NO
    d03   0.716  Reporting a dimensional concern      -> NO
          0.707  Cab step frame - damaged crate       -> NO
          0.638  What a released purchase order needs -> NO

No false negative on either correct answer, no false positive on any of d03's.

Note what this does NOT need: a similarity threshold. An earlier version
decided coverage from the MARGIN between the top two scores (d01 +0.117, d03
+0.009), which separates the five cases we had but is a cutoff fitted to five
points. The judge removes the need for one - retrieval only has to put the
right article in the top few, and a yes/no question about one article is the
kind a weak model answers reliably. That matters because d03 has failed every
graded round on the platform's model, and the h01 and q01 fixes transferred
precisely because they replaced "remember to notice" with one focused question.

WHAT IT COSTS
=============

One embedding batch per instance per run, cached for the process, plus one
model call per shortlisted article. A queue walk of 8 tickets at 3 candidates
each is 24 extra calls. That is real against a 30-minute budget, which is why
JUDGE_TOP is 3 and not 5, and why a failure anywhere falls back to lexical
rather than retrying.

EVERY failure path falls back. The provider returned 503 on a third of our
calls one afternoon this month and 171s latency on another. A coverage check
that cannot run must not become a refusal: it hands the question back to the
lexical ranking, which is what runs today.
"""
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request

EMBED_MODEL = os.environ.get("SEAT15_EMBED_MODEL") or "gemini-embedding-001"
EMBED_BATCH = 32

# How many of the semantically-ranked articles get a judge call. Three covers
# every case we have measured and bounds the cost at three calls a question.
JUDGE_TOP = int(os.environ.get("SEAT15_JUDGE_TOP") or 3)

# Timeouts are generous because the alternative is a fallback, not a retry.
EMBED_TIMEOUT = 90
JUDGE_TIMEOUT = 60

# The availability probe: short, because its whole job is to fail fast.
PROBE_TIMEOUT = 15

# Articles we will list in one comparison call rather than shortlist first.
# 25 (Keystone's sendable set) reads comfortably; 40 is the existing
# WHOLE_BOOK_LIMIT and the point past which the shortlist has to do its job.
CHOOSE_LIMIT = int(os.environ.get('SEAT15_CHOOSE_LIMIT') or 40)

JUDGE_PROMPT = (
    "A customer wrote this:%(nl)s%(nl)s%(question)s%(nl)s%(nl)s"
    "Here is a help article:%(nl)s%(nl)sTITLE: %(title)s%(nl)s"
    "SUMMARY: %(summary)s%(nl)s%(nl)s"
    "Does this article answer what the customer actually asked about? "
    "An article about the same product but a different problem does NOT "
    "answer it. Reply with one word, YES or NO.")

# Embeddings for an instance's articles, keyed by article id. Per process: the
# book moves between runs but not inside one, and a run embeds 25 articles.
_VECTORS = {}

# Failures per instance, not a boolean. One blip must not disable coverage for
# the whole process.
#
# The first version used a set and gave up permanently on the first failure,
# reasoning that a run should not spend its budget rediscovering that the
# provider is down. On 2026-10-27 that made the whole feature invisible:
# Suryodaya has 100 articles, so embedding is four batches, and a single burst
# 429 on any one of them disabled coverage for every task that followed. The
# A/B then reported the semantic path as "identical to lexical", which it was,
# because it never ran.
#
# This provider answers 8 of 8 one minute and 503s a third of its calls the
# next, so a transient failure is the common case and a standing outage is the
# rare one. Retry the batch, and only stop after GIVE_UP_AFTER failures.
_FAILURES = {}
GIVE_UP_AFTER = int(os.environ.get("SEAT15_COVERAGE_GIVE_UP") or 3)
RETRIES = 2
RETRY_PAUSE = 2.0
BATCH_PAUSE = 1.5


_PREFLIGHT = {}


def available():
    """Can this endpoint embed at all? One tiny call, once per process.

    Without this the discovery cost is unbounded. The graded run supplies its
    own OPENAI_BASE_URL and we cannot see whether it serves /embeddings; if it
    does not, the failure budget would spend 3 failures x 3 attempts x the
    90-second embed timeout - about thirteen minutes - finding that out, inside
    a 30-minute budget. The fallback to lexical is safe; the cost of reaching
    it was not.

    So: one two-word input with a short timeout and no retries. It answers in
    under a second when the endpoint works, and fails in PROBE_TIMEOUT when it
    does not.
    """
    if "ok" in _PREFLIGHT:
        return _PREFLIGHT["ok"]
    cfg = _llm()
    if cfg is None:
        _PREFLIGHT["ok"] = False
        return False
    base, key, _ = cfg
    try:
        data = _post(base + "/embeddings", key,
                     {"model": EMBED_MODEL, "input": ["probe"]},
                     PROBE_TIMEOUT, retries=0)
        _PREFLIGHT["ok"] = bool((data.get("data") or [{}])[0].get("embedding"))
    except Exception:
        _PREFLIGHT["ok"] = False
    return _PREFLIGHT["ok"]


def enabled():
    return bool(os.environ.get("SEAT15_SEMANTIC_KB")) and available()


def _llm():
    """Model settings: environment first, then `.env`.

    Environment first because a run exports them through pin_llm_config and a
    deployment injects them. `.env` second because without it this module is
    silently unusable outside a run - which is how the first wiring test of
    2026-10-27 "passed" by falling back to lexical on every task and looking
    identical to the baseline. The same order as Client.cred, for the same
    reason.
    """
    def pick(*names):
        for n in names:
            v = os.environ.get(n)
            if v:
                return v
        try:
            from seat15.harness.client import load_env
            env = load_env()
        except Exception:
            return None
        for n in names:
            v = env.get(n)
            if v:
                return v
        return None

    base = pick("SEAT15_LLM_BASE_URL", "OPENAI_BASE_URL")
    key = pick("SEAT15_LLM_API_KEY", "OPENAI_API_KEY")
    model = pick("SEAT15_LLM_MODEL", "OPENAI_MODEL")
    if not (base and key and model):
        return None
    return base.rstrip("/"), key, model


def _post(url, key, payload, timeout, retries=RETRIES):
    """One request, retried on failure. The provider's errors come in bursts."""
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            url, json.dumps(payload).encode("utf-8"),
            {"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except Exception as exc:
            last = exc
            if attempt < retries:
                time.sleep(RETRY_PAUSE * (attempt + 1))
    raise last


def _give_up(instance):
    return _FAILURES.get(instance, 0) >= GIVE_UP_AFTER


def _note_failure(instance):
    _FAILURES[instance] = _FAILURES.get(instance, 0) + 1


def _text(value):
    return "" if value is None else str(value)


def article_text(article):
    """What an article is about, for embedding. Title first: it carries the
    topic, and an excerpt can run to boilerplate."""
    return "%s. %s" % (_text(article.get("title")),
                       _text(article.get("excerpt"))[:400])


def _cache_path(instance):
    root = os.environ.get("SEAT15_CACHE_DIR") or ".cache"
    return os.path.join(root, "embeddings-%s.json" % instance)


def _load_cache(instance):
    """Vectors from a previous run, for articles whose text has not changed.

    Embedding the same book on every run is the whole cost of this feature and
    almost all of it is waste: Suryodaya's 100 articles are four batches, and
    four batches back-to-back is what trips the provider's burst limit - which
    on 2026-10-27 made coverage give up on Suryodaya and fall back to lexical
    before d01 and d02 were reached. Keystone's 34 articles, two batches, went
    through fine. So the fix is to stop re-paying for rows that have not moved.

    Keyed on a hash of the embedded text, so an edited article is re-embedded
    and a renamed one does not quietly keep its old vector.
    """
    try:
        with open(_cache_path(instance), encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception:
        return {}
    if raw.get("model") != EMBED_MODEL:
        return {}          # a different model's vectors are not comparable
    return raw.get("rows") or {}


def _save_cache(instance, rows):
    path = _cache_path(instance)
    try:
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"model": EMBED_MODEL, "rows": rows}, fh)
        if os.path.exists(path):
            os.remove(path)
        os.rename(tmp, path)
    except Exception:
        pass           # a cache we cannot write is a slow run, not a failure


def _fingerprint(article):
    return hashlib.sha256(article_text(article).encode("utf-8")).hexdigest()[:16]


def vectors_for(instance, articles):
    """Embeddings for these articles, or None if embedding is unavailable.

    Held in the process and on disk between runs. Only articles whose text has
    changed since the last run are sent to the provider.
    """
    if _give_up(instance):
        return None
    have = _VECTORS.get(instance)
    if have is None:
        cached = _load_cache(instance)
        have = {}
        for a in articles:
            row = cached.get(str(a.get("id")))
            if row and row.get("h") == _fingerprint(a):
                have[a.get("id")] = row["v"]
        _VECTORS[instance] = have
    missing = [a for a in articles if a.get("id") not in have]
    if missing:
        cfg = _llm()
        if cfg is None:
            _note_failure(instance)
            return None
        base, key, _ = cfg
        try:
            for i in range(0, len(missing), EMBED_BATCH):
                if i:
                    time.sleep(BATCH_PAUSE)   # four batches at once is a burst
                chunk = missing[i:i + EMBED_BATCH]
                data = _post(base + "/embeddings", key,
                             {"model": EMBED_MODEL,
                              "input": [article_text(a) for a in chunk]},
                             EMBED_TIMEOUT)
                for a, row in zip(chunk, data["data"]):
                    have[a.get("id")] = row["embedding"]
        except Exception:
            _note_failure(instance)
            return None
        _save_cache(instance, {str(a.get("id")): {"h": _fingerprint(a),
                                                  "v": have[a.get("id")]}
                               for a in articles if a.get("id") in have})
    return have


def embed_query(instance, query):
    if _give_up(instance):
        return None
    cfg = _llm()
    if cfg is None:
        return None
    base, key, _ = cfg
    try:
        data = _post(base + "/embeddings", key,
                     {"model": EMBED_MODEL, "input": [query]}, EMBED_TIMEOUT)
        return data["data"][0]["embedding"]
    except Exception:
        _note_failure(instance)
        return None


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def answers_question(question, article):
    """One focused call: does this article answer this question?

    Returns True, False, or None when the model could not be reached. None is
    not False - an unanswerable question about coverage must not become a
    refusal, so the caller falls back rather than assuming the worst.
    """
    cfg = _llm()
    if cfg is None:
        return None
    base, key, model = cfg
    ask = JUDGE_PROMPT % {"nl": chr(10), "question": _text(question)[:600],
                          "title": _text(article.get("title")),
                          "summary": _text(article.get("excerpt"))[:300]}
    try:
        data = _post(base + "/chat/completions", key,
                     {"model": model, "temperature": 0, "max_tokens": 6,
                      "messages": [{"role": "user", "content": ask}]},
                     JUDGE_TIMEOUT)
        said = data["choices"][0]["message"]["content"].strip().upper()
    except Exception:
        return None
    if said.startswith("YES"):
        return True
    if said.startswith("NO"):
        return False
    return None          # neither word: treat as unknown, not as a refusal


def covering_articles(instance, question, articles):
    """Which of these articles answer the question, best first.

    Returns (covering, ranked, reason):

        covering  the articles the judge said YES to, best-ranked first
        ranked    [(score, article)] for the shortlist it considered
        reason    None on success, else why this is not a usable answer

    A non-None reason means the caller must fall back to its own ranking. It
    never means "nothing covers this".
    """
    if not articles:
        return [], [], "no articles to consider"
    if not _text(question).strip():
        return [], [], "no customer question to check against"

    # Small enough to show the model all of them? Then do that, and skip
    # embeddings entirely.
    #
    # Measured 2026-10-27: the SENDABLE set is 10 articles on Suryodaya and 25
    # on Keystone - not the 100+ in the book, because most are draft, internal
    # or archived. One comparison call over all of them answers correctly and
    # repeatably: d03 NONE twice, d01 and d02 the right lead-time article twice
    # each. That is the whole feature with no embeddings, no cache and no
    # availability probe.
    #
    # Which matters for the graded run more than anything else here. It
    # supplies its own OPENAI_BASE_URL and we cannot see whether it serves
    # /embeddings - but it certainly serves /chat/completions, because the
    # agent could not run at all otherwise. Needing only the endpoint we know
    # exists turns an unverifiable dependency into none.
    #
    # Embeddings stay for the case this cannot cover: a sendable set too long
    # to list, where something has to shortlist first.
    if len(articles) <= CHOOSE_LIMIT:
        picked = choose_answer(question, articles)
        if picked is None:
            return [], [], "coverage could not be judged"
        return picked, [(0.0, a) for a in articles], None

    have = vectors_for(instance, articles)
    if not have:
        return [], [], "embeddings unavailable"
    qv = embed_query(instance, question)
    if qv is None:
        return [], [], "embeddings unavailable"

    scored = []
    for a in articles:
        v = have.get(a.get("id"))
        if v:
            scored.append((cosine(qv, v), a))
    if not scored:
        return [], [], "no article could be embedded"
    scored.sort(key=lambda p: -p[0])
    shortlist = scored[:JUDGE_TOP]

    picked = choose_answer(question, [a for _, a in shortlist])
    if picked is None:
        return [], shortlist, "coverage could not be judged"
    return picked, shortlist, None

CHOOSE_PROMPT = (
    "A customer wrote this:%(nl)s%(nl)s%(question)s%(nl)s%(nl)s"
    "Here are the help articles closest to it:%(nl)s%(articles)s%(nl)s"
    "Which ONE of them answers what the customer actually asked about? An "
    "article about the same product, or the same general area, but a "
    "different problem does NOT answer it. If none of them answers it, say "
    "NONE - that is a complete and correct answer, not a failure to find "
    "something.%(nl)s%(nl)sReply with just the number, or the word NONE.")


def choose_answer(question, articles):
    """Which ONE of these answers the question, if any. [] means none.

    One call for the whole shortlist, not one per article, for two reasons.

    It is cheaper - one call instead of JUDGE_TOP - which matters against a
    30-minute budget when a queue walk asks this per ticket.

    And it is steadier. Asking per article, at temperature 0, gave different
    answers on the same pair across runs: d02's correct article was judged YES
    in one check on 2026-10-27 and NO twenty minutes later, which turned an
    answer into a refusal. A single comparison is a different question - "which
    of these, if any" rather than "is this one acceptable" - and the model
    commits to one row rather than re-deciding a borderline case three times.

    Returns None when the model could not be reached, which is not the same as
    NONE from the model and must not become a refusal.
    """
    if not articles:
        return []
    cfg = _llm()
    if cfg is None:
        return None
    base, key, model = cfg
    listed = chr(10).join(
        "%d. %s - %s" % (i + 1, _text(a.get("title")),
                         _text(a.get("excerpt"))[:200])
        for i, a in enumerate(articles))
    ask = CHOOSE_PROMPT % {"nl": chr(10), "question": _text(question)[:600],
                           "articles": listed}
    try:
        data = _post(base + "/chat/completions", key,
                     {"model": model, "temperature": 0, "max_tokens": 8,
                      "messages": [{"role": "user", "content": ask}]},
                     JUDGE_TIMEOUT)
        said = data["choices"][0]["message"]["content"].strip().upper()
    except Exception:
        return None
    if "NONE" in said:
        return []
    for i in range(len(articles), 0, -1):
        if str(i) in said:
            return [articles[i - 1]]
    return None          # unparseable: unknown, not a refusal

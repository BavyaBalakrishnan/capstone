"""Does semantic retrieval separate "an article answers this" from "none does"?

Read-only. Touches NOTHING the agent or the harness uses: it embeds the
articles and the task prompts, prints the numbers, and exits. Run it, read the
table, decide. It exists because the answer to d03 looked like a threshold
problem for five attempts and is not one.

    python -m tools.semantic_probe

Background. `kb_candidates` ranks by lexical overlap, and that signal is wrong
at BOTH ends:

  * d01 and d02 ask in words the right article does not use ("how long before
    my stuff turns up?" against "What lead time can I expect?"). Lexical
    overlap misses it - on 2026-10-22 it ranked "Mounting a bench vice so it
    stops moving" first, on the substring match `take`. Those tasks pass only
    because the agent falls back to reading the whole book and the MODEL does
    the semantic work.

  * d03 asks about a shipment 48 pieces short, and two articles share the
    product's name - `step`, `frame` - while saying nothing about a shortage.
    Lexical overlap picks one.

So five attempts to fix d03 by thresholding that signal failed, and had to:
the decisive measurement is that d03's wrong answer covers 14% of the query
and d01/d02's RIGHT answers cover 11%. No threshold lies between them.

What this probe measures instead. Embed each sendable article (title +
excerpt) and the task prompt, rank by cosine similarity, and print the top two
scores and the gap between them.

Measured 2026-10-22, gemini-embedding-001, 3072 dims:

    task   top1   top2   margin   covered?
    d01    0.757  0.640  +0.117   yes - and it ranks the RIGHT article first
    d02    0.701  0.594  +0.106   yes - same right article
    i05    0.803  0.667  +0.136   yes, then blocked by the rating rule
    i04    0.625  0.577  +0.049   no
    d03    0.716  0.707  +0.009   no

The discriminator is the MARGIN, not the score. d03's top score is as high as
d01's, so no absolute threshold separates them. But when one article genuinely
answers a question it stands clear of the field, and when none does the top
candidates cluster - several are vaguely about the product and none is
distinctly the answer. d03's margin is an order of magnitude smaller than
d01's.

i05 is not a counterexample. Its margin is large because an article really
does cover the topic; it must not be SENT because it is rated 0 helpful / 51
not helpful. Coverage and quality are different gates and the band rule
already does the second one. That the new signal says nothing about rating is
a point in its favour: it does one job.

NOT SHIPPED, on purpose. Five data points are not a measurement, and a
threshold fitted to five points is a guess wearing a number. Switching
retrieval would change the path all 30 passing tasks depend on.

If you pick this up, the order matters:

  1. Put it behind SEAT15_SEMANTIC_KB, default OFF, so the current behaviour
     stays byte-identical.
  2. Run the two-arm grid across EVERY task, not the five here. The question
     is never "does it fix d03" - it is "which tasks separate the arms".
  3. Only make it the default if the separation is clean, and keep lexical as
     the fallback for when embeddings are unavailable. The provider returned
     503 on a third of our calls one afternoon this month.

The reason to do it is not d03. It is that d01 and d02 pass today only because
a capable model rescues a bad ranking - which is exactly the model-diligence
dependency the graded run of 2026-10-21 punished twice, in h01 and q01. d03 is
the symptom; the fragility is the disease.
"""
import glob
import json
import math
import urllib.request

from seat15.harness.client import Client, load_env

EMBED_MODEL = "gemini-embedding-001"
BATCH = 32

# What each task's correct behaviour is, so the table can be read at a glance.
ANSWER = {"d01", "d02"}
REFUSE = {"d03", "i04", "i05", "r01", "r02", "r03"}


def embed(texts, env):
    base = env["SEAT15_LLM_BASE_URL"].rstrip("/")
    out = []
    for i in range(0, len(texts), BATCH):
        body = json.dumps({"model": EMBED_MODEL,
                           "input": texts[i:i + BATCH]}).encode()
        req = urllib.request.Request(
            base + "/embeddings", body,
            {"Authorization": "Bearer " + env["SEAT15_LLM_API_KEY"],
             "Content-Type": "application/json"})
        payload = json.load(urllib.request.urlopen(req, timeout=60))
        out.extend(x["embedding"] for x in payload["data"])
    return out


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def load_prompts():
    tasks = {}
    for path in sorted(glob.glob("seat15/harness/tasks/*.json")):
        with open(path, encoding="utf-8") as fh:
            t = json.load(fh)
        if t.get("prompt"):
            tasks[t["id"]] = t
    return tasks


def main():
    env = load_env()
    tasks = load_prompts()
    print("%-38s %-6s %-6s %-7s %s"
          % ("task", "top1", "top2", "margin", "expected"))
    for instance in ("suryodaya", "keystone"):
        client = Client(instance)
        client.login()
        articles = [a for a in client.list("KBArticle")
                    if a.get("status") == "published"
                    and a.get("visibility") == "public"]
        if len(articles) < 2:
            print("%s: %d sendable articles, nothing to rank"
                  % (instance, len(articles)))
            continue
        vectors = embed(["%s. %s" % (a.get("title") or "",
                                     (a.get("excerpt") or "")[:400])
                         for a in articles], env)
        for task_id, task in sorted(tasks.items()):
            key = task_id[:3]
            if key not in ANSWER | REFUSE:
                continue
            if instance not in task.get("instances", []):
                continue
            query = embed([task["prompt"]], env)[0]
            scores = sorted((cosine(query, v) for v in vectors), reverse=True)
            print("%-38s %.3f  %.3f  %+.3f  %s"
                  % (task_id[:38], scores[0], scores[1],
                     scores[0] - scores[1],
                     "ANSWER" if key in ANSWER else "refuse"))


if __name__ == "__main__":
    main()

# Orchestrator v1 → v2: Change Summary

## Overview

v2 introduces three architectural changes discovered through analysis of the
system prompt's relationship to real-world constraints: (1) the orchestrator
must not hold full article text in context, (2) search results must be
normalized across providers, and (3) verification failures must be recoverable
through intelligent loop-back rather than blind acceptance.

---

## Change 1: File-Reference Architecture (Major)

**Problem:** `fetch_page` returns full article content (5–50KB) directly to the
orchestrator. After 3–5 fetches, the orchestrator's context window is consumed
by raw HTML/text, leaving no room for reasoning about what to do with it.

**Solution:** Full text is written to temporary files. The orchestrator
receives only a summary (~first 200 words) + metadata + a file pointer.
Worker LLMs (`verify_claim`, `generate_document`) read the files directly.

### Schema changes

| Tool | v1 | v2 |
|---|---|---|
| `fetch_page` output | `{ok, text, reason}` | `{ok, file_ref, summary, word_count, title, reason}` |
| `verify_claim` input | `{claim, url, page_text}` | `{claim, url, file_ref}` |
| `generate_document` manifest entry | `{claim, source_url, verification_result}` | `{claim, source_url, file_ref, verification_result}` |

### New failure handling

- If `file_ref` is not readable: re-fetch the URL, retry once, then mark claim
  as unverified if it fails again (Section 6).

---

## Change 2: Search Result Normalization (Minor, Section 3)

**Problem:** Every search API (DuckDuckGo, Tavily, SerpAPI, Brave, Google CSE)
returns a different JSON shape with different key names (`body` vs `snippet` vs
`content` vs `description`). The orchestrator prompt should not know about this.

**Solution:** The `search_web` tool description now explicitly states it
normalizes across providers to a single internal format: `{results: [{url, title, snippet}]}`.
Added a note that snippets are ~150–350 chars and safe to keep inline.

---

## Change 3: Research Triage Rules (New, Section 5)

**Problem:** v1 had no guidance on how to use search snippets. The orchestrator
could either blindly trust rankings or overthink every result.

**Solution:** Added explicit triage rules:
- Use snippets for lightweight sanity checks (does the page mention my topic?)
- Trust search engine ranking as a reasonable prior, not a correctness guarantee
- Skip results where the engine clearly misunderstood the query (e.g., "does"
  the verb vs. a transistor)
- Actual relevance is decided after `fetch_page` + `verify_claim`

---

## Change 4: REFINE Loop-Back (Major, Sections 2, 5, 8)

**Problem:** v1 had only a vague sentence: *"You may loop back to earlier stages
if new information requires it."* This gave the model permission but no
procedure — resulting in either infinite loops or premature abandonment.

**Solution:** Added Stage 4b (REFINE) as a first-class pipeline stage with
explicit gate conditions.

### When to loop back (not when to stop)

| Condition | Action |
|---|---|
| Zero claims verified | MUST loop back (document has no foundation) |
| A MAJOR claim failed | Loop back (definitional/core claim unverified) |
| A minor claim failed | Do NOT loop back — flag in ⚠️ section and proceed |

### How to reformulate

- Extract key terms from the *failed claim itself* (turns verification failure
  into search signal)
- Try alternative phrasings: "X vs Y", "X explained", "X internals"
- Try site-scoped queries: `site:arxiv.org X`, `site:docs.python.org X`
- Vary technical depth: add "tutorial" for basics, "reference" for depth

### When to stop looping (saturation rule)

- If 2 consecutive reformulations produce zero new verified claims, stop.
  Further searching is unlikely to help and burns the search budget.
- Previously verified claims are preserved — you fill gaps, don't restart.

---

## Change 5: Worked Example Extended (Section 8)

**Problem:** v1's worked example was a clean happy path — every claim verified,
no loop-backs needed. This taught the model ideal behavior but not recovery
behavior.

**Solution:** Extended from 12 cycles to 16 cycles. Added:
- Cycle 9–10: A second `search_web` + `fetch_page` round for supplementary
  material (showing research breadth)
- Cycle 11: A `verify_claim` that returns `supported: false` — this is the
  trigger event
- Cycles 12–13: The REFINE loop-back — reformulated keywords extracted from
  the failed claim, site-scoped search, successful re-verification against an
  already-fetched trusted source
- Cycles 14–16: Compilation, quality gate, commit, done

The example now mirrors the three-stage relevance pipeline (search snippet →
triage → fetch → verify → loop-back if needed) and demonstrates the saturation
rule implicitly (the first reformulation succeeded, so no second was needed).

---

## What Did NOT Change

- Role & Identity (Section 1) — identical
- Format Constraints (Section 4) — identical
- Document Template (Section 7) — identical
- Clarification threshold rules — identical
- Verification threshold rules (zero-claims fallback, any-unverified-flagged) — identical
- Quality gate before COMMIT — identical
- Looping safety call limits — identical (5/10/20/3)
- Tool `done`, `ask_user`, `commit_document`, `read_repo_index` — identical schemas

---

## Token Budget Impact

| Component | v1 (~chars) | v2 (~chars) | Delta |
|---|---|---|---|
| Orchestrator prompt (one-time) | ~12,500 | ~16,500 | +4,000 |
| Per `fetch_page` cycle | ~5,000 (full text) | ~300 (summary) | −4,700 |
| Per `verify_claim` cycle | ~1,200 (with page_text) | ~300 (file_ref only) | −900 |
| After 10-cycle session | ~12,500 + 50,000 = ~62,500 | ~16,500 + 3,000 = ~19,500 | −43,000 |

v2 is ~4,000 chars larger as a static prompt but saves ~4,700 chars per
`fetch_page` cycle. Over a typical session, the per-cycle savings dominate.

---

*Generated from diff of prompts/orchestrator_v1.txt → prompts/orchestrator_v2.txt*

# Orchestrator v2 → v3: Change Summary

## Overview

v3 resolves a design ambiguity in the research strategy. v2's pipeline table
implied a batch-first approach (gather all → verify all → decide), but the
worked example interleaved searching, fetching, and verifying in a way that
contradicted the table. A model reading v2 would learn the example's behavior
(which was inconsistent) rather than the pipeline's stated intent.

v3 makes the research strategy explicit by splitting it into two named phases
with distinct behaviors and a hard rule preventing interleaving in Phase 1.

---

## Change 1: Two-Phase Research Strategy (Sections 2, 3, 5, 8)

### What changed

Stage 3 (RESEARCH) and Stage 4b (REFINE) are now explicitly framed as
two phases with different goals, search strategies, and sequencing rules.

**Phase 1: Initial Sweep** (Stage 3)
- Broad discovery: 2–3 distinct queries from different angles before ANY
  verification
- Suggested angles: definition/fundamentals, internals/mechanism,
  applications/use cases, comparisons, historical/formal
- Fetch the most promising 3–5 pages across all Phase 1 queries combined
- Hard rule: "Do not verify one claim and then immediately search for more
  — batch Phase 1 first" (Section 5)

**Phase 2: Targeted Refill** (Stage 4b)
- Surgical: each query is a direct response to a SPECIFIC failed claim
- Keywords extracted from the failed claim itself
- "Do NOT do broad discovery in Phase 2 — that work belongs in Phase 1"
  (Section 5)
- Same saturation rule as v2 (2 consecutive failures = stop)

### Why this matters

| v2 behavior | v3 behavior |
|---|---|
| Pipeline said "batch" but example interleaved | Pipeline and example are consistent |
| No suggestion for how many Phase 1 queries | Explicit: 2–3 from different angles |
| No suggestion for how many pages to fetch | Explicit: 3–5 best candidates across all queries |
| Phase 1 and Phase 2 searches looked identical | Phase 1 = broad angles, Phase 2 = surgical claim-driven |
| Could waste cycles interleaving search + verify | Clear sequencing prevents premature verification |

### Budget allocation example

With a 5-search_web budget:
- v2: unclear split → could be 1 query + 4 loop-backs, or 4 queries + 1 loop-back
- v3: 2–3 Phase 1 queries → 2–3 remaining for Phase 2 → clean allocation

---

## Change 2: Worked Example Re-annotated (Section 8)

### What changed

The same 16-cycle example now has visual stage markers and phase labels on
each cycle:

```
 ═══════════════════════════════════════════
 │ STAGE 3: RESEARCH — Phase 1: Initial    │
 │ Sweep (2 distinct queries before        │
 │ verification)                          │
 ═══════════════════════════════════════════

--- ORCHESTRATOR CYCLE 3 --- [Phase 1, Query 1/2: fundamentals]
--- ORCHESTRATOR CYCLE 4 --- [Phase 1, Query 2/2: internals/applications]
--- ORCHESTRATOR CYCLE 5 --- [Phase 1, fetch from query 1]
...
--- ORCHESTRATOR CYCLE 9 --- [Phase 1 complete, beginning VERIFY]
```

And the REFINE section:

```
 ═══════════════════════════════════════════
 │ STAGE 4b: REFINE — Phase 2: Targeted   │
 │ Refill (surgical query driven by the   │
 │ specific failed claim)                 │
 ═══════════════════════════════════════════

--- ORCHESTRATOR CYCLE 12 (PHASE 2 REFINE TRIGGERED) ---
```

The cycles themselves are structurally identical to v2 — but the phase
annotations make the two-phase pattern impossible to miss. A model reading
this will pattern-match: "Phase 1 = batch, Phase 2 = surgical."

---

## Change 3: Tool Description Updates (Section 3)

### What changed

The `search_web` tool's "When" field now distinguishes the two phases:

| v2 | v3 |
|---|---|
| "Stage 3 (RESEARCH) and Stage 4b (REFINE). Call multiple times with different queries for comprehensive coverage." | "Stage 3 (Phase 1: Initial Sweep — 2–3 queries from different angles) and Stage 4b (Phase 2: Targeted Refill — surgical queries driven by specific failed claims)." |

The `fetch_page` tool's "When" field now specifies Phase 1 volume:

| v2 | v3 |
|---|---|
| "Stage 3 (RESEARCH). Also during Stage 4b (REFINE) if new URLs are discovered." | "Stage 3 (Phase 1: fetch the most promising 3–5 pages across all initial queries). Also during Stage 4b (Phase 2) if new URLs are discovered from reformulated searches." |

---

## Change 4: Decision Rules Expanded (Section 5)

### What changed

A new top-level rule block added between Clarification and Research Triage:

```
  Phase 1: Initial Sweep rules (Stage 3 — before any verification):
    - Run 2–3 distinct search_web queries before beginning verification.
      Each query must approach the topic from a different angle. Suggested
      angles (pick 2–3 that fit the topic): ...
    - Fetch the most promising 3–5 pages across ALL Phase 1 queries combined.
    - Only after all Phase 1 pages are fetched and a candidate claim list
      exists in your head should you move to Stage 4 (VERIFY). Do not verify
      one claim and then immediately search for more — batch Phase 1 first.
```

The existing REFINE rules are now titled "Phase 2: Targeted Refill rules"
with an added distinguishing sentence: "Phase 2 searches are surgical: each
is a direct response to a SPECIFIC failed claim... Do NOT do broad discovery
in Phase 2 — that work belongs in Phase 1."

The search budget note now clarifies: "You may call search_web at most 5
times per session (budget includes both Phase 1 and Phase 2 queries)."

---

## What Did NOT Change

- Role & Identity (Section 1) — identical
- Format Constraints (Section 4) — identical
- Available Tools schemas — identical signatures, only "When" notes updated
- Document Template (Section 7) — identical
- Clarification threshold rules — identical
- Research triage rules — identical
- Verification threshold rules — identical
- Quality gate before COMMIT — identical
- Call limits (5/10/20/3) — identical
- Failure Behavior (Section 6) — identical
- File lifecycle error handling — identical
- Tool `done`, `ask_user`, `commit_document`, `read_repo_index` — identical

---

## Token Budget Impact

| Component | v2 | v3 | Delta |
|---|---|---|---|
| Orchestrator prompt (static) | ~16,500 chars | ~18,400 chars | +1,900 |
| Phase/angle guidance | ~350 chars (implied) | ~900 chars (explicit) | +550 |
| Worked example annotations | 0 chars (none) | ~1,200 chars (stage markers + phase labels) | +1,200 |
| Per-cycle cost (no change) | same | same | 0 |

v3 is ~1,900 chars (~475 tokens) larger than v2. This is a one-time cost
paid once per session. The benefit is that Phase 1/Phase 2 ambiguity —
which could cause 2–3 wasted search_web cycles (each ~375 tokens of
snippets + ~200 tokens of thought + tool JSON) — is eliminated.

---

## Design Rationale: Why Two Phases Instead of One Iterative Loop

A pure iterative approach (search → verify → search → verify → ...) has
three failure modes:

1. **Narrow framing:** The first query anchors the entire research direction.
   If you search "descriptor protocol definition" first and verify it, you
   may never think to search "descriptor protocol internals" because the
   definition seems complete.

2. **Premature satisfaction:** Verifying one claim early creates a false sense
   of progress. You might generate after 2 verified claims, missing 3 more
   that would have come from a second angle.

3. **Reformulation fatigue:** Each loop-back costs mental energy. After 2
   iterations, models tend to accept weaker sources rather than reformulate
   again. Batching Phase 1 upfront puts the discovery work before the
   fatigue sets in.

The two-phase split forces breadth-first discovery (you MUST try 2–3 angles)
before you're allowed to verify anything, and restricts reformulation to
surgical gap-filling rather than aimless re-searching.

---

*Generated from diff of prompts/orchestrator_v2.txt → prompts/orchestrator_v3.txt*

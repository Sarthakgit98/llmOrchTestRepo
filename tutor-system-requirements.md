# Tutor System — Project Requirements

## Project Summary
A CLI-based tutor system running locally on a MacBook, with potential future migration to a Raspberry Pi. The user requests topics via chat. An LLM agent researches the topic, generates a structured markdown document with verified references, and commits it autonomously to a private GitHub repository.

Primary goal is also personal learning, so raw API calls are preferred over heavy frameworks.

---

## Core Requirements

### Agent & LLM
- Model-agnostic. All LLM calls routed through a single abstraction:
  ```python
  def call_llm(messages: list, model: str, api_key: str, system: str = None) -> str
  ```
- No agent framework (LangChain etc.). Raw API calls only.
- Language: Python.
- LLM access via **Pi agent harness**, potentially with **Open Code Bridge** for cheaper/proxied model access. The `call_llm` abstraction must accommodate this without leaking provider specifics into the rest of the system.

### CLI & Session
- Runs locally on MacBook, triggered on demand.
- Plain CLI interface.
- Conversation history retained within a session (for clarifying questions and followups).
- Session ends and memory is cleared once the agent decides the document is complete.
- Agent commits autonomously — no user approval step before commit.
- No hard limit on clarifying back-and-forth for now (to be guardrailed later via agent instructions).

### GitHub Integration
- New private repo (to be created).
- Commits directly to `main`. No PRs.
- Standard Git tooling — **GitPython** or subprocess `git` calls are acceptable. No need to drop to raw GitHub REST API.
- Folder structure: `topic/subtopic/file.md` or `topic/file.md` — agent infers appropriate depth.
- Agent infers parent topic by reading existing repo contents, then confirms with user before proceeding.
- If a topic already has a document, a new version is created with a numeric suffix: `topic-v2.md`.

### Document Structure (standard template)
```
# [Topic Title]

## Overview
What it is, why it matters, scope of this document.

## Mental Model
"Think of it like X" — one clear analogy.

## Core Concepts
Subsections per major concept. Depth proportional to complexity.

## Worked Examples
Concrete, practical examples with explanation.

## Perspectives  *(omitted if not applicable)*
Brief coverage of genuine disagreements or alternative approaches.

## Related Documents
Links to parent doc and any existing subtopics in the repo.

## References
Numbered list. Each entry: claim context, source title, URL, verification status.

## ⚠️ Unverified Claims  *(omitted if not applicable)*
Prominent section flagging claims where credible sourcing failed.
```

- Target length: up to ~30-minute read. No bloating if content doesn't warrant it.
- Factual topics only (software engineering, mathematics primarily). Multiple perspectives shared briefly where they exist.

### Reference Verification
- Agent fetches linked content, confirms the cited claim appears in the source, and checks the link is live.
- Ideal sources: academic/peer-reviewed (arXiv, papers, official docs).
- If credible references cannot be found: document is still produced, but with a prominent `⚠️ Unverified Claims` section.
- A `TRUSTED_SOURCES.md` file in the repo root lists pre-approved domains (e.g. `arxiv.org`, `docs.python.org`). Sources on this list skip claim-matching verification (link-live check still applies).

### Topic Handling
- Anything goes, but intended for software engineering and mathematics domains.
- Subtopics link back to their parent document.
- Agent flags topics where credible references cannot be found (document still produced with warning).

---

## System Architecture

```
CLI (MacBook)
 └── Session Manager        # in-memory message history, cleared on session end
      └── Orchestrator      # core LLM agent, raw API calls, model-agnostic
           ├── Repo Inspector     # reads local repo structure (GitPython / subprocess),
           │                      # infers parent topic, confirms with user
           ├── Research Module    # [OPEN POINT] web search + scraper, pluggable
           ├── Reference Verifier # checks link live, fetches content,
           │                      # matches claim; relaxed for TRUSTED_SOURCES.md
           ├── Document Generator # assembles markdown to standard template
           └── Git Publisher      # commits to main via GitPython or subprocess git
```

**Session flow:**
1. User inputs topic via CLI.
2. Repo Inspector reads existing local repo structure.
3. Agent asks clarifying questions as needed.
4. Agent infers parent doc, confirms with user.
5. Research → Verify → Generate → Commit.
6. Agent closes session, memory cleared.

---

## Open Points (Undecided)

| # | Area | Detail |
|---|------|--------|
| 1 | Web Search | API/tool undecided. Must be pluggable. Options: Tavily, SerpAPI, DuckDuckGo scrape. |
| 2 | Web Scraping | Approach undecided. Likely `requests` + `BeautifulSoup`; headless browser not ruled out. |
| 3 | Agent Guardrails | No limit on clarifying back-and-forth for now. To be defined later via system prompt constraints. |
| 4 | Session End Signal | Agent decides when doc is complete and closes session. Exact decision logic TBD (prompt-defined). |
| 5 | Open Code Bridge | Whether Open Code Bridge is used for LLM proxying, and which models it exposes, is TBD. The `call_llm` abstraction must remain valid regardless. |
| 6 | Pi Migration | Current target is MacBook. Pi is a possible future deployment target, not an active constraint. |

---

## Stretch / Long-Term Goals (Not in scope yet)

- Migration to Raspberry Pi once system is stable on MacBook.
- Telegram interface replacing or supplementing CLI.
- HTML document output instead of (or alongside) markdown, for human readability.
- Multi-agent architecture: one master agent delegates to subagents for research, writing, and verification.
- Asynchronous document generation with user notification on completion.
- Visual or textual data map linking related documents under a major topic.
- Ability to update/correct an existing document when user manually provides a credible source.

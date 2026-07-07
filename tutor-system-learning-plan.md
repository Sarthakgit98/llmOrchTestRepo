# Tutor System — Learning Plan & Getting Started Guide

*Personal reference for building the LLM-powered document tutor.*

This plan covers every meaningful knowledge gap between a solid general programming background and being able to build this system reliably — without frameworks, without hand-holding from a library that hides the machinery. Each section explains what to learn, why it matters specifically for this project, and a minimal starting point so you know where to open the first file or terminal window.

The system is assumed to run locally on a MacBook, calling external LLM APIs (potentially via Open Code Bridge / Pi agent harness), storing documents in a local Git repo, and committing autonomously on completion.

---

## Priority Order

*Work through these in sequence. Each one unlocks the next.*

| # | Topic | Why It Matters Here |
|---|-------|---------------------|
| 1 | **LLM Agent Patterns (No Frameworks)** | The Orchestrator is a raw ReAct loop — nothing works without understanding this first. |
| 2 | **Prompt Engineering for Agents** | The quality of every output depends entirely on how the system prompt is written. |
| 3 | **Session & State Machine Design** | Your stated architecture gap. Bad orchestration design causes cascading failures. |
| 4 | **Git Integration (GitPython / subprocess)** | More depth than it looks — reading tree structure, staging, and committing programmatically. |
| 5 | **Claim Verification Logic** | Architecturally subtle; easy to get sloppy in ways that break trust in the output. |
| 6 | **Web Scraping & Graceful Failure** | Mechanical, but failure modes dominate real-world use. |
| 7 | **LLM Proxy & call_llm Abstraction** | Needed to accommodate Open Code Bridge without leaking provider details. |
| 8 | **Adapter Pattern for Pluggable Modules** | Unlocks swappable search providers and future architecture changes. |
| 9 | **Python Fundamentals to Solidify** | Dataclasses, logging, env management — small gaps with outsized effect on reliability. |

---

## 1. LLM Agent Patterns (Without Frameworks)

An agent is just a loop: the model reasons, decides to take an action (call a tool), your code executes that action and returns a result, then the model sees the result and reasons again. Every framework — LangChain, LlamaIndex, AutoGen — is wrapping this loop. You need to write the loop yourself.

### 1.1 The ReAct Loop

ReAct (Reason + Act) is the pattern where the model is instructed to alternate between a Thought (reasoning step) and an Action (tool call), iterating until it produces a final answer. Your Orchestrator is a ReAct loop.

**Getting started:**
- Read the original ReAct paper abstract ([arxiv.org/abs/2210.03629](https://arxiv.org/abs/2210.03629)) — just the intro and figures are enough to understand the concept.
- Write a minimal Python loop: call the API, parse the model's reply for a structured action block, execute the action, append the result to the messages list, call again. No more than 50 lines.
- Start with a toy tool — e.g. "get current time" — before adding real tools.

### 1.2 Tool-Use via Prompt Engineering

Before using native function-calling APIs, understand how to get a model to emit a structured tool call using only a well-crafted system prompt. This is the fallback for models that don't support native tool use.

**Getting started:**
- Write a system prompt that tells the model to respond in JSON with a fixed schema: `{"action": "search", "query": "..."}` or `{"action": "done", "content": "..."}`
- Parse the reply with `json.loads()` — build in a retry for malformed output.
- Add a schema validator (Python's `jsonschema` library) so malformed output is caught cleanly, not silently.

### 1.3 Native Function / Tool Calling (Anthropic API)

Anthropic's API has a `tools` parameter that lets you declare callable functions. The model returns a structured `tool_use` block instead of text when it wants to call one. Your `call_llm` abstraction needs to handle both text and `tool_use` content blocks.

**Getting started:**
- Read: [Anthropic tool use guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- Implement one tool (e.g., fetch URL) declared in the tools array, handle the `tool_use` response block, return a `tool_result` back to the model.
- Make sure `call_llm()` returns a unified type — a string for text, a structured dict for tool calls — so the Orchestrator doesn't need to know which path triggered.

### 1.4 Multi-Step Agent Loops & Termination

An agent loop runs until some termination condition. For this system, the agent itself decides when the document is ready. You need to design the termination signal cleanly: either a special action type (`"action": "commit"`) or a prompt instruction that produces a parseable done signal.

**Getting started:**
- Add a `max_iterations` safety cap to your loop — the agent can't decide it's done if it's stuck. Start with 15.
- Define "done" as a specific action in your tool schema, not a free-text judgement. This keeps the loop deterministic.

---

## 2. Prompt Engineering for Agentic Systems

Prompting an agent is different from prompting for a single answer. The system prompt is the agent's constitution — it defines personality, available tools, output format rules, and decision logic all at once. Getting this right has more leverage on output quality than any other single choice.

### 2.1 System Prompt Design

A good agent system prompt covers: role and purpose, available tools and how to invoke them, format constraints (always respond in JSON, always reason before acting), decision rules (when to ask the user vs. proceed), and failure behaviour (what to do when a source can't be verified).

**Getting started:**
- Write a single-page system prompt for the Orchestrator. Treat it like a spec document, not a casual instruction.
- Include a worked example of a complete Thought → Observation → Done cycle inline in the prompt as a few-shot example.
- Version your system prompt in a file (`prompts/orchestrator_v1.txt`). You will iterate on it more than any code file.

### 2.2 Structured Output Prompting

Models will drift from your required JSON schema under pressure (long chains, unexpected inputs). Design your prompt so it's clear what happens if the model fails to comply — not just what the format should be.

**Getting started:**
- Add an explicit line to your system prompt: *"If you are unsure what action to take, use the `ask_user` action. Never return freeform text outside the JSON schema."*
- Build a `parse_or_retry(response, retries=2)` helper that re-prompts with the parse error attached if JSON is malformed.

### 2.3 Few-Shot Examples in System Prompts

A single concrete example of a full agent cycle, embedded in the system prompt, reduces format errors dramatically — especially on smaller models.

**Getting started:**
- Write one complete ideal interaction (user input → full agent cycle → committed document) and embed it in your system prompt under an `## Example` heading.
- Keep it realistic: include one clarifying question, one failed URL check, and a graceful fallback to the unverified claims section.

### 2.4 Chain-of-Thought Elicitation

Asking the model to reason before acting (a `thought` field before the `action` field in your JSON schema) measurably reduces errors on multi-step tasks like research & verification.

**Getting started:**
- Add a required `"thought"` key to your action schema that must be populated before the `action` key. The model's reasoning becomes auditable — useful for debugging the agent.

---

## 3. Session & State Machine Design

*This is the area flagged as needing the most attention.* An unstructured orchestrator that passes data around as loose variables will develop subtle, hard-to-reproduce bugs as the agent chain gets longer. Thinking in state machines before writing code prevents most of this.

### 3.1 Conversation History as State

The model has no persistent memory. The messages list is the entirety of what it knows. Every action result, user reply, and tool output must be appended correctly or the agent loses context.

**Getting started:**
- Use a typed data structure for messages from the start. A dataclass `Message(role, content, tool_use_id=None)` is sufficient. Dicts are fine but become messy quickly.
- Write a `trim_history(messages, max_tokens)` function early, even before you need it. Context windows fill faster than expected during multi-step research.

### 3.2 Explicit State Machines

The session flow (Inspect → Commit) is a state machine. Implementing it explicitly — even as a simple Python Enum and a `while state != DONE` loop — makes transitions auditable and prevents the agent from skipping steps.

**Getting started:**
- Define a `SessionState` enum with one value per pipeline stage. The Orchestrator's main loop switches on this enum — each stage has a dedicated handler function.
- Log every state transition to stdout during development. It turns a black-box agent into a readable step-by-step trace.

### 3.3 Passing State Cleanly

A `SessionContext` dataclass — holding the topic, clarifications gathered, research results, verified references, and final document — should be the single source of truth passed between modules. No globals.

**Getting started:**
- Define the full `SessionContext` dataclass before writing any module. It acts as the interface contract between components.
- Each module (RepoInspector, ResearchModule, etc.) takes a `SessionContext` in and returns an updated one. This makes each component independently testable.

---

## 4. Git Integration (GitPython / subprocess)

The GitPython library wraps the command-line git interface cleanly. `subprocess` git is simpler but requires string-building for every command. Either works — GitPython is more readable for complex operations like reading tree structure.

### 4.1 Reading Repo Structure

The Repo Inspector needs to list existing topic folders so the agent can infer the correct parent topic for a new document.

**Getting started:**
```bash
pip install gitpython
```
```python
from git import Repo
repo = Repo('/path/to/your/repo')
tracked = [item[0] for item in repo.index.entries]
# Returns paths like 'software/algorithms/sorting.md'
```

### 4.2 Writing and Committing a File

Writing a new document means creating the file at the right path, staging it, and committing with a descriptive message.

```python
repo = Repo('/path/to/repo')
path = os.path.join(repo.working_dir, 'topic/subtopic/file.md')
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w') as f:
    f.write(document_content)
repo.index.add([path])
repo.index.commit('Add document: topic/subtopic/file.md')
```

### 4.3 Versioning (`topic-v2.md`)

Before writing, the Repo Inspector checks if a file at that path already exists and increments the version suffix.

**Getting started:**
- Write a `resolve_path(repo, proposed_path) -> str` helper that checks existing tracked files, increments `-v2`, `-v3` etc., and returns the final safe path before any file is written.

---

## 5. Claim Verification Logic

The Reference Verifier is the most architecturally subtle component. Its job is not just to check that a URL is live — it must check that the specific claim appears in the fetched content, and handle the case where it can't verify gracefully without crashing the pipeline.

### 5.1 Substring vs. Semantic Matching

Naive substring search fails frequently — a source might use different wording for the same claim. The practical approach: chunk the fetched page content, pass the chunks and the original claim to the LLM, ask it to judge whether the claim is supported. This is a good early use of the `call_llm` abstraction.

**Getting started:**
- Write a `verify_claim(claim: str, url: str) -> VerificationResult` function.
- `VerificationResult` is a dataclass with fields: `live: bool`, `supported: bool`, `trusted: bool`, `note: str`
- Chunk page text into ~500-word windows. Ask the LLM: *"Does any of the following text support this claim? Answer yes/no and quote the relevant sentence if yes."*

### 5.2 Trusted Source Short-Circuiting

Sources listed in `TRUSTED_SOURCES.md` in the repo root skip the claim-matching step — a live URL check is enough. Load this list once at session start.

**Getting started:**
- Load and parse `TRUSTED_SOURCES.md` into a `set[str]` of domain strings at session initialisation. Pass it into the verifier as a parameter, not a global.
- The check: `if urllib.parse.urlparse(url).netloc in trusted_domains: skip_claim_match()`

### 5.3 Graceful Degradation

Verification failure must not crash the pipeline. It sets a flag on the reference object, and the document generator picks this up when assembling the "Unverified Claims" section.

**Getting started:**
- Never raise an exception in the verifier for verification failure — only for network errors above a retry threshold. Verification failure is a valid, expected output.
- The `VerificationResult.supported = False` path should be as well-tested as the success path.

---

## 6. Web Scraping & Content Extraction

The Research Module and Reference Verifier both need to fetch and parse web pages. The failure modes dominate real-world use more than the happy path.

### 6.1 `requests` + BeautifulSoup Baseline

**Getting started:**
```bash
pip install requests beautifulsoup4 lxml
```
```python
# Always set a User-Agent header and a timeout
resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
# Extract body text
text = BeautifulSoup(resp.text, 'lxml').get_text(separator=' ', strip=True)
```

### 6.2 Handling Failure Cases

Build a `fetch_url(url) -> FetchResult` helper that wraps all failure types cleanly:
- `FetchResult(ok=False, reason='timeout')`
- `FetchResult(ok=False, reason='http_{code}')`
- JavaScript-only page (empty body text) → `FetchResult(ok=False, reason='js_required')`
- Paywall / login wall (short page with no claim-relevant content) → fallback to unverified

### 6.3 Content Quality

Raw `get_text()` returns navigation, footers, cookie notices, and ads alongside article content. Consider the `trafilatura` library — it extracts main article text with one function call and handles most real-world pages well.

**Getting started:**
```bash
pip install trafilatura
```
```python
html = trafilatura.fetch_url(url)
text = trafilatura.extract(html)
# Falls back to BeautifulSoup if trafilatura returns None
```

---

## 7. LLM Proxy & `call_llm` Abstraction

Open Code Bridge acts as a proxy layer — you call it like a standard API but it routes to cheaper or alternative model backends. The `call_llm` abstraction must accommodate this without leaking provider details into any other module.

### 7.1 The Abstraction Contract

The function signature is fixed by the requirements:

```python
def call_llm(
    messages: list,
    model: str,
    api_key: str,
    system: str = None
) -> ...
```

Everything else — base URL, headers, provider-specific parameters — is configured per-provider inside this function. The Orchestrator calls `call_llm` and never imports anything provider-specific.

### 7.2 Supporting Multiple Backends

**Getting started:**
- Use an environment variable `LLM_PROVIDER=anthropic|opencode|openai` to switch backends.
- Inside `call_llm`, branch on this variable — each branch builds the correct request shape and base URL.
- Open Code Bridge typically exposes an OpenAI-compatible API endpoint. Test by pointing the OpenAI base URL at the bridge's local port.

### 7.3 Handling Tool Use Responses

When using native tool calling, the response content may be a list of blocks, not a plain string. Extend `call_llm` to return a union type or separate `call_llm_with_tools` variant — decide which pattern before writing the Orchestrator.

---

## 8. Software Architecture: Key Patterns

Applied concretely to this project — not abstract theory.

### 8.1 Dependency Injection

Every module receives its dependencies (API keys, config, model name) as constructor parameters or function arguments — never reads them from globals or environment variables directly. This makes each module independently testable.

**Getting started:**
- Create a `Config` dataclass holding all keys, model names, repo path, trusted sources. Instantiate it once at startup. Pass it into every module that needs it.
- Test: *Can you instantiate `ReferenceVerifier(config=mock_config)` in a unit test without it touching the real network or API?*

### 8.2 Adapter / Strategy Pattern

The web search module is the clearest example. Tavily, SerpAPI, and DuckDuckGo scrape are different implementations of the same interface: take a query, return a list of URLs with snippets. Define the interface first; each search provider is a separate class implementing it.

```python
from abc import ABC, abstractmethod

class SearchProvider(ABC):
    @abstractmethod
    def search(self, query: str, n: int = 5) -> list[SearchResult]:
        ...

class TavilyProvider(SearchProvider):
    def search(self, query, n=5): ...

class DDGProvider(SearchProvider):
    def search(self, query, n=5): ...
```

### 8.3 Separation of Concerns

Each module in the architecture diagram should have one job and know nothing about its siblings. The Orchestrator is the only component that talks to more than one other component. If `ResearchModule` is importing from `ReferenceVerifier`, something is wrong.

### 8.4 Error Propagation Design

Decide your error philosophy before writing module code. A mixed approach — exceptions for infrastructure failures, result objects for expected failures — is the clearest:

- **Raise exceptions for:** network down, API key invalid, file system full.
- **Return a result object for:** claim unverifiable, URL dead, source not credible. These are not errors — they're valid outcomes that affect document content.

The Orchestrator catches infrastructure exceptions, logs them, and decides whether to retry or abort.

---

## 9. Python Fundamentals to Solidify

Small gaps with outsized effect on maintainability and reliability.

### 9.1 `dataclasses`

Use dataclasses everywhere you'd otherwise use a dict for structured data. They're self-documenting, type-checkable, and work with Python's type system.

```python
from dataclasses import dataclass, field

@dataclass
class VerificationResult:
    url:       str
    live:      bool
    supported: bool
    trusted:   bool
    note:      str = ''
```

### 9.2 `logging`

A multi-step agent pipeline is very hard to debug with `print()`. Use the standard logging module from the start. Set up one logger per module.

```python
import logging
log = logging.getLogger(__name__)
log.info('State transition: RESEARCH -> VERIFY')
log.warning('URL unresponsive, marking unverified: %s', url)
```

### 9.3 `httpx` (preferred over `requests`)

`httpx` is a modern drop-in for `requests` with connection pooling and async support if you need it later.

```bash
pip install httpx
```

The API is almost identical to `requests`.

### 9.4 Environment Variable Management

Store all API keys and configuration in a `.env` file at project root. Load with `python-dotenv` at startup only — never scatter `os.getenv()` calls throughout the codebase. Pass values into the `Config` dataclass once.

```bash
# .env
ANTHROPIC_API_KEY=sk-...
GITHUB_REPO_PATH=/Users/you/tutor-docs
LLM_PROVIDER=anthropic
```

```python
from dotenv import load_dotenv
load_dotenv()
config = Config.from_env()  # reads os.environ once
```

---

*Tutor System Learning Plan — Generated June 2026*

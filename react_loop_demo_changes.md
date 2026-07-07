# react_loop_demo.py — Changes Summary

## What changed

Migrated from **text-based ReAct** (parsing `"Action:"` / `"Answer:"` from model output) to **native `tools` API** (structured `tool_use` blocks via the `tools` parameter).

## Key architectural changes

### 1. `call_llm()` abstraction added

Replaces the inline `requests.post()` call. Takes `messages`, `tools`, and `provider`. Returns a **unified type** — the orchestrator never branches on provider:

```python
# Text response (no tool call):
{"type": "text", "content": "The time is...", "tool_calls": []}

# Tool call response:
{"type": "tool_use", "content": "Let me check...", "tool_calls": [
    {"id": "call_abc", "name": "get_current_time", "args": {}}
]}
```

Provider-specific parsing lives **inside** `call_llm()` only.

### 2. Tool definitions moved out of system prompt

| Before | After |
|--------|-------|
| `TOOLS` dict (name → callable) | `TOOL_DEFINITIONS` list (JSON Schema) + `TOOL_REGISTRY` dict (name → callable) |
| Tools described as text in `SYSTEM` prompt | Tools passed via native `tools` API parameter |
| Model returned free-text `"Action: {...}"` | Model returns structured `tool_calls` array |

### 3. `content: null` rule applied

When the model returns `tool_calls`, the assistant message **must** have `content: None`. Done here:

```python
assistant_msg = {
    "role": "assistant",
    "content": None,
    "tool_calls": [...]
}
```

### 4. Tool results use structured `role: "tool"`

Instead of injecting `"Observation: ..."` as a user message:

```python
{"role": "tool", "tool_call_id": "call_abc", "content": "2026-07-05 14:30:00"}
```

The `tool_call_id` links each result back to the specific call that produced it (important for parallel tool calls).

### 5. Multiple tool calls per turn supported

The loop iterates `response["tool_calls"]` — handles multiple parallel tool calls in one response.

### 6. Provider stubs for future expansion

```python
PROVIDERS = {
    "opencode": { "url": "...", "api_key": API_KEY },
    "openai": None,     # stub
    "anthropic": None,  # stub
}
```

Adding a new provider means implementing its request/response format inside `call_llm()` — the orchestrator loop stays unchanged.

## Things to note for later

- **Tool choice**: Currently hardcoded to `"auto"`. Could expose as a parameter later.
- **Anthropic format**: Has a different response structure (`content` as array of blocks with `type: "text"` / `type: "tool_use"`). Would need a dedicated parser branch in `call_llm()`.
- **Error handling**: No retries, no HTTP error handling. Bare minimum for a demo.
- **`tool_choice`**: Not exposed yet. Only `"auto"` is used. `"any"` and `"none"` could be useful for forcing/blocking tool use.

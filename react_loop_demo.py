#!/usr/bin/env python3
"""Minimal ReAct loop — DeepSeek V4 Flash, native tools API, orchestrated loop."""
import os, json, datetime, requests

API_KEY = os.environ.get("OPENCODE_API_KEY")
if not API_KEY: raise SystemExit("Set OPENCODE_API_KEY")
MODEL = "deepseek-v4-flash"


def get_current_time(**kw) -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── Tool definitions (schemas) and registry ──
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current date and time",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOL_REGISTRY = {"get_current_time": get_current_time}


# ── Provider configuration ──
PROVIDERS = {
    "opencode": {
        "url": "https://opencode.ai/zen/go/v1/chat/completions",
        "api_key": API_KEY,
    },
    "openai": None,     # stub
    "anthropic": None,  # stub
}


def call_llm(messages: list, tools: list, provider: str = "opencode") -> dict:
    """Call an LLM and return a unified response.

    Returns:
        {"type": "text", "content": str, "tool_calls": []}
        or
        {"type": "tool_use", "content": str | None, "tool_calls": [...]}
    """
    config = PROVIDERS.get(provider)
    if not config:
        raise NotImplementedError(f"Provider '{provider}' not yet supported")

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    http_resp = requests.post(
        config["url"],
        json=payload,
        headers={"Authorization": f"Bearer {config['api_key']}"},
    )
    data = http_resp.json()

    # Parse OpenAI-compatible response into unified format
    choice = data["choices"][0]
    msg = choice["message"]
    content = msg.get("content")
    raw_calls = msg.get("tool_calls", [])

    if raw_calls:
        tool_calls = [
            {
                "id": tc["id"],
                "name": tc["function"]["name"],
                "args": json.loads(tc["function"]["arguments"]),
            }
            for tc in raw_calls
        ]
        return {"type": "tool_use", "content": content, "tool_calls": tool_calls}
    else:
        return {"type": "text", "content": content, "tool_calls": []}


# ── Orchestrator loop ──
messages = [
    {"role": "system", "content": "You are a helpful assistant. Use the available tools to answer the user's question."},
    {"role": "user", "content": "What time is it?"},
]

for step in range(10):
    response = call_llm(messages, TOOL_DEFINITIONS, "opencode")

    print(f"\n{'='*60}")
    print(f"  Step {step}")
    print(f"  {'─'*56}")

    if response["type"] == "text":
        print(f"\n  Answer:\n  │ {response['content']}")
        messages.append({"role": "assistant", "content": response["content"]})
        print("\n✓ Done.")
        break

    # ── Handle tool_use ──
    print(f"\n  Reasoning: {response['content']}")

    # Append assistant msg with content=None (required when tool_calls exist)
    assistant_msg = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": json.dumps(tc["args"]),
                },
            }
            for tc in response["tool_calls"]
        ],
    }
    messages.append(assistant_msg)

    for tc in response["tool_calls"]:
        print(f"  → Tool call: {tc['name']}({json.dumps(tc['args'])})")
        result = TOOL_REGISTRY[tc["name"]](**tc["args"])
        print(f"    Result: {result}")

        messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": str(result),
        })
else:
    print("\nMax steps reached without final answer.")

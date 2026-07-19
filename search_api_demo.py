"""
Demonstration: Search API response formats & realities

Shows:
1. What search APIs actually return
2. Snippet sizes measured in chars
3. How results differ across query types
4. Comparison table: which APIs need keys, format differences
"""

import json

# ─────────────────────────────────────────────────────────────
# First try ddgs (the current package name)
# ─────────────────────────────────────────────────────────────

print("=" * 70)
print("DEMO 1: Raw search results using ddgs (DuckDuckGo, no API key)")
print("=" * 70)

try:
    from ddgs import DDGS
    ENGINE = "ddgs"
except ImportError:
    from duckduckgo_search import DDGS
    ENGINE = "duckduckgo_search"

queries = [
    "Python descriptor protocol __get__ __set__",
    "merge sort algorithm time complexity",
    "how does a transistor work",
]

results_by_query = {}

for query in queries:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        results_by_query[query] = results

        print(f"\n{'─' * 70}")
        print(f"Query: \"{query}\"")
        print(f"Results returned: {len(results)}")

        for i, r in enumerate(results):
            body = r.get("body", "")
            print(f"\n  Result {i+1}:")
            print(f"    title:   {r.get('title', 'N/A')[:100]}")
            print(f"    href:    {r.get('href', 'N/A')[:80]}")
            print(f"    body:    \"{body[:150]}{'...' if len(body) > 150 else ''}\"")
            print(f"    snippet_length: {len(body)} chars (~{len(body)//4} tokens)")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        results_by_query[query] = []


# ─────────────────────────────────────────────────────────────
# DEMO 2: Snippet size distribution
# ─────────────────────────────────────────────────────────────

print("\n\n" + "=" * 70)
print("DEMO 2: Snippet size distribution")
print("=" * 70)

for query, results in results_by_query.items():
    if not results:
        print(f"\nQuery: \"{query}\" → no results (likely rate limited)")
        continue

    bodies = [r.get("body", "") for r in results]
    sizes = [len(b) for b in bodies]

    print(f"\nQuery: \"{query}\"")
    print(f"  Individual snippets: {sizes} chars")
    print(f"  Min: {min(sizes)}, Max: {max(sizes)}, Avg: {sum(sizes)//len(sizes)}")
    print(f"  Total across {len(results)} results: {sum(sizes)} chars ({sum(sizes)//4} tokens)")


# ─────────────────────────────────────────────────────────────
# DEMO 3: Keys that are always vs. sometimes present
# ─────────────────────────────────────────────────────────────

print("\n\n" + "=" * 70)
print("DEMO 3: Key presence analysis")
print("=" * 70)

all_results = [r for results in results_by_query.values() for r in results]

if all_results:
    all_keys = set()
    for r in all_results:
        all_keys.update(k for k in r.keys() if r[k] is not None)

    always_present = set(all_keys)
    for r in all_results:
        for k in list(always_present):
            if k not in r or r[k] is None:
                always_present.discard(k)

    optional = all_keys - always_present

    print(f"  Always present: {sorted(always_present)}")
    print(f"  Sometimes missing/None: {sorted(optional)}")
else:
    print("  No results to analyze (rate limited)")


# ─────────────────────────────────────────────────────────────
# COMPARISON TABLE
# ─────────────────────────────────────────────────────────────

print("""

======================================================================
COMPARISON: Major search API landscape
======================================================================

┌─────────────────┬──────────┬──────────────────────┬──────────────┐
│ Provider         │ API Key? │ Snippet Size         │ Notes         │
├─────────────────┼──────────┼──────────────────────┼──────────────┤
│ DuckDuckGo       │ NO       │ ~150-350 chars       │ Free, scrapes │
│ (ddgs library)   │          │ (variable)           │ HTML results.  │
│                  │          │                      │ May rate-limit │
├─────────────────┼──────────┼──────────────────────┼──────────────┤
│ Tavily           │ YES      │ ~150-300 chars       │ Purpose-built │
│                  │ (free    │ (internally capped)  │ for LLM/RAG.  │
│                  │  tier)   │                      │ Cleanest JSON. │
├─────────────────┼──────────┼──────────────────────┼──────────────┤
│ SerpAPI          │ YES      │ ~150-300 chars       │ Wraps Google. │
│                  │ (paid)   │ (Google's snippet)   │ Deeply nested. │
├─────────────────┼──────────┼──────────────────────┼──────────────┤
│ Brave Search     │ YES      │ ~150-300 chars       │ Clean JSON.   │
│                  │ (free    │ (Brave internal)     │ 2K queries/mo │
│                  │  tier)   │                      │ free.         │
├─────────────────┼──────────┼──────────────────────┼──────────────┤
│ Google CSE       │ YES      │ ~160 chars           │ Needs CSE ID  │
│                  │ (free    │ (hard Google cap)    │ + API key.    │
│                  │  tier)   │                      │ 100 queries/d │
└─────────────────┴──────────┴──────────────────────┴──────────────┘

KEY TAKEAWAYS

  1. SNIPPETS ARE UNIVERSALLY SMALL.
     Every provider, without exception, caps snippets at 150-350 chars.
     Nobody returns full article text from a search call — that's what
     fetch_page is for. A search result is a catalog entry, not a book.

     With n=5 results: total is ~1,500 chars (~375 tokens).
     With n=10 results: total is ~3,000 chars (~750 tokens).
     This is NOT what fills your orchestrator's context window.

  2. FORMATS ARE NOT UNIFORM.
     Every API returns a different JSON shape with different key names:
     - Tavily:    {results: [{url, title, content}]}
     - SerpAPI:   {organic_results: [{link, title, snippet}]}
     - Brave:     {web: {results: [{url, title, description}]}}
     - DDG/ddgs:  [{href, title, body}]
     - Google CSE: {items: [{link, title, snippet}]}

     This is WHY your search_web tool must normalize these to ONE
     internal format before returning to the orchestrator. The
     orchestrator prompt should only know about:
       {results: [{url, title, snippet}]}

  3. YOU NEED AN API KEY FOR EVERYTHING EXCEPT DUCKDUCKGO.
     For your real project, get a Tavily free tier key (1000 calls/mo).
     It's purpose-built for RAG and returns the cleanest JSON of any
     search API. The DuckDuckGo library works for demos but can be
     flaky under load and has no SLA.

  4. THE REAL CONTEXT THREAT IS fetch_page, NOT search_web.
     The full article text from fetching a single URL is 5-50KB
     (1,250-12,500 tokens). That's 10-100x bigger than all search
     snippets combined. Your file-reference architecture from earlier
     is the right solution for that problem.

======================================================================
""")

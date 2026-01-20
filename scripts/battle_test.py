"""
Battle Test Script for Agent A

Runs a series of test queries and outputs results to markdown.
"""

import asyncio
import httpx
import json
import sys
import os
from datetime import datetime

# Windows asyncio compatibility handled by default in Python 3.14+

# Configuration
API_URL = "https://claude-code-dev.fly.dev"
API_KEY = os.environ.get("API_KEY", "your-api-key-for-authentication")
ORG_ID = "00000000-0000-0000-0000-000000000001"

# Battle test queries
QUERIES = [
    # Category 1: Factual Recall
    ("Factual", "What does Lean Labs do?"),
    ("Factual", "What services does Lean Labs offer?"),
    ("Factual", "Who is Lean Labs' target audience?"),

    # Category 2: Specificity
    ("Specificity", "What is Lean Labs' pricing?"),
    ("Specificity", "How much does Lean Labs charge per month?"),
    ("Specificity", "What results have Lean Labs clients achieved?"),
    ("Specificity", "How long does Lean Labs onboarding take?"),

    # Category 3: Comparison & Reasoning
    ("Reasoning", "What's the difference between Lean Labs plans?"),
    ("Reasoning", "How is Lean Labs different from other agencies?"),
    ("Reasoning", "What makes Lean Labs' approach unique?"),

    # Category 4: Process
    ("Process", "How do I get started with Lean Labs?"),
    ("Process", "What is Lean Labs' methodology?"),
    ("Process", "What happens after I sign up with Lean Labs?"),

    # Category 5: Edge Cases
    ("Edge Case", "Does Lean Labs offer refunds?"),
    ("Edge Case", "What is Lean Labs' phone number?"),
    ("Edge Case", "Tell me about quantum computing"),

    # Category 6: Ambiguous
    ("Ambiguous", "Is Lean Labs worth it?"),
    ("Ambiguous", "What does Lean Labs do for SEO?"),

    # Category 7: Consistency (similar questions)
    ("Consistency", "What is Lean Labs' price?"),
    ("Consistency", "How much does Lean Labs charge?"),

    # Category 8: Stress
    ("Stress", "Give me all details about Lean Labs services and pricing"),
    ("Stress", "Hi"),
    ("Stress", "Thanks!"),
]


async def run_query(client: httpx.AsyncClient, query: str) -> dict:
    """Run a single query and return result."""
    start_time = datetime.now()

    try:
        response_text = ""
        metadata = {}

        async with client.stream(
            "POST",
            f"{API_URL}/chat/stream",
            headers={"X-API-Key": API_KEY},
            json={"message": query, "org_id": ORG_ID},
            timeout=60.0,
        ) as response:
            if response.status_code != 200:
                error = await response.aread()
                return {
                    "query": query,
                    "response": f"ERROR {response.status_code}: {error.decode()[:200]}",
                    "duration_ms": 0,
                    "status": "error",
                }

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        if data.get("type") == "answer":
                            response_text = data.get("data", "")
                            metadata = data.get("metadata", {})
                    except json.JSONDecodeError:
                        pass

        duration_ms = metadata.get("duration_ms", (datetime.now() - start_time).total_seconds() * 1000)

        return {
            "query": query,
            "response": response_text,
            "duration_ms": round(duration_ms),
            "status": "success",
        }

    except Exception as e:
        return {
            "query": query,
            "response": f"ERROR: {str(e)}",
            "duration_ms": 0,
            "status": "error",
        }


async def run_battle_test():
    """Run all battle test queries."""
    results = []

    async with httpx.AsyncClient() as client:
        print(f"Running {len(QUERIES)} battle test queries...\n")

        for i, (category, query) in enumerate(QUERIES, 1):
            print(f"[{i}/{len(QUERIES)}] {category}: {query[:40]}...")
            result = await run_query(client, query)
            result["category"] = category
            result["index"] = i
            results.append(result)

            status = "OK" if result["status"] == "success" else "FAIL"
            print(f"       [{status}] {result['duration_ms']}ms\n")

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)

    return results


def generate_markdown(results: list) -> str:
    """Generate markdown report from results."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Calculate stats
    successful = [r for r in results if r["status"] == "success"]
    times = [r["duration_ms"] for r in successful if r["duration_ms"] > 0]
    avg_time = sum(times) / len(times) if times else 0
    min_time = min(times) if times else 0
    max_time = max(times) if times else 0

    md = f"""# Agent A Battle Test Results

**Date:** {now}
**API:** {API_URL}
**Total Queries:** {len(results)}
**Successful:** {len(successful)}/{len(results)}

## Performance Summary

| Metric | Value |
|--------|-------|
| Average Response Time | {avg_time:.0f}ms |
| Fastest | {min_time}ms |
| Slowest | {max_time}ms |
| Success Rate | {len(successful)/len(results)*100:.0f}% |

---

## Detailed Results

"""

    # Group by category
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r)

    for category, cat_results in categories.items():
        md += f"### {category}\n\n"

        for r in cat_results:
            status = "✅" if r["status"] == "success" else "❌"
            md += f"#### {r['index']}. {r['query']}\n\n"
            md += f"**Status:** {status} | **Time:** {r['duration_ms']}ms\n\n"

            md += f"**Response:**\n\n{r['response']}\n\n"
            md += "---\n\n"

    # Summary table
    md += """## Quick Reference Table

| # | Category | Query | Time | Status |
|---|----------|-------|------|--------|
"""
    for r in results:
        status = "✅" if r["status"] == "success" else "❌"
        query_short = r["query"][:35] + "..." if len(r["query"]) > 35 else r["query"]
        md += f"| {r['index']} | {r['category']} | {query_short} | {r['duration_ms']}ms | {status} |\n"

    return md


async def main():
    print("=" * 50)
    print("Agent A Battle Test")
    print("=" * 50 + "\n")

    results = await run_battle_test()

    # Generate markdown
    markdown = generate_markdown(results)

    # Save to file
    output_file = "battle_test_results.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\n{'=' * 50}")
    print(f"Results saved to: {output_file}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    asyncio.run(main())

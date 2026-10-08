"""Test script to verify local Ollama LLM and benchmark response times."""

import json
import time

import httpx


def test_ollama_questions():
    client = httpx.Client(base_url="http://127.0.0.1:11434", timeout=30.0)
    model = "qwen2.5:1.5b"

    print("=" * 70)
    print(f" BENCHMARKING OLLAMA MODEL: {model}")
    print("=" * 70)

    # Question 1: General reasoning
    q1 = "Explain why high inflation causes price-seeking behavior in households in 2 concise sentences."
    print(f'\n[Test 1] Query: "{q1}"')
    t0 = time.perf_counter()
    resp1 = client.post(
        "/api/generate",
        json={"model": model, "prompt": q1, "stream": False},
    )
    t1 = time.perf_counter()
    res1_json = resp1.json()
    duration1 = t1 - t0
    eval_count1 = res1_json.get("eval_count", 0)
    eval_duration1_ns = res1_json.get("eval_duration", 1)
    tok_per_sec1 = eval_count1 / (eval_duration1_ns / 1e9) if eval_duration1_ns else 0

    print(f"Response: {res1_json.get('response', '').strip()}")
    print(
        f"Latency:  {duration1:.3f}s | Tokens: {eval_count1} | Speed: {tok_per_sec1:.1f} tokens/sec"
    )

    # Question 2: Structured JSON strategic decision (Phase 7 simulation scenario)
    q2 = (
        "You are the Mayor of a simulation city. Food prices rose by 15% and unrest is 0.20. "
        "Choose an action from ['FOOD_SUBSIDY', 'AUSTERITY', 'PUBLIC_WORKS', 'NO_ACTION']. "
        'Return ONLY valid JSON in format: {"action": "<choice>", "confidence": <float 0-1>, "rationale": "<reason>"}.'
    )
    print("\n[Test 2] Query: Structured JSON Decision Proposal")
    t2 = time.perf_counter()
    resp2 = client.post(
        "/api/generate",
        json={
            "model": model,
            "prompt": q2,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        },
    )
    t3 = time.perf_counter()
    res2_json = resp2.json()
    duration2 = t3 - t2
    eval_count2 = res2_json.get("eval_count", 0)
    eval_duration2_ns = res2_json.get("eval_duration", 1)
    tok_per_sec2 = eval_count2 / (eval_duration2_ns / 1e9) if eval_duration2_ns else 0

    raw_resp2 = res2_json.get("response", "").strip()
    print(f"Response JSON: {raw_resp2}")
    parsed = None
    try:
        parsed = json.loads(raw_resp2)
        print(
            f"Parsed Successfully: action={parsed.get('action')}, confidence={parsed.get('confidence')}"
        )
    except (json.JSONDecodeError, ValueError) as e:
        print(f"JSON Parsing Error: {e}")

    print(
        f"Latency:  {duration2:.3f}s | Tokens: {eval_count2} | Speed: {tok_per_sec2:.1f} tokens/sec"
    )
    print("=" * 70)


if __name__ == "__main__":
    test_ollama_questions()

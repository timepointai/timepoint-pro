#!/usr/bin/env python3
"""
Stairstep Load Testing for Paid Mode

Tests LLM tensor population with gradually increasing parallelism:
1. Start with 1 concurrent call
2. Monitor success rate (target >= 95%)
3. If stable, increase concurrency
4. If failures occur, back off
5. Find maximum stable throughput

Usage:
    # Test FREE mode (baseline)
    python test_paid_mode_stairstep.py --mode free

    # Test PAID mode (aggressive)
    python test_paid_mode_stairstep.py --mode paid

    # Start at specific concurrency level
    python test_paid_mode_stairstep.py --mode paid --start-level 5
"""

import os
import sys
import time
import argparse
import concurrent.futures
from typing import List, Tuple
from datetime import datetime
import json
from pathlib import Path

from llm import LLMClient, RateLimiter
from schemas import Entity
from tensor_initialization import _extract_json_from_response

def create_test_entity(entity_id: str) -> Entity:
    """Create a minimal test entity for load testing."""
    return Entity(
        entity_id=entity_id,
        entity_type="human",
        role="test",
        description=f"Test entity {entity_id} for load testing",
        background="",
        entity_metadata={}
    )

def test_llm_call(llm_client: LLMClient, entity_id: str) -> Tuple[bool, float, str]:
    """
    Make a single LLM call and return (success, duration, error_msg).

    Returns:
        (success, duration_seconds, error_message)
    """
    start_time = time.time()

    try:
        # Simple test prompt similar to tensor population
        prompt = f"""Analyze entity "{entity_id}" and return JSON.

Expected format:
{{"context_adjustments": [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]}}

IMPORTANT: Return ONLY valid JSON, no explanation."""

        response = llm_client.client.chat.completions.create(
            model=llm_client.default_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )

        content = response["choices"][0]["message"]["content"]

        # Try to extract and parse JSON
        json_content = _extract_json_from_response(content)
        parsed = json.loads(json_content)

        duration = time.time() - start_time
        return (True, duration, "")

    except Exception as e:
        duration = time.time() - start_time
        return (False, duration, str(e))

def run_concurrency_level(
    llm_client: LLMClient,
    concurrency: int,
    num_calls: int = 10
) -> Tuple[int, int, float, List[float]]:
    """
    Run a batch of calls at specific concurrency level.

    Returns:
        (successes, failures, avg_duration, durations)
    """
    print(f"\n{'='*60}")
    print(f"Testing concurrency level: {concurrency}")
    print(f"Total calls: {num_calls}")
    print(f"{'='*60}")

    successes = 0
    failures = 0
    durations = []
    errors = []

    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(num_calls):
            future = executor.submit(test_llm_call, llm_client, f"test_entity_{i}")
            futures.append(future)

        # Collect results as they complete
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            success, duration, error = future.result()
            durations.append(duration)

            if success:
                successes += 1
                print(f"  ✅ Call {i+1}/{num_calls}: {duration:.2f}s")
            else:
                failures += 1
                errors.append(error)
                print(f"  ❌ Call {i+1}/{num_calls}: FAILED after {duration:.2f}s")
                print(f"     Error: {error[:100]}")

    elapsed = time.time() - start_time
    success_rate = (successes / num_calls) * 100
    avg_duration = sum(durations) / len(durations) if durations else 0
    throughput = num_calls / elapsed

    print(f"\n📊 Results:")
    print(f"   Successes: {successes}/{num_calls} ({success_rate:.1f}%)")
    print(f"   Failures: {failures}")
    print(f"   Avg duration: {avg_duration:.2f}s")
    print(f"   Total time: {elapsed:.2f}s")
    print(f"   Throughput: {throughput:.2f} calls/sec")

    if errors:
        unique_errors = set(errors)
        print(f"\n⚠️  Error types:")
        for error in unique_errors:
            count = errors.count(error)
            print(f"     - {error[:80]} ({count}x)")

    return (successes, failures, avg_duration, durations)

def main():
    parser = argparse.ArgumentParser(description="Stairstep load testing for paid mode")
    parser.add_argument(
        "--mode",
        choices=["free", "paid"],
        default="paid",
        help="Rate limit mode (free or paid, DEFAULT: paid)"
    )
    parser.add_argument(
        "--start-level",
        type=int,
        default=1,
        help="Starting concurrency level"
    )
    parser.add_argument(
        "--max-level",
        type=int,
        default=20,
        help="Maximum concurrency level to test"
    )
    parser.add_argument(
        "--calls-per-level",
        type=int,
        default=10,
        help="Number of calls to test at each level"
    )
    parser.add_argument(
        "--success-threshold",
        type=float,
        default=0.95,
        help="Success rate threshold to advance (0.95 = 95%%)"
    )

    args = parser.parse_args()

    # Check API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ No OPENROUTER_API_KEY found")
        sys.exit(1)

    # Set rate limits based on mode
    if args.mode == "paid":
        max_rpm = 1000  # Aggressive for paid tier
        burst = 50
    else:
        max_rpm = 20  # Conservative for free tier
        burst = 5

    print("=" * 80)
    print(f"🚀 STAIRSTEP LOAD TEST - {args.mode.upper()} MODE")
    print("=" * 80)
    print(f"Mode: {args.mode}")
    print(f"Rate limits: {max_rpm} req/min, burst {burst}")
    print(f"Concurrency range: {args.start_level} → {args.max_level}")
    print(f"Calls per level: {args.calls_per_level}")
    print(f"Success threshold: {args.success_threshold * 100}%")
    print("=" * 80)

    # Create LLM client with specified mode
    llm_client = LLMClient(
        api_key=api_key,
        mode=args.mode,
        max_requests_per_minute=max_rpm,
        burst_size=burst
    )

    # Track results
    results = []
    current_level = args.start_level
    max_stable_level = 1

    while current_level <= args.max_level:
        successes, failures, avg_duration, durations = run_concurrency_level(
            llm_client,
            concurrency=current_level,
            num_calls=args.calls_per_level
        )

        success_rate = successes / args.calls_per_level

        results.append({
            "concurrency": current_level,
            "successes": successes,
            "failures": failures,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "mode": args.mode
        })

        # Decision: advance or stop
        if success_rate >= args.success_threshold:
            print(f"\n✅ Level {current_level}: STABLE ({success_rate*100:.1f}% success)")
            max_stable_level = current_level

            # Advance to next level (increment by 1 for paid, more conservative for free)
            if args.mode == "paid":
                current_level += 2  # Faster ramp for paid
            else:
                current_level += 1  # Slower ramp for free
        else:
            print(f"\n❌ Level {current_level}: UNSTABLE ({success_rate*100:.1f}% success)")
            print(f"   Max stable level found: {max_stable_level}")
            break

        # Short pause between levels
        time.sleep(2)

    # Summary
    print("\n" + "=" * 80)
    print(f"📈 LOAD TEST SUMMARY - {args.mode.upper()} MODE")
    print("=" * 80)
    print(f"Maximum stable concurrency: {max_stable_level}")
    print(f"\nResults by concurrency level:")
    for r in results:
        status = "✅" if r["success_rate"] >= args.success_threshold else "❌"
        print(f"  {status} Level {r['concurrency']:2d}: {r['success_rate']*100:5.1f}% success, {r['avg_duration']:.2f}s avg")

    # Save results
    log_file = Path(f"logs/load_test_{args.mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    log_file.parent.mkdir(exist_ok=True)
    with open(log_file, "w") as f:
        json.dump({
            "mode": args.mode,
            "max_stable_level": max_stable_level,
            "results": results,
            "config": {
                "max_rpm": max_rpm,
                "burst": burst,
                "success_threshold": args.success_threshold
            }
        }, f, indent=2)

    print(f"\n📄 Results saved to: {log_file}")
    print("=" * 80)

    return max_stable_level

if __name__ == "__main__":
    max_level = main()
    sys.exit(0 if max_level > 1 else 1)

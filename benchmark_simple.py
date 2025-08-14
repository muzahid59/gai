#!/usr/bin/env python3
"""
Simple benchmark comparing OpenAI GPT-3.5 vs GPT-4 performance.
"""

import time
import json
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gai.openai_client import OpenAIProvider
from gai.utils import get_staged_diff, is_git_repository


def benchmark_openai_models():
    """Benchmark GPT-3.5 vs GPT-4 performance."""

    # Load environment
    load_dotenv()

    # Check if we're in a git repository
    if not is_git_repository():
        print(
            "❌ Not in a git repository. Please run from a git repository with staged changes."
        )
        sys.exit(1)

    # Get staged diff
    staged_diff = get_staged_diff()
    if not staged_diff:
        print(
            "❌ No staged changes found. Please stage some changes with 'git add' first."
        )
        sys.exit(1)

    print(f"📄 Diff size: {len(staged_diff)} characters")
    print(f"📄 Diff lines: {len(staged_diff.splitlines())} lines")
    print("\n" + "=" * 60)

    # Models to test
    models = ["gpt-3.5-turbo", "gpt-4o", "gpt-4o-mini", "o3"]
    results = []

    for model in models:
        print(f"\n🤖 Testing {model}...")
        print("-" * 40)

        # Initialize provider
        provider = OpenAIProvider(model=model)

        # Run 3 iterations for each model
        model_results = []

        for iteration in range(3):
            print(f"  Iteration {iteration + 1}/3...", end=" ")

            # Measure time
            start_time = time.time()

            try:
                commit_message = provider.generate_commit_message(staged_diff)
                end_time = time.time()

                response_time = end_time - start_time
                message_length = len(commit_message)

                model_results.append(
                    {
                        "model": model,
                        "iteration": iteration + 1,
                        "response_time": response_time,
                        "message_length": message_length,
                        "message": commit_message.strip(),
                        "success": True,
                    }
                )

                print(f"✅ {response_time:.2f}s")

            except Exception as e:
                print(f"❌ Error: {e}")
                model_results.append(
                    {
                        "model": model,
                        "iteration": iteration + 1,
                        "response_time": None,
                        "message_length": 0,
                        "message": "",
                        "success": False,
                        "error": str(e),
                    }
                )

            # Small delay between requests
            time.sleep(1)

        results.extend(model_results)

        # Show results for this model
        successful_runs = [r for r in model_results if r["success"]]
        if successful_runs:
            avg_time = sum(r["response_time"] for r in successful_runs) / len(
                successful_runs
            )
            avg_length = sum(r["message_length"] for r in successful_runs) / len(
                successful_runs
            )

            print(f"\n  📊 {model} Summary:")
            print(f"    Average response time: {avg_time:.2f}s")
            print(f"    Average message length: {avg_length:.0f} characters")
            print(f"    Success rate: {len(successful_runs)}/3")

            # Show sample message
            print(f"\n  📝 Sample message:")
            sample_message = successful_runs[0]["message"]
            # Truncate if too long
            if len(sample_message) > 200:
                sample_message = sample_message[:200] + "..."
            print(f"    {sample_message}")
        else:
            print(f"  ❌ All attempts failed for {model}")

    # Generate comparison report
    print("\n" + "=" * 60)
    print("📈 COMPARISON RESULTS")
    print("=" * 60)

    # Filter successful results
    successful_results = [r for r in results if r["success"]]

    if not successful_results:
        print("❌ No successful results to compare")
        return

    # Group by model
    gpt35_results = [r for r in successful_results if r["model"] == "gpt-3.5-turbo"]
    gpt4o_results = [r for r in successful_results if r["model"] == "gpt-4o"]
    gpt4o_mini_results = [r for r in successful_results if r["model"] == "gpt-4o-mini"]
    o3_results = [r for r in successful_results if r["model"] == "o3"]

    # Calculate averages for each model
    model_stats = {}
    for model_name, model_results in [
        ("gpt-3.5-turbo", gpt35_results),
        ("gpt-4o", gpt4o_results),
        ("gpt-4o-mini", gpt4o_mini_results),
        ("o3", o3_results),
    ]:
        if model_results:
            model_stats[model_name] = {
                "avg_time": sum(r["response_time"] for r in model_results)
                / len(model_results),
                "avg_length": sum(r["message_length"] for r in model_results)
                / len(model_results),
                "count": len(model_results),
            }

    if len(model_stats) >= 2:
        print(f"\n⚡ Speed Comparison:")
        sorted_by_speed = sorted(model_stats.items(), key=lambda x: x[1]["avg_time"])

        for i, (model, stats) in enumerate(sorted_by_speed):
            if i == 0:
                print(f"  🏆 {model}: {stats['avg_time']:.2f}s (fastest)")
            else:
                slowdown = stats["avg_time"] / sorted_by_speed[0][1]["avg_time"]
                print(
                    f"  {i+1}. {model}: {stats['avg_time']:.2f}s ({slowdown:.1f}x slower)"
                )

        print(f"\n📏 Message Length Comparison:")
        sorted_by_length = sorted(
            model_stats.items(), key=lambda x: x[1]["avg_length"], reverse=True
        )

        for i, (model, stats) in enumerate(sorted_by_length):
            if i == 0:
                print(f"  📝 {model}: {stats['avg_length']:.0f} chars (most detailed)")
            else:
                print(f"  {i+1}. {model}: {stats['avg_length']:.0f} chars")

        # Updated cost estimation with current pricing
        # Approximate pricing (as of 2024):
        # GPT-3.5-turbo: $0.0005/1K input tokens, $0.0015/1K output tokens
        # GPT-4o: $0.0025/1K input tokens, $0.01/1K output tokens
        # GPT-4o-mini: $0.00015/1K input tokens, $0.0006/1K output tokens
        # o3: $0.06/1K input tokens, $0.24/1K output tokens (premium reasoning model)

        pricing = {
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-4o": {"input": 0.0025, "output": 0.01},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "o3": {"input": 0.06, "output": 0.24},
        }

        estimated_input_tokens = len(staged_diff) // 4
        estimated_output_tokens = 50

        print(f"\n💰 Estimated Cost per Request:")
        cost_comparison = []

        for model in model_stats.keys():
            if model in pricing:
                cost = (
                    estimated_input_tokens * pricing[model]["input"]
                    + estimated_output_tokens * pricing[model]["output"]
                ) / 1000
                cost_comparison.append((model, cost))
                print(f"  {model}: ~${cost:.4f}")

        if len(cost_comparison) >= 2:
            cheapest = min(cost_comparison, key=lambda x: x[1])
            most_expensive = max(cost_comparison, key=lambda x: x[1])
            ratio = most_expensive[1] / cheapest[1]
            print(
                f"  💡 {most_expensive[0]} is {ratio:.0f}x more expensive than {cheapest[0]}"
            )

    # Save detailed results
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = f"benchmark_results_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "diff_size": len(staged_diff),
                "diff_lines": len(staged_diff.splitlines()),
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\n💾 Detailed results saved to: {results_file}")

    # Updated recommendations for all 4 models
    print(f"\n💡 RECOMMENDATIONS:")
    if len(model_stats) >= 2:
        fastest_model = min(model_stats.items(), key=lambda x: x[1]["avg_time"])
        cheapest_model = (
            min(cost_comparison, key=lambda x: x[1]) if cost_comparison else None
        )
        most_detailed = max(model_stats.items(), key=lambda x: x[1]["avg_length"])

        print(
            f"  • ⚡ Fastest: {fastest_model[0]} ({fastest_model[1]['avg_time']:.2f}s)"
        )
        if cheapest_model:
            print(
                f"  • 💰 Most cost-effective: {cheapest_model[0]} (~${cheapest_model[1]:.4f})"
            )
        print(
            f"  • 📝 Most detailed: {most_detailed[0]} ({most_detailed[1]['avg_length']:.0f} chars)"
        )
        print(
            f"  • 🎯 For daily use: gpt-4o-mini (good balance of speed, cost, quality)"
        )
        print(f"  • 🧠 For complex reasoning: o3 (premium model for difficult commits)")
        print(f"  • ⚖️ For balanced performance: gpt-4o (good quality, reasonable cost)")


if __name__ == "__main__":
    print("🚀 OpenAI Model Benchmark (GPT-3.5 vs GPT-4)")
    print("=" * 60)

    # Check API key
    load_dotenv()
    if not os.getenv("OPEN_AI_API_KEY"):
        print("❌ API_KEY not found in .env file")
        sys.exit(1)

    benchmark_openai_models()

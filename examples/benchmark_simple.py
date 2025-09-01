#!/usr/bin/env python3
"""
Simple benchmark comparing OpenAI models performance.

Adds automatic fallback to a synthetic demo diff when:
- Not in a git repo
- No staged changes found
- --force-sample flag supplied
"""

import time
import json
import sys
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to Python path (project root assumed one level up)
root_dir = Path(__file__).parent.parent
src_dir = root_dir / "src"
sys.path.insert(0, str(src_dir))

from gai.openai_client import OpenAIProvider
from gai.utils import get_staged_diff, is_git_repository
from gai.cli import load_config


DEMO_DIFF = """--- a/src/example/math.py
+++ b/src/example/math.py
@@ -1,6 +1,17 @@
-def add(a, b):
-    return a+b
+def add(a: int, b: int) -> int:
+    \"\"\"Add two integers with validation.\"\"\"
+    if a is None or b is None:
+        raise ValueError("Inputs cannot be None")
+    return a + b
 
-def mul(a, b):
-    return a*b
+def mul(a: int, b: int) -> int:
+    \"\"\"Multiply two integers.\"\"\"
+    return a * b
+
+def div(a: int, b: int) -> float:
+    \"\"\"Safe division that avoids ZeroDivisionError.\"\"\"
+    if b == 0:
+        return 0.0
+    return a / b
+
+PI = 3.14159
 
--- a/README.md
+++ b/README.md
@@ -10,6 +10,12 @@ Features
 - Fast
 - Simple
 
+New Additions
+-------------
+- Safer math helpers
+- Type hints
+- Division support
+
--- a/src/example/__init__.py
+++ b/src/example/__init__.py
@@ -1,2 +1,5 @@
-__all__ = ["add", "mul"]
+__all__ = ["add", "mul", "div", "PI"]
+
+VERSION = "0.2.0"
+
+# Updated exports for new functionality
"""


def _resolve_diff(args) -> tuple[str, bool]:
    """Return a diff string and whether it's a demo."""
    if args.force_sample:
        print("💡 Using demo diff (forced).")
        return DEMO_DIFF, True

    if not is_git_repository():
        print("⚠️  Not a git repo: falling back to demo diff.")
        return DEMO_DIFF, True

    diff = get_staged_diff()
    if not diff.strip():
        print("⚠️  No staged changes: falling back to demo diff.")
        return DEMO_DIFF, True

    return diff, False


def benchmark_openai_models():
    """Benchmark OpenAI models on commit message generation."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--models",
        nargs="+",
        default=["gpt-3.5-turbo", "gpt-4o-mini", "gpt-4o", "gpt-5"],
        help="Models to benchmark (space separated)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Iterations per model",
    )
    parser.add_argument(
        "--force-sample",
        action="store_true",
        help="Always use built‑in demo diff (ignore git)",
    )
    args, _ = parser.parse_known_args()

    load_dotenv()

    diff, is_demo = _resolve_diff(args)

    print(f"📄 Using {'demo' if is_demo else 'staged'} diff")
    print(f"   Lines: {len(diff.splitlines())}  Chars: {len(diff)}")
    print("=" * 60)

    results = []
    for model in args.models:
        print(f"\n🤖 {model}")
        print("-" * 40)
        try:
            provider = OpenAIProvider(model=model)
        except ValueError as e:
            print(f"❌ Init error: {e}")
            continue

        model_runs = []
        for i in range(args.iterations):
            print(f"  Iter {i+1}/{args.iterations} ... ", end="")
            start = time.time()
            try:
                msg = provider.generate_commit_message(diff)
                dur = time.time() - start
                model_runs.append(
                    {
                        "model": model,
                        "iteration": i + 1,
                        "response_time": dur,
                        "message_length": len(msg),
                        "message": msg.strip(),
                        "success": True,
                    }
                )
                print(f"✅ {dur:.2f}s")
            except Exception as ex:
                print(f"❌ {ex}")
                model_runs.append(
                    {
                        "model": model,
                        "iteration": i + 1,
                        "response_time": None,
                        "message_length": 0,
                        "message": "",
                        "success": False,
                        "error": str(ex),
                    }
                )
            time.sleep(0.6)

        results.extend(model_runs)
        ok = [r for r in model_runs if r["success"]]
        if ok:
            avg_t = sum(r["response_time"] for r in ok) / len(ok)
            avg_len = sum(r["message_length"] for r in ok) / len(ok)
            print(f"  📊 Avg time: {avg_t:.2f}s  Avg len: {avg_len:.0f} chars  Success: {len(ok)}/{args.iterations}")
            sample = ok[0]["message"]
            if len(sample) > 160:
                sample = sample[:160] + "..."
            print(f"  📝 Sample: {sample}")
        else:
            print("  ❌ All attempts failed")

    success = [r for r in results if r["success"]]
    if not success:
        print("\n❌ No successful runs.")
        return

    # Simple comparison
    from collections import defaultdict
    bucket = defaultdict(list)
    for r in success:
        bucket[r["model"]].append(r)

    stats = {}
    for m, rows in bucket.items():
        stats[m] = {
            "avg_time": sum(r["response_time"] for r in rows) / len(rows),
            "avg_len": sum(r["message_length"] for r in rows) / len(rows),
            "count": len(rows),
        }

    print("\n=== SUMMARY ===")
    fastest = sorted(stats.items(), key=lambda x: x[1]["avg_time"])
    print("⚡ Speed:")
    for i, (m, s) in enumerate(fastest):
        tag = "🏆" if i == 0 else " "
        print(f"  {tag} {m}: {s['avg_time']:.2f}s")

    detailed = sorted(stats.items(), key=lambda x: x[1]["avg_len"], reverse=True)
    print("\n📝 Detail (length):")
    for i, (m, s) in enumerate(detailed):
        tag = "🏆" if i == 0 else " "
        print(f"  {tag} {m}: {s['avg_len']:.0f} chars")

    # Save results
    ts = time.strftime("%Y%m%d_%H%M%S")
    out_file = f"benchmark_results_{ts}.json"
    with open(out_file, "w") as f:
        json.dump(
            {
                "timestamp": ts,
                "demo_diff": is_demo,
                "diff_lines": len(diff.splitlines()),
                "results": results,
                "stats": stats,
            },
            f,
            indent=2,
        )
    print(f"\n💾 Saved: {out_file}")


def _load_api_key():
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return True
    config = load_config()
    key = config.get("api_keys", {}).get("openai")
    if key:
        os.environ["OPENAI_API_KEY"] = key
        return True
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark OpenAI models.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=["gpt-4o-mini", "gpt-4o"],
        help="Models list",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Iterations per model",
    )
    parser.add_argument(
        "--force-sample",
        action="store_true",
        help="Always use built‑in demo diff",
    )
    parser.add_argument(
        "--check-api-key",
        action="store_true",
        help="Only check API key availability",
    )
    args = parser.parse_args()

    print("🚀 OpenAI Model Benchmark")
    print("=" * 50)

    if args.check_api_key:
        if _load_api_key():
            key = os.getenv("OPENAI_API_KEY")
            print(f"✅ API key found: {key[:4]}...{key[-4:]}")
            sys.exit(0)
        print("❌ No API key found")
        sys.exit(1)

    if not _load_api_key():
        print("❌ OPENAI_API_KEY missing (env or config).")
        print("Set via: export OPENAI_API_KEY=sk-...")
        sys.exit(1)

    # Pass through to internal runner
    sys.argv = [sys.argv[0]] + [f"--{k.replace('_','-')}={v}" for k, v in []]  # no-op
    # Simpler: reuse argparse in benchmark function
    # Provide flags again for inner parser:
    extra = []
    for m in args.models:
        extra += ["--models", m]
    extra += ["--iterations", str(args.iterations)]
    if args.force_sample:
        extra.append("--force-sample")
    sys.argv = [sys.argv[0]] + extra
    benchmark_openai_models()

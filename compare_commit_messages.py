#!/usr/bin/env python3
"""Compare Claude's commit message vs GAI semantic commit message."""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from acceptance_tests.analyzers.factory import AnalyzerFactory
from acceptance_tests.extractors.claim_extractor import ClaimExtractor
from acceptance_tests.verifiers.verification_engine import VerificationEngine

# Read the diff
with open("/tmp/acceptance_test_diff.txt") as f:
    diff_content = f.read()

# Read all commit messages
with open("/tmp/claude_message.txt") as f:
    claude_message = f.read()

with open("/tmp/gai_semantic_message.txt") as f:
    gai_openai_message = f.read()

with open("/tmp/gai_ollama_message.txt") as f:
    gai_ollama_message = f.read()


def analyze_message(message_name, commit_message):
    """Analyze a commit message against the diff."""
    print(f"\n{'=' * 80}")
    print(f"{message_name}")
    print('=' * 80)
    print(commit_message)
    print()

    # Analyze the first Python file in the diff as representative
    file_path = "acceptance_tests/analyzers/python_analyzer.py"

    analyzer = AnalyzerFactory.get_analyzer(file_path)
    ground_truth = analyzer.analyze_diff(diff_content, file_path)

    print(f"Ground Truth: {len(ground_truth.changes)} changes detected")

    # Extract claims
    extractor = ClaimExtractor()
    claims = extractor.extract_claims(commit_message)

    print(f"Claims Extracted: {len(claims)} claims")

    # Verify
    verifier = VerificationEngine()
    report = verifier.verify(claims, ground_truth)

    # Print results
    print(f"\n📊 SCORES:")
    print(f"  Accuracy:          {report.accuracy_score:6.2f}%")
    print(f"  Completeness:      {report.completeness_score:6.2f}%")
    print(f"  Hallucination Rate: {report.hallucination_rate:6.2f}%")
    print(f"  Overall Score:     {report.overall_score:6.2f}%")

    print(f"\n📈 DETAILS:")
    print(f"  Total Claims:      {report.total_claims}")
    print(f"  Verified Claims:   {report.verified_claims}")
    print(f"  False Claims:      {report.false_claims}")
    print(f"  Missing Facts:     {report.missing_facts}")

    # Show some verification details
    print(f"\n🔍 SAMPLE VERIFICATIONS:")
    for _, result in enumerate(report.verification_results[:5]):
        status = "✓" if result.verified else "✗"
        print(f"  {status} {result.claim.subject:30s} - {result.reason}")

    return report


if __name__ == "__main__":
    print("=" * 80)
    print("COMMIT MESSAGE ACCURACY COMPARISON - 3 APPROACHES")
    print("=" * 80)
    print(f"Analyzing diff across 17 files (2,771 insertions)")

    # Test all three messages
    claude_report = analyze_message("CLAUDE'S MANUAL ANALYSIS", claude_message)
    gai_openai_report = analyze_message("GAI SEMANTIC (OpenAI gpt-4o-mini)", gai_openai_message)
    gai_ollama_report = analyze_message("GAI SEMANTIC (Ollama llama3.2)", gai_ollama_message)

    # Comparison
    print(f"\n{'=' * 80}")
    print("COMPARISON SUMMARY")
    print('=' * 80)

    print(f"\n{'Metric':<20} {'Claude':>10} {'GAI-OpenAI':>12} {'GAI-Ollama':>12} {'Winner':>12}")
    print("-" * 70)

    metrics = [
        ("Accuracy", claude_report.accuracy_score, gai_openai_report.accuracy_score, gai_ollama_report.accuracy_score),
        ("Completeness", claude_report.completeness_score, gai_openai_report.completeness_score, gai_ollama_report.completeness_score),
        ("Hallucination Rate", claude_report.hallucination_rate, gai_openai_report.hallucination_rate, gai_ollama_report.hallucination_rate),
        ("Overall Score", claude_report.overall_score, gai_openai_report.overall_score, gai_ollama_report.overall_score),
    ]

    for metric_name, claude_val, openai_val, ollama_val in metrics:
        if metric_name == "Hallucination Rate":
            # Lower is better
            winner_val = min(claude_val, openai_val, ollama_val)
        else:
            # Higher is better
            winner_val = max(claude_val, openai_val, ollama_val)

        if claude_val == winner_val:
            winner = "Claude"
        elif openai_val == winner_val:
            winner = "GAI-OpenAI"
        else:
            winner = "GAI-Ollama"

        print(f"{metric_name:<20} {claude_val:>9.1f}% {openai_val:>11.1f}% {ollama_val:>11.1f}% {winner:>12}")

    print(f"\n🎯 OVERALL WINNER:")
    scores = [
        ("Claude", claude_report.overall_score),
        ("GAI-OpenAI", gai_openai_report.overall_score),
        ("GAI-Ollama", gai_ollama_report.overall_score)
    ]
    winner_name, winner_score = max(scores, key=lambda x: x[1])
    print(f"  🏆 {winner_name} with {winner_score:.1f}% overall score")

    print(f"\n📝 MESSAGE CHARACTERISTICS:")
    print(f"  • Claude length:      {len(claude_message):4d} chars | {len(ClaimExtractor().extract_claims(claude_message)):2d} claims")
    print(f"  • GAI-OpenAI length:  {len(gai_openai_message):4d} chars | {len(ClaimExtractor().extract_claims(gai_openai_message)):2d} claims")
    print(f"  • GAI-Ollama length:  {len(gai_ollama_message):4d} chars | {len(ClaimExtractor().extract_claims(gai_ollama_message)):2d} claims")

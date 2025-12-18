#!/usr/bin/env python3
"""
Main test runner for commit message accuracy verification.

This can be used to test commit messages against actual diffs to verify
that AI-generated messages are factually accurate.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Tuple

from acceptance_tests.analyzers.factory import AnalyzerFactory
from acceptance_tests.extractors.claim_extractor import ClaimExtractor
from acceptance_tests.verifiers.verification_engine import VerificationEngine, AccuracyReport


def verify_commit_message(diff: str, commit_message: str, file_path: str) -> AccuracyReport:
    """
    Verify a commit message against a diff.

    Args:
        diff: The unified diff content
        commit_message: The commit message to verify
        file_path: Path to the file (for language detection)

    Returns:
        AccuracyReport with verification results
    """
    # Step 1: Analyze diff to extract ground truth
    analyzer = AnalyzerFactory.get_analyzer(file_path)
    ground_truth = analyzer.analyze_diff(diff, file_path)

    # Step 2: Extract claims from commit message
    extractor = ClaimExtractor()
    claims = extractor.extract_claims(commit_message)

    # Step 3: Verify claims against ground truth
    verifier = VerificationEngine()
    report = verifier.verify(claims, ground_truth)

    return report


def print_report(report: AccuracyReport, verbose: bool = False):
    """Print a formatted accuracy report."""
    print("\n" + "=" * 70)
    print("ACCURACY REPORT")
    print("=" * 70)

    print(f"\n📊 SCORES:")
    print(f"  Accuracy:        {report.accuracy_score:6.1f}%  (claims that are true)")
    print(f"  Completeness:    {report.completeness_score:6.1f}%  (coverage of changes)")
    print(f"  Hallucination:   {report.hallucination_rate:6.1f}%  (false claims)")
    print(f"  Overall Score:   {report.overall_score:6.1f}%")

    print(f"\n📈 STATS:")
    print(f"  Total claims:    {report.total_claims}")
    print(f"  Verified:        {report.verified_claims}")
    print(f"  False:           {report.false_claims}")
    print(f"  Missing facts:   {report.missing_facts}")

    if verbose:
        print(f"\n🔍 DETAILED VERIFICATION:")
        for result in report.verification_results:
            status = "✓" if result.verified else "✗"
            print(f"  {status} {result.claim.subject:30s} ({result.confidence:.0%}) - {result.reason}")

        if report.ground_truth:
            print(f"\n💡 GROUND TRUTH ({len(report.ground_truth.changes)} changes):")
            for change in report.ground_truth.changes:
                print(f"  • {change}")

    # Verdict
    print(f"\n🎯 VERDICT:")
    if report.overall_score >= 80:
        print("  ✅ EXCELLENT - Accurate and complete commit message")
    elif report.overall_score >= 60:
        print("  ✓ GOOD - Mostly accurate with minor issues")
    elif report.overall_score >= 40:
        print("  ⚠ FAIR - Some accuracy issues or missing details")
    else:
        print("  ❌ POOR - Significant accuracy problems or hallucinations")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify commit message accuracy against code diffs"
    )
    parser.add_argument(
        "--diff",
        required=True,
        help="Path to diff file or diff content"
    )
    parser.add_argument(
        "--message",
        required=True,
        help="Path to commit message file or message content"
    )
    parser.add_argument(
        "--file",
        default="file.py",
        help="File path (for language detection)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed verification results"
    )

    args = parser.parse_args()

    # Read diff
    if Path(args.diff).exists():
        with open(args.diff) as f:
            diff = f.read()
    else:
        diff = args.diff

    # Read commit message
    if Path(args.message).exists():
        with open(args.message) as f:
            message = f.read()
    else:
        message = args.message

    print("🔍 Analyzing diff and verifying commit message...")

    # Verify
    report = verify_commit_message(diff, message, args.file)

    # Print results
    print_report(report, verbose=args.verbose)

    # Exit code based on overall score
    if report.overall_score >= 60:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

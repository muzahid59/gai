#!/usr/bin/env python3
"""
Benchmark Research - Master Script

This script runs the complete benchmark suite:
1. Collect commits from repository
2. Run comparison analysis (semantic vs traditional)
3. Perform statistical analysis
4. Generate comprehensive report
"""

import argparse
import sys
from pathlib import Path

# Add project root and src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from benchmark_research.collectors.commit_collector import CommitCollector
from benchmark_research.analyzers.comparison_engine import ComparisonEngine
from benchmark_research.analysis.statistical_analyzer import StatisticalAnalyzer
from benchmark_research.reporting.report_generator import ReportGenerator


def run_full_benchmark(
    repo_path: str = '.',
    commit_count: int = 30,
    output_dir: str = 'benchmark_research'
):
    """
    Run complete benchmark suite.

    Args:
        repo_path: Path to git repository
        commit_count: Number of commits to analyze
        output_dir: Output directory for results
    """
    print("\n" + "=" * 70)
    print("🚀 BENCHMARK RESEARCH SUITE")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"   Repository: {repo_path}")
    print(f"   Commits: {commit_count}")
    print(f"   Output: {output_dir}")
    print("\n" + "=" * 70)

    # File paths
    data_dir = Path(output_dir) / 'data'
    results_dir = Path(output_dir) / 'results'

    commits_file = data_dir / 'commits.json'
    comparison_file = results_dir / 'comparison.json'
    statistics_file = results_dir / 'statistical_analysis.json'
    report_file = results_dir / 'BENCHMARK_REPORT.md'

    try:
        # Phase 1 & 2: Collect Commits
        print("\n📦 PHASE 1-2: Collecting Commits")
        print("-" * 70)

        collector = CommitCollector(repo_path)
        commits = collector.collect_commits(count=commit_count)
        collector.print_summary(commits)
        collector.save_commits(commits, str(commits_file))

        # Phase 3: Run Comparison Analysis
        print("\n🔬 PHASE 3: Running Comparison Analysis")
        print("-" * 70)

        engine = ComparisonEngine(repo_path=repo_path)
        engine.run_comparison(str(commits_file), str(comparison_file))

        # Phase 4: Statistical Analysis
        print("\n📈 PHASE 4: Statistical Analysis")
        print("-" * 70)

        analyzer = StatisticalAnalyzer(str(comparison_file))
        analysis = analyzer.analyze()
        analyzer.save_results(str(statistics_file), analysis)

        # Phase 5: Generate Report
        print("\n📝 PHASE 5: Generating Report")
        print("-" * 70)

        generator = ReportGenerator(
            str(comparison_file),
            str(statistics_file),
            str(commits_file)
        )
        generator.generate_report(str(report_file))

        # Summary
        print("\n" + "=" * 70)
        print("✅ BENCHMARK COMPLETE!")
        print("=" * 70)
        print(f"\n📊 Results:")
        print(f"   Data:        {commits_file}")
        print(f"   Comparison:  {comparison_file}")
        print(f"   Statistics:  {statistics_file}")
        print(f"   Report:      {report_file}")
        print(f"\n📄 View the report:")
        print(f"   cat {report_file}")
        print(f"   or open {report_file} in your editor")
        print("\n" + "=" * 70)

        return True

    except Exception as e:
        print(f"\n❌ BENCHMARK FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """CLI for benchmark suite."""
    parser = argparse.ArgumentParser(
        description='Run complete benchmark suite for semantic vs traditional diff analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with defaults (30 commits from current repo)
  python run_benchmark.py

  # Analyze 50 commits
  python run_benchmark.py --commits 50

  # Analyze different repository
  python run_benchmark.py --repo /path/to/repo --commits 100

  # Custom output directory
  python run_benchmark.py --output my_benchmark_results
        """
    )

    parser.add_argument(
        '--repo',
        default='.',
        help='Path to git repository (default: current directory)'
    )
    parser.add_argument(
        '--commits',
        type=int,
        default=30,
        help='Number of commits to analyze (default: 30)'
    )
    parser.add_argument(
        '--output',
        default='benchmark_research',
        help='Output directory (default: benchmark_research)'
    )

    args = parser.parse_args()

    success = run_full_benchmark(
        repo_path=args.repo,
        commit_count=args.commits,
        output_dir=args.output
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

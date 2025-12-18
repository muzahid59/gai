"""
Comparison Engine - Run both analyzers and compare results.

This module runs both traditional and semantic analyzers on the same
commits and generates comparison metrics.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from .traditional_analyzer import TraditionalAnalyzer
from .semantic_analyzer_wrapper import SemanticAnalyzerWrapper


class ComparisonEngine:
    """Run both analyzers and compare results."""

    def __init__(self, repo_path: str = '.'):
        """
        Initialize comparison engine.

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = repo_path
        self.traditional = TraditionalAnalyzer()
        self.semantic = SemanticAnalyzerWrapper(repo_path)

    def run_comparison(self, commits_file: str, output_file: str):
        """
        Run comparison analysis on commits.

        Args:
            commits_file: Path to commits JSON file
            output_file: Path to save results
        """
        print("\n" + "=" * 70)
        print("🔬 BENCHMARK: Semantic vs Traditional Analysis")
        print("=" * 70)

        # Load commits
        print(f"\n📂 Loading commits from: {commits_file}")
        with open(commits_file, 'r') as f:
            data = json.load(f)

        commits = data['commits']
        print(f"   ✓ Loaded {len(commits)} commits")

        # Run both analyzers
        traditional_results = self.traditional.analyze_batch(commits)
        semantic_results = self.semantic.analyze_batch(commits)

        # Compare results
        print(f"\n📊 Comparing Results:")
        comparisons = self._compare_results(traditional_results, semantic_results)

        # Calculate summary statistics
        print(f"\n📈 Calculating Statistics...")
        summary = self._calculate_summary(comparisons, commits)

        # Save results
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        results = {
            'metadata': {
                'analysis_date': datetime.now().isoformat(),
                'commits_analyzed': len(commits),
                'source_file': commits_file,
                'repository': data.get('repository', 'unknown')
            },
            'summary': summary,
            'comparisons': comparisons
        }

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"   ✓ Results saved to: {output_file}")

        # Print summary
        self._print_summary(summary)

        return results

    def _compare_results(
        self,
        traditional_results: List[Dict],
        semantic_results: List[Dict]
    ) -> List[Dict]:
        """
        Compare results from both analyzers.

        Args:
            traditional_results: Results from traditional analyzer
            semantic_results: Results from semantic analyzer

        Returns:
            List of comparison dictionaries
        """
        comparisons = []

        for trad, sem in zip(traditional_results, semantic_results):
            # Calculate metrics
            token_reduction = 0
            if trad['tokens'] > 0:
                token_reduction = ((trad['tokens'] - sem['tokens']) / trad['tokens']) * 100

            cost_savings = trad['estimated_cost'] - sem['estimated_cost']
            time_diff = sem['time_seconds'] - trad['time_seconds']

            comparison = {
                'commit_hash': trad['commit_hash'],
                'traditional': {
                    'tokens': trad['tokens'],
                    'time_seconds': trad['time_seconds'],
                    'cost': trad['estimated_cost']
                },
                'semantic': {
                    'tokens': sem['tokens'],
                    'time_seconds': sem['time_seconds'],
                    'cost': sem['estimated_cost']
                },
                'metrics': {
                    'token_reduction_percent': token_reduction,
                    'tokens_saved': trad['tokens'] - sem['tokens'],
                    'cost_savings': cost_savings,
                    'time_difference': time_diff
                }
            }

            comparisons.append(comparison)

        return comparisons

    def _calculate_summary(self, comparisons: List[Dict], commits: List[Dict]) -> Dict:
        """
        Calculate summary statistics.

        Args:
            comparisons: List of comparison results
            commits: Original commit data

        Returns:
            Summary statistics dictionary
        """
        if not comparisons:
            return {}

        # Token metrics
        total_trad_tokens = sum(c['traditional']['tokens'] for c in comparisons)
        total_sem_tokens = sum(c['semantic']['tokens'] for c in comparisons)
        total_tokens_saved = total_trad_tokens - total_sem_tokens
        avg_token_reduction = sum(c['metrics']['token_reduction_percent'] for c in comparisons) / len(comparisons)

        # Cost metrics
        total_trad_cost = sum(c['traditional']['cost'] for c in comparisons)
        total_sem_cost = sum(c['semantic']['cost'] for c in comparisons)
        total_cost_savings = total_trad_cost - total_sem_cost

        # Time metrics
        total_trad_time = sum(c['traditional']['time_seconds'] for c in comparisons)
        total_sem_time = sum(c['semantic']['time_seconds'] for c in comparisons)
        avg_time_diff = sum(c['metrics']['time_difference'] for c in comparisons) / len(comparisons)

        # By size
        by_size = self._analyze_by_category(comparisons, commits, 'size')

        # By language
        by_language = self._analyze_by_category(comparisons, commits, 'primary_language')

        # By commit type
        by_type = self._analyze_by_category(comparisons, commits, 'commit_type')

        return {
            'overall': {
                'commits_analyzed': len(comparisons),
                'total_traditional_tokens': total_trad_tokens,
                'total_semantic_tokens': total_sem_tokens,
                'total_tokens_saved': total_tokens_saved,
                'average_token_reduction_percent': avg_token_reduction,
                'total_traditional_cost': total_trad_cost,
                'total_semantic_cost': total_sem_cost,
                'total_cost_savings': total_cost_savings,
                'total_traditional_time': total_trad_time,
                'total_semantic_time': total_sem_time,
                'average_time_difference': avg_time_diff
            },
            'by_size': by_size,
            'by_language': by_language,
            'by_commit_type': by_type
        }

    def _analyze_by_category(
        self,
        comparisons: List[Dict],
        commits: List[Dict],
        category_key: str
    ) -> Dict:
        """
        Analyze metrics by category (size, language, or type).

        Args:
            comparisons: Comparison results
            commits: Original commit data
            category_key: 'size', 'primary_language', or 'commit_type'

        Returns:
            Dictionary with metrics by category
        """
        # Build category mapping
        category_map = {}
        for commit in commits:
            commit_hash = commit['hash']

            if category_key == 'commit_type':
                category = commit['metadata']['commit_type']
            else:
                category = commit['classification'][category_key]

            category_map[commit_hash] = category

        # Group comparisons by category
        by_category = {}
        for comp in comparisons:
            category = category_map.get(comp['commit_hash'], 'unknown')

            if category not in by_category:
                by_category[category] = []

            by_category[category].append(comp)

        # Calculate metrics for each category
        results = {}
        for category, comps in by_category.items():
            avg_reduction = sum(c['metrics']['token_reduction_percent'] for c in comps) / len(comps)
            total_savings = sum(c['metrics']['cost_savings'] for c in comps)

            results[category] = {
                'count': len(comps),
                'avg_token_reduction_percent': avg_reduction,
                'total_cost_savings': total_savings,
                'avg_traditional_tokens': sum(c['traditional']['tokens'] for c in comps) / len(comps),
                'avg_semantic_tokens': sum(c['semantic']['tokens'] for c in comps) / len(comps)
            }

        return results

    def _print_summary(self, summary: Dict):
        """
        Print summary statistics to console.

        Args:
            summary: Summary statistics dictionary
        """
        print("\n" + "=" * 70)
        print("📊 BENCHMARK RESULTS SUMMARY")
        print("=" * 70)

        overall = summary['overall']

        print(f"\n🎯 Overall Performance:")
        print(f"   Commits Analyzed:        {overall['commits_analyzed']}")
        print(f"   Total Traditional Tokens: {overall['total_traditional_tokens']:,}")
        print(f"   Total Semantic Tokens:    {overall['total_semantic_tokens']:,}")
        print(f"   Total Tokens Saved:       {overall['total_tokens_saved']:,}")
        print(f"   Average Token Reduction:  {overall['average_token_reduction_percent']:.1f}%")

        print(f"\n💰 Cost Analysis:")
        print(f"   Traditional Cost:  ${overall['total_traditional_cost']:.4f}")
        print(f"   Semantic Cost:     ${overall['total_semantic_cost']:.4f}")
        print(f"   Total Savings:     ${overall['total_cost_savings']:.4f}")
        print(f"   Savings Percent:   {(overall['total_cost_savings'] / overall['total_traditional_cost'] * 100):.1f}%")

        print(f"\n⏱️  Time Analysis:")
        print(f"   Traditional Time:  {overall['total_traditional_time']:.2f}s")
        print(f"   Semantic Time:     {overall['total_semantic_time']:.2f}s")
        print(f"   Avg Time Diff:     {overall['average_time_difference']:.3f}s per commit")

        # By size
        if 'by_size' in summary:
            print(f"\n📏 By Commit Size:")
            for size in ['small', 'medium', 'large', 'xlarge']:
                if size in summary['by_size']:
                    data = summary['by_size'][size]
                    print(f"   {size.capitalize():<10} "
                          f"{data['count']:>3} commits, "
                          f"{data['avg_token_reduction_percent']:>5.1f}% reduction, "
                          f"${data['total_cost_savings']:>6.4f} saved")

        # By language
        if 'by_language' in summary:
            print(f"\n🌐 By Language:")
            for lang, data in sorted(summary['by_language'].items(), key=lambda x: -x[1]['count']):
                print(f"   {lang.capitalize():<15} "
                      f"{data['count']:>3} commits, "
                      f"{data['avg_token_reduction_percent']:>5.1f}% reduction")

        # By commit type
        if 'by_commit_type' in summary:
            print(f"\n📝 By Commit Type:")
            for ctype, data in sorted(summary['by_commit_type'].items(), key=lambda x: -x[1]['count']):
                print(f"   {ctype.capitalize():<15} "
                      f"{data['count']:>3} commits, "
                      f"{data['avg_token_reduction_percent']:>5.1f}% reduction")

        print("\n" + "=" * 70)


def main():
    """CLI for comparison engine."""
    import argparse

    parser = argparse.ArgumentParser(description='Compare semantic vs traditional analysis')
    parser.add_argument(
        '--commits',
        default='benchmark_research/data/commits.json',
        help='Path to commits JSON file'
    )
    parser.add_argument(
        '--output',
        default='benchmark_research/results/comparison.json',
        help='Path to save results'
    )
    parser.add_argument(
        '--repo',
        default='.',
        help='Repository path'
    )

    args = parser.parse_args()

    engine = ComparisonEngine(repo_path=args.repo)
    engine.run_comparison(args.commits, args.output)

    print(f"\n✅ Comparison complete!")
    print(f"   Results: {args.output}")


if __name__ == '__main__':
    main()

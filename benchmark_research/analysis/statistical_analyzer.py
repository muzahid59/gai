"""
Statistical Analyzer - Calculate detailed statistics and identify patterns.

This module performs statistical analysis on the comparison results to
identify patterns, outliers, and provide deeper insights.
"""

import json
import statistics
from pathlib import Path
from typing import Dict, List


class StatisticalAnalyzer:
    """Perform statistical analysis on benchmark results."""

    def __init__(self, results_file: str):
        """
        Initialize analyzer.

        Args:
            results_file: Path to comparison results JSON
        """
        with open(results_file, 'r') as f:
            self.data = json.load(f)

        self.comparisons = self.data['comparisons']

    def analyze(self) -> Dict:
        """
        Perform comprehensive statistical analysis.

        Returns:
            Dictionary with statistical analysis results
        """
        print("\n" + "=" * 70)
        print("📈 STATISTICAL ANALYSIS")
        print("=" * 70)

        results = {
            'descriptive_stats': self._descriptive_statistics(),
            'distribution_analysis': self._distribution_analysis(),
            'correlation_analysis': self._correlation_analysis(),
            'outlier_detection': self._detect_outliers(),
            'efficiency_analysis': self._efficiency_analysis()
        }

        return results

    def _descriptive_statistics(self) -> Dict:
        """Calculate descriptive statistics for key metrics."""
        print("\n📊 Descriptive Statistics:")

        token_reductions = [c['metrics']['token_reduction_percent'] for c in self.comparisons]
        cost_savings = [c['metrics']['cost_savings'] for c in self.comparisons]
        tokens_saved = [c['metrics']['tokens_saved'] for c in self.comparisons]

        stats = {
            'token_reduction': self._calculate_stats(token_reductions, 'Token Reduction'),
            'cost_savings': self._calculate_stats(cost_savings, 'Cost Savings'),
            'tokens_saved': self._calculate_stats(tokens_saved, 'Tokens Saved')
        }

        return stats

    def _calculate_stats(self, values: List[float], name: str) -> Dict:
        """Calculate statistics for a list of values."""
        if not values:
            return {}

        stats = {
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
            'min': min(values),
            'max': max(values),
            'q1': statistics.quantiles(values, n=4)[0] if len(values) >= 4 else min(values),
            'q3': statistics.quantiles(values, n=4)[2] if len(values) >= 4 else max(values)
        }

        print(f"   {name}:")
        print(f"      Mean:   {stats['mean']:.2f}")
        print(f"      Median: {stats['median']:.2f}")
        print(f"      Std Dev: {stats['std_dev']:.2f}")
        print(f"      Min:    {stats['min']:.2f}")
        print(f"      Max:    {stats['max']:.2f}")
        print(f"      Q1:     {stats['q1']:.2f}")
        print(f"      Q3:     {stats['q3']:.2f}")

        return stats

    def _distribution_analysis(self) -> Dict:
        """Analyze distribution of token reductions."""
        print("\n📉 Distribution Analysis:")

        token_reductions = [c['metrics']['token_reduction_percent'] for c in self.comparisons]

        # Create buckets
        buckets = {
            '0-50%': 0,
            '50-70%': 0,
            '70-85%': 0,
            '85-95%': 0,
            '95-100%': 0
        }

        for reduction in token_reductions:
            if reduction < 50:
                buckets['0-50%'] += 1
            elif reduction < 70:
                buckets['50-70%'] += 1
            elif reduction < 85:
                buckets['70-85%'] += 1
            elif reduction < 95:
                buckets['85-95%'] += 1
            else:
                buckets['95-100%'] += 1

        print("   Token Reduction Distribution:")
        for bucket, count in buckets.items():
            percent = (count / len(token_reductions) * 100) if token_reductions else 0
            bar = '█' * int(percent / 5)
            print(f"      {bucket:<12} {count:>3} commits ({percent:>5.1f}%) {bar}")

        return {
            'buckets': buckets,
            'total_commits': len(token_reductions)
        }

    def _correlation_analysis(self) -> Dict:
        """Analyze correlation between commit characteristics and performance."""
        print("\n🔗 Correlation Analysis:")

        # Load original commits for metadata
        commits_file = self.data['metadata'].get('source_file')
        if not commits_file:
            print("   ⚠️  No source file found, skipping correlation analysis")
            return {}

        with open(commits_file, 'r') as f:
            commits_data = json.load(f)

        # Build commit lookup
        commit_lookup = {c['hash']: c for c in commits_data['commits']}

        # Analyze: files changed vs token reduction
        files_vs_reduction = []
        for comp in self.comparisons:
            commit = commit_lookup.get(comp['commit_hash'])
            if commit:
                files_changed = commit['metadata']['files_changed']
                reduction = comp['metrics']['token_reduction_percent']
                files_vs_reduction.append((files_changed, reduction))

        # Calculate correlation
        if len(files_vs_reduction) > 1:
            files_changed = [x[0] for x in files_vs_reduction]
            reductions = [x[1] for x in files_vs_reduction]

            # Simple correlation coefficient
            correlation = self._pearson_correlation(files_changed, reductions)
            print(f"   Files Changed vs Token Reduction: {correlation:.3f}")

            if correlation > 0.3:
                print(f"      → Positive correlation: More files = Better reduction")
            elif correlation < -0.3:
                print(f"      → Negative correlation: Fewer files = Better reduction")
            else:
                print(f"      → Weak correlation")

            return {
                'files_vs_reduction_correlation': correlation,
                'interpretation': self._interpret_correlation(correlation)
            }

        return {}

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0

        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n

        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator_x = sum((x[i] - mean_x) ** 2 for i in range(n))
        denominator_y = sum((y[i] - mean_y) ** 2 for i in range(n))

        if denominator_x == 0 or denominator_y == 0:
            return 0.0

        return numerator / (denominator_x * denominator_y) ** 0.5

    def _interpret_correlation(self, correlation: float) -> str:
        """Interpret correlation coefficient."""
        abs_corr = abs(correlation)
        if abs_corr > 0.7:
            return "strong"
        elif abs_corr > 0.3:
            return "moderate"
        else:
            return "weak"

    def _detect_outliers(self) -> Dict:
        """Detect outliers in token reduction."""
        print("\n🎯 Outlier Detection:")

        token_reductions = [c['metrics']['token_reduction_percent'] for c in self.comparisons]

        if len(token_reductions) < 4:
            print("   ⚠️  Not enough data for outlier detection")
            return {}

        # Calculate IQR
        q1 = statistics.quantiles(token_reductions, n=4)[0]
        q3 = statistics.quantiles(token_reductions, n=4)[2]
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # Find outliers
        outliers = []
        for comp in self.comparisons:
            reduction = comp['metrics']['token_reduction_percent']
            if reduction < lower_bound or reduction > upper_bound:
                outliers.append({
                    'commit_hash': comp['commit_hash'],
                    'token_reduction': reduction,
                    'tokens_saved': comp['metrics']['tokens_saved'],
                    'type': 'low' if reduction < lower_bound else 'high'
                })

        print(f"   IQR: {iqr:.2f} (Q1: {q1:.2f}, Q3: {q3:.2f})")
        print(f"   Bounds: [{lower_bound:.2f}, {upper_bound:.2f}]")
        print(f"   Outliers Detected: {len(outliers)}")

        if outliers:
            print("\n   Outliers:")
            for outlier in outliers[:5]:  # Show first 5
                print(f"      {outlier['commit_hash']}: {outlier['token_reduction']:.1f}% "
                      f"({outlier['type']} outlier)")

        return {
            'iqr': iqr,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'outliers': outliers,
            'outlier_count': len(outliers)
        }

    def _efficiency_analysis(self) -> Dict:
        """Analyze efficiency of semantic approach."""
        print("\n⚡ Efficiency Analysis:")

        # Best performers
        sorted_by_reduction = sorted(
            self.comparisons,
            key=lambda x: x['metrics']['token_reduction_percent'],
            reverse=True
        )

        best = sorted_by_reduction[:5]
        worst = sorted_by_reduction[-5:]

        print(f"\n   Top 5 Best Performers (Token Reduction):")
        for i, comp in enumerate(best, 1):
            print(f"      {i}. {comp['commit_hash']}: "
                  f"{comp['metrics']['token_reduction_percent']:.1f}% "
                  f"({comp['metrics']['tokens_saved']:,} tokens saved)")

        print(f"\n   Bottom 5 Performers (Token Reduction):")
        for i, comp in enumerate(worst, 1):
            print(f"      {i}. {comp['commit_hash']}: "
                  f"{comp['metrics']['token_reduction_percent']:.1f}% "
                  f"({comp['metrics']['tokens_saved']:,} tokens saved)")

        # Calculate aggregate efficiency
        total_trad_tokens = sum(c['traditional']['tokens'] for c in self.comparisons)
        total_sem_tokens = sum(c['semantic']['tokens'] for c in self.comparisons)
        total_cost_savings = sum(c['metrics']['cost_savings'] for c in self.comparisons)

        efficiency_score = (total_trad_tokens - total_sem_tokens) / total_trad_tokens * 100

        print(f"\n   Overall Efficiency Score: {efficiency_score:.1f}%")
        print(f"   Total Cost Savings: ${total_cost_savings:.4f}")

        return {
            'best_performers': [
                {
                    'commit_hash': c['commit_hash'],
                    'token_reduction': c['metrics']['token_reduction_percent'],
                    'tokens_saved': c['metrics']['tokens_saved']
                }
                for c in best
            ],
            'worst_performers': [
                {
                    'commit_hash': c['commit_hash'],
                    'token_reduction': c['metrics']['token_reduction_percent'],
                    'tokens_saved': c['metrics']['tokens_saved']
                }
                for c in worst
            ],
            'efficiency_score': efficiency_score,
            'total_cost_savings': total_cost_savings
        }

    def save_results(self, output_file: str, analysis: Dict):
        """
        Save statistical analysis results.

        Args:
            output_file: Path to save results
            analysis: Analysis results dictionary
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        results = {
            'metadata': self.data.get('metadata', {}),
            'statistical_analysis': analysis
        }

        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n💾 Statistical analysis saved to: {output_file}")


def main():
    """CLI for statistical analyzer."""
    import argparse

    parser = argparse.ArgumentParser(description='Statistical analysis of benchmark results')
    parser.add_argument(
        '--results',
        default='benchmark_research/results/comparison.json',
        help='Path to comparison results JSON'
    )
    parser.add_argument(
        '--output',
        default='benchmark_research/results/statistical_analysis.json',
        help='Path to save statistical analysis'
    )

    args = parser.parse_args()

    try:
        analyzer = StatisticalAnalyzer(args.results)
        analysis = analyzer.analyze()
        analyzer.save_results(args.output, analysis)

        print("\n✅ Statistical analysis complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == '__main__':
    main()

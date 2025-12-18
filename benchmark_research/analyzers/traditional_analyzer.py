"""
Traditional Analyzer - Analyze commits using raw git diff.

This module measures the performance of traditional diff approach
for comparison with semantic analysis.
"""

import time
import sys
from pathlib import Path
from typing import Dict

# Add src to path for utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from gai.utils import estimate_tokens


class TraditionalAnalyzer:
    """Analyze commits using traditional git diff approach."""

    def __init__(self):
        """Initialize traditional analyzer."""
        self.name = "traditional"

    def analyze_commit(self, commit_data: Dict) -> Dict:
        """
        Analyze a commit using traditional diff approach.

        Args:
            commit_data: Commit data dictionary

        Returns:
            Analysis results
        """
        start_time = time.time()

        # Get raw diff
        diff_content = commit_data.get('diff', '')

        # Measure tokens
        tokens = estimate_tokens(diff_content)

        # Calculate processing time
        elapsed_time = time.time() - start_time

        # Estimate API cost (GPT-3.5-turbo: $0.0015/1K input tokens)
        estimated_cost = (tokens / 1000) * 0.0015

        return {
            'approach': 'traditional',
            'tokens': tokens,
            'time_seconds': elapsed_time,
            'content_length': len(diff_content),
            'estimated_cost': estimated_cost,
            'content_preview': diff_content[:500] if diff_content else '',
        }

    def analyze_batch(self, commits: list) -> list:
        """
        Analyze multiple commits.

        Args:
            commits: List of commit data dictionaries

        Returns:
            List of analysis results
        """
        results = []

        print(f"🔍 Traditional Analysis:")
        for i, commit in enumerate(commits, 1):
            result = self.analyze_commit(commit)
            result['commit_hash'] = commit['hash']
            results.append(result)

            if i % 5 == 0:
                print(f"   Processed: {i}/{len(commits)}...")

        print(f"   ✓ Completed {len(results)} commits")

        return results

"""
Commit Collector - Extract commits from git repositories for analysis.

This module collects commits with metadata, diffs, and classifications
for benchmarking semantic vs traditional diff approaches.
"""

import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import re


class CommitCollector:
    """Collect and classify commits from git repositories."""

    def __init__(self, repo_path: str):
        """
        Initialize collector.

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = Path(repo_path)
        if not (self.repo_path / '.git').exists():
            raise ValueError(f"Not a git repository: {repo_path}")

    def collect_commits(
        self,
        count: int = 30,
        skip_merges: bool = True,
        min_files: int = 1
    ) -> List[Dict]:
        """
        Collect commits from repository.

        Args:
            count: Number of commits to collect
            skip_merges: Skip merge commits
            min_files: Minimum files changed per commit

        Returns:
            List of commit data dictionaries
        """
        print(f"📦 Collecting commits from: {self.repo_path.name}")
        print(f"   Target: {count} commits")

        commits = []
        collected = 0
        skip_count = 0

        # Get commit list
        cmd = ['git', 'log', '--oneline', '--no-merges' if skip_merges else '--all', '-500']
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )

        commit_hashes = [line.split()[0] for line in result.stdout.strip().split('\n') if line]

        for commit_hash in commit_hashes:
            if collected >= count:
                break

            try:
                commit_data = self._extract_commit_data(commit_hash)

                # Filter by minimum files
                if commit_data['metadata']['files_changed'] < min_files:
                    skip_count += 1
                    continue

                # Skip if no meaningful changes (e.g., only .gitignore)
                if not commit_data['files']:
                    skip_count += 1
                    continue

                commits.append(commit_data)
                collected += 1

                # Progress indicator
                if collected % 5 == 0:
                    print(f"   Collected: {collected}/{count}...")

            except Exception as e:
                print(f"   ⚠️  Skipped commit {commit_hash}: {e}")
                skip_count += 1
                continue

        print(f"   ✓ Collected {collected} commits")
        if skip_count > 0:
            print(f"   ⊘ Skipped {skip_count} commits (merges, no files, errors)")

        # Classify commits
        self._classify_commits(commits)

        return commits

    def _extract_commit_data(self, commit_hash: str) -> Dict:
        """
        Extract detailed data for a single commit.

        Args:
            commit_hash: Git commit hash

        Returns:
            Dictionary with commit data
        """
        # Get commit metadata
        metadata_cmd = [
            'git', 'show', '--no-patch',
            '--format=%H%n%an%n%ae%n%ai%n%s%n%b',
            commit_hash
        ]
        result = subprocess.run(
            metadata_cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        lines = result.stdout.strip().split('\n')
        full_hash = lines[0]
        author_name = lines[1]
        author_email = lines[2]
        date = lines[3]
        subject = lines[4]
        body = '\n'.join(lines[5:]) if len(lines) > 5 else ''

        # Get files changed
        files_cmd = ['git', 'show', '--name-status', '--format=', commit_hash]
        result = subprocess.run(
            files_cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )

        files = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) >= 2:
                status = parts[0]
                filepath = parts[1]
                files.append({
                    'path': filepath,
                    'status': status,
                    'extension': Path(filepath).suffix
                })

        # Get diff stats
        stats_cmd = ['git', 'show', '--shortstat', '--format=', commit_hash]
        result = subprocess.run(
            stats_cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        stats_line = result.stdout.strip()

        # Parse stats
        files_changed = 0
        insertions = 0
        deletions = 0

        if stats_line:
            # Format: "3 files changed, 45 insertions(+), 12 deletions(-)"
            match = re.search(r'(\d+) file', stats_line)
            if match:
                files_changed = int(match.group(1))

            match = re.search(r'(\d+) insertion', stats_line)
            if match:
                insertions = int(match.group(1))

            match = re.search(r'(\d+) deletion', stats_line)
            if match:
                deletions = int(match.group(1))

        # Get full diff
        diff_cmd = ['git', 'show', commit_hash]
        result = subprocess.run(
            diff_cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        diff_content = result.stdout

        # Extract commit type from message
        commit_type = self._extract_commit_type(subject)

        return {
            'hash': commit_hash,
            'full_hash': full_hash,
            'author': {
                'name': author_name,
                'email': author_email
            },
            'date': date,
            'message': {
                'subject': subject,
                'body': body
            },
            'metadata': {
                'files_changed': files_changed,
                'insertions': insertions,
                'deletions': deletions,
                'total_changes': insertions + deletions,
                'commit_type': commit_type
            },
            'files': files,
            'diff': diff_content,
            'classification': {}  # Will be filled by _classify_commits
        }

    def _extract_commit_type(self, subject: str) -> str:
        """
        Extract commit type from subject line.

        Args:
            subject: Commit subject line

        Returns:
            Commit type (feat, fix, refactor, etc.)
        """
        # Check conventional commits format
        match = re.match(r'^(feat|fix|docs|style|refactor|test|chore|perf)(\(.+?\))?:', subject)
        if match:
            return match.group(1)

        # Fallback: guess from subject
        subject_lower = subject.lower()
        if 'fix' in subject_lower or 'bug' in subject_lower:
            return 'fix'
        elif 'add' in subject_lower or 'feat' in subject_lower:
            return 'feat'
        elif 'refactor' in subject_lower:
            return 'refactor'
        elif 'test' in subject_lower:
            return 'test'
        elif 'doc' in subject_lower:
            return 'docs'
        else:
            return 'other'

    def _classify_commits(self, commits: List[Dict]):
        """
        Classify commits by size and language.

        Args:
            commits: List of commit dictionaries (modified in place)
        """
        for commit in commits:
            files_changed = commit['metadata']['files_changed']

            # Size classification
            if files_changed <= 2:
                size = 'small'
            elif files_changed <= 10:
                size = 'medium'
            elif files_changed <= 50:
                size = 'large'
            else:
                size = 'xlarge'

            # Language classification
            extensions = [f['extension'] for f in commit['files']]
            languages = set()

            for ext in extensions:
                if ext in ['.py']:
                    languages.add('python')
                elif ext in ['.js', '.jsx']:
                    languages.add('javascript')
                elif ext in ['.ts', '.tsx']:
                    languages.add('typescript')
                elif ext in ['.md', '.txt', '.rst']:
                    languages.add('docs')
                elif ext in ['.json', '.yaml', '.yml', '.toml']:
                    languages.add('config')

            # Determine primary language
            if len(languages) == 0:
                primary_language = 'other'
            elif len(languages) == 1:
                primary_language = list(languages)[0]
            else:
                # Multiple languages - prioritize code over docs/config
                if 'python' in languages:
                    primary_language = 'python'
                elif 'javascript' in languages:
                    primary_language = 'javascript'
                elif 'typescript' in languages:
                    primary_language = 'typescript'
                else:
                    primary_language = 'mixed'

            commit['classification'] = {
                'size': size,
                'languages': list(languages),
                'primary_language': primary_language
            }

    def save_commits(self, commits: List[Dict], output_file: str):
        """
        Save commits to JSON file.

        Args:
            commits: List of commit dictionaries
            output_file: Output file path
        """
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'repository': str(self.repo_path),
            'collected_at': datetime.now().isoformat(),
            'total_commits': len(commits),
            'commits': commits
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\n💾 Saved commits to: {output_file}")

    def print_summary(self, commits: List[Dict]):
        """
        Print summary of collected commits.

        Args:
            commits: List of commit dictionaries
        """
        print("\n" + "=" * 70)
        print("📊 COLLECTION SUMMARY")
        print("=" * 70)

        # Count by size
        size_counts = {'small': 0, 'medium': 0, 'large': 0, 'xlarge': 0}
        for commit in commits:
            size = commit['classification']['size']
            size_counts[size] += 1

        print(f"\n📏 By Size:")
        print(f"   Small (1-2 files):    {size_counts['small']:>3} commits")
        print(f"   Medium (3-10 files):  {size_counts['medium']:>3} commits")
        print(f"   Large (11-50 files):  {size_counts['large']:>3} commits")
        print(f"   XLarge (50+ files):   {size_counts['xlarge']:>3} commits")

        # Count by language
        lang_counts = {}
        for commit in commits:
            lang = commit['classification']['primary_language']
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        print(f"\n🌐 By Primary Language:")
        for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
            print(f"   {lang.capitalize():<15} {count:>3} commits")

        # Count by type
        type_counts = {}
        for commit in commits:
            ctype = commit['metadata']['commit_type']
            type_counts[ctype] = type_counts.get(ctype, 0) + 1

        print(f"\n📝 By Commit Type:")
        for ctype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            print(f"   {ctype.capitalize():<15} {count:>3} commits")

        # Total changes
        total_insertions = sum(c['metadata']['insertions'] for c in commits)
        total_deletions = sum(c['metadata']['deletions'] for c in commits)

        print(f"\n📈 Total Changes:")
        print(f"   Insertions: +{total_insertions:,}")
        print(f"   Deletions:  -{total_deletions:,}")
        print(f"   Net:        {total_insertions - total_deletions:+,}")

        print("\n" + "=" * 70)


def main():
    """CLI for commit collector."""
    import argparse

    parser = argparse.ArgumentParser(description='Collect commits for benchmarking')
    parser.add_argument(
        '--repo',
        default='.',
        help='Repository path (default: current directory)'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=30,
        help='Number of commits to collect (default: 30)'
    )
    parser.add_argument(
        '--output',
        default='data/commits.json',
        help='Output file path (default: data/commits.json)'
    )

    args = parser.parse_args()

    try:
        collector = CommitCollector(args.repo)
        commits = collector.collect_commits(count=args.count)
        collector.print_summary(commits)
        collector.save_commits(commits, args.output)

        print(f"\n✅ Collection complete!")
        print(f"   Next: Run analysis with: python benchmark_research.py analyze")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == '__main__':
    main()

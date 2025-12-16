#!/usr/bin/env python3
"""
Performance benchmark for semantic analysis.

This script measures the performance of semantic diff analysis across
different file counts and processing modes (sequential vs parallel).
"""

import time
import subprocess
import tempfile
import os
import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gai.semantic_analyzer import SemanticAnalyzer
from gai.utils import estimate_tokens


class BenchmarkRunner:
    """Run performance benchmarks for semantic analysis."""

    def __init__(self):
        self.results = []
        self.analyzer = SemanticAnalyzer()

    def create_test_file(self, filepath: str, language: str, num_functions: int = 5):
        """
        Create a test file with specified number of functions.

        Args:
            filepath: Path to create file
            language: 'python', 'javascript', or 'typescript'
            num_functions: Number of functions to generate
        """
        if language == 'python':
            content = self._generate_python_code(num_functions)
        elif language == 'javascript':
            content = self._generate_javascript_code(num_functions)
        elif language == 'typescript':
            content = self._generate_typescript_code(num_functions)
        else:
            raise ValueError(f"Unsupported language: {language}")

        with open(filepath, 'w') as f:
            f.write(content)

    def _generate_python_code(self, num_functions: int) -> str:
        """Generate Python code with specified number of functions."""
        code = "\"\"\"Test module for benchmarking.\"\"\"\n\n"
        code += "import os\nimport sys\nfrom typing import List, Dict\n\n"

        for i in range(num_functions):
            code += f"""
def function_{i}(param1: str, param2: int) -> Dict:
    \"\"\"Function {i} for testing.\"\"\"
    result = {{'param1': param1, 'param2': param2}}
    return result

"""

        code += f"""
class TestClass:
    \"\"\"Test class with methods.\"\"\"

    def __init__(self):
        self.value = 0

"""
        for i in range(3):
            code += f"""    def method_{i}(self):
        \"\"\"Method {i}.\"\"\"
        return self.value + {i}

"""
        return code

    def _generate_javascript_code(self, num_functions: int) -> str:
        """Generate JavaScript code with specified number of functions."""
        code = "// Test module for benchmarking\n\n"
        code += "import React from 'react';\nimport axios from 'axios';\n\n"

        for i in range(num_functions):
            code += f"""
function function_{i}(param1, param2) {{
    return {{ param1, param2 }};
}}

"""

        code += f"""
class TestClass {{
    constructor() {{
        this.value = 0;
    }}

"""
        for i in range(3):
            code += f"""    method_{i}() {{
        return this.value + {i};
    }}

"""
        code += "}\n"
        return code

    def _generate_typescript_code(self, num_functions: int) -> str:
        """Generate TypeScript code with specified number of functions."""
        code = "// Test module for benchmarking\n\n"
        code += "import React from 'react';\nimport axios from 'axios';\n\n"

        code += """
interface TestInterface {
    id: number;
    name: string;
}

"""

        for i in range(num_functions):
            code += f"""
function function_{i}(param1: string, param2: number): TestInterface {{
    return {{ id: param2, name: param1 }};
}}

"""

        code += """
class TestClass {
    private value: number = 0;

"""
        for i in range(3):
            code += f"""    method_{i}(): number {{
        return this.value + {i};
    }}

"""
        code += "}\n"
        return code

    def setup_git_repo(self, temp_dir: str, file_count: int, language: str):
        """
        Set up a temporary git repository with test files.

        Args:
            temp_dir: Temporary directory path
            file_count: Number of files to create
            language: Language for test files
        """
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=temp_dir, capture_output=True)

        # Create initial files
        ext_map = {'python': 'py', 'javascript': 'js', 'typescript': 'ts'}
        ext = ext_map[language]

        for i in range(file_count):
            filepath = os.path.join(temp_dir, f'file_{i}.{ext}')
            self.create_test_file(filepath, language, num_functions=3)

        # Initial commit
        subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=temp_dir, capture_output=True)

        # Modify files
        for i in range(file_count):
            filepath = os.path.join(temp_dir, f'file_{i}.{ext}')
            self.create_test_file(filepath, language, num_functions=5)  # More functions

        # Stage changes
        subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)

    def benchmark_file_count(self, file_count: int, language: str = 'python'):
        """
        Benchmark semantic analysis with specified file count.

        Args:
            file_count: Number of files to analyze
            language: Language for test files

        Returns:
            Dict with benchmark results
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup
            self.setup_git_repo(temp_dir, file_count, language)

            # Change to temp directory
            original_dir = os.getcwd()
            os.chdir(temp_dir)

            try:
                # Measure semantic analysis time
                start_time = time.time()
                result = self.analyzer.analyze_diff()
                elapsed_time = time.time() - start_time

                # Get traditional diff for comparison
                diff_result = subprocess.run(
                    ['git', 'diff', '--staged'],
                    capture_output=True,
                    text=True
                )
                raw_diff = diff_result.stdout

                # Calculate metrics
                semantic_summary = self.analyzer.format_for_ai(result)

                raw_tokens = estimate_tokens(raw_diff)
                semantic_tokens = estimate_tokens(semantic_summary)
                token_reduction = ((raw_tokens - semantic_tokens) / raw_tokens * 100) if raw_tokens > 0 else 0

                return {
                    'file_count': file_count,
                    'language': language,
                    'elapsed_time': elapsed_time,
                    'changes_detected': len(result['changes']),
                    'raw_tokens': raw_tokens,
                    'semantic_tokens': semantic_tokens,
                    'token_reduction_percent': token_reduction,
                    'processing_mode': 'parallel' if file_count > 5 else 'sequential'
                }

            finally:
                os.chdir(original_dir)

    def run_benchmarks(self):
        """Run full benchmark suite."""
        print("🚀 Starting Semantic Analysis Performance Benchmark\n")
        print("=" * 70)

        # Test different file counts
        file_counts = [1, 3, 5, 10, 20, 50]
        languages = ['python', 'javascript', 'typescript']

        for language in languages:
            print(f"\n📊 Benchmarking {language.upper()} files:")
            print("-" * 70)

            for count in file_counts:
                print(f"  Testing {count} file{'s' if count > 1 else ''}...", end=' ', flush=True)

                # Run benchmark 3 times and take average
                times = []
                token_reductions = []

                for _ in range(3):
                    result = self.benchmark_file_count(count, language)
                    times.append(result['elapsed_time'])
                    token_reductions.append(result['token_reduction_percent'])

                avg_time = sum(times) / len(times)
                avg_reduction = sum(token_reductions) / len(token_reductions)

                # Update result with averages
                result['elapsed_time'] = avg_time
                result['token_reduction_percent'] = avg_reduction

                self.results.append(result)

                mode = result['processing_mode']
                print(f"✓ {avg_time:.3f}s ({mode}, {avg_reduction:.1f}% token reduction)")

        print("\n" + "=" * 70)
        self.print_summary()
        self.save_results()

    def print_summary(self):
        """Print benchmark summary."""
        print("\n📈 BENCHMARK SUMMARY")
        print("=" * 70)

        # Group by language
        by_language = {}
        for result in self.results:
            lang = result['language']
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(result)

        for language, results in by_language.items():
            print(f"\n{language.upper()}:")
            print(f"{'Files':<8} {'Time (s)':<12} {'Mode':<12} {'Raw Tokens':<12} {'Semantic':<12} {'Reduction'}")
            print("-" * 70)

            for r in results:
                print(
                    f"{r['file_count']:<8} "
                    f"{r['elapsed_time']:<12.3f} "
                    f"{r['processing_mode']:<12} "
                    f"{r['raw_tokens']:<12} "
                    f"{r['semantic_tokens']:<12} "
                    f"{r['token_reduction_percent']:.1f}%"
                )

        # Calculate speedup for parallel processing
        print("\n⚡ PARALLEL PROCESSING SPEEDUP:")
        print("-" * 70)

        for language in by_language.keys():
            results = by_language[language]

            # Find sequential baseline (5 files)
            sequential = next((r for r in results if r['file_count'] == 5), None)
            if not sequential:
                continue

            # Compare with parallel results
            for result in results:
                if result['file_count'] > 5:
                    # Estimate what sequential would have taken (linear scaling)
                    estimated_sequential = (sequential['elapsed_time'] / 5) * result['file_count']
                    actual_parallel = result['elapsed_time']
                    speedup = estimated_sequential / actual_parallel if actual_parallel > 0 else 1

                    print(
                        f"{language:<12} {result['file_count']:>3} files: "
                        f"{speedup:.2f}x speedup "
                        f"(est. {estimated_sequential:.2f}s → actual {actual_parallel:.2f}s)"
                    )

    def save_results(self):
        """Save benchmark results to JSON file."""
        output_file = 'benchmark_results.json'

        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'results': self.results
            }, f, indent=2)

        print(f"\n💾 Results saved to {output_file}")


def main():
    """Run benchmarks."""
    runner = BenchmarkRunner()

    try:
        runner.run_benchmarks()
    except KeyboardInterrupt:
        print("\n\n⚠️  Benchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

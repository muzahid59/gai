# Benchmark Research Suite

Comprehensive performance comparison between **semantic diff analysis** and **traditional git diff** approaches for AI-powered commit message generation.

## Overview

This benchmark suite evaluates the performance, cost-efficiency, and token reduction of semantic analysis compared to traditional diff analysis across real commits from the repository.

## Quick Start

### Run Complete Benchmark

```bash
# From project root
python benchmark_research/run_benchmark.py
```

This will:
1. ✅ Collect 30 commits from the repository
2. ✅ Run both traditional and semantic analysis
3. ✅ Perform statistical analysis
4. ✅ Generate comprehensive markdown report

### View Results

```bash
# View the comprehensive report
cat benchmark_research/results/BENCHMARK_REPORT.md

# Or open in your editor
code benchmark_research/results/BENCHMARK_REPORT.md
```

## Custom Usage

### Analyze More Commits

```bash
python benchmark_research/run_benchmark.py --commits 50
```

### Analyze Different Repository

```bash
python benchmark_research/run_benchmark.py --repo /path/to/repo --commits 100
```

### Custom Output Directory

```bash
python benchmark_research/run_benchmark.py --output my_benchmark
```

## Project Structure

```
benchmark_research/
├── run_benchmark.py          # Master script - runs entire suite
├── collectors/               # Commit data collection
│   ├── commit_collector.py   # Extract commits from git
│   └── __init__.py
├── analyzers/                # Analysis engines
│   ├── traditional_analyzer.py      # Traditional git diff
│   ├── semantic_analyzer_wrapper.py # Semantic approach
│   ├── comparison_engine.py         # Compare both approaches
│   └── __init__.py
├── analysis/                 # Statistical analysis
│   ├── statistical_analyzer.py # Descriptive stats, correlations
│   └── __init__.py
├── reporting/                # Report generation
│   ├── report_generator.py   # Markdown report with visualizations
│   └── __init__.py
├── data/                     # Collected commit data
│   └── commits.json          # Commit metadata and diffs
└── results/                  # Analysis results
    ├── comparison.json           # Raw comparison data
    ├── statistical_analysis.json # Statistical metrics
    └── BENCHMARK_REPORT.md       # Final comprehensive report
```

## Individual Components

### 1. Commit Collection

Collect commits with metadata, diffs, and classifications:

```bash
python -m benchmark_research.collectors.commit_collector \
  --repo . \
  --count 30 \
  --output benchmark_research/data/commits.json
```

**Output:** `commits.json` with:
- Commit metadata (hash, author, date, message)
- File changes (paths, status, extensions)
- Diff stats (insertions, deletions)
- Full git diff content
- Classifications (size, language, type)

### 2. Comparison Analysis

Run both analyzers and compare results:

```bash
python -m benchmark_research.analyzers.comparison_engine \
  --commits benchmark_research/data/commits.json \
  --output benchmark_research/results/comparison.json
```

**Metrics:**
- Token counts (traditional vs semantic)
- Processing time
- Cost estimates
- Token reduction percentages

### 3. Statistical Analysis

Calculate descriptive statistics and identify patterns:

```bash
python -m benchmark_research.analysis.statistical_analyzer \
  --results benchmark_research/results/comparison.json \
  --output benchmark_research/results/statistical_analysis.json
```

**Analysis:**
- Descriptive statistics (mean, median, std dev, quartiles)
- Distribution analysis (token reduction buckets)
- Correlation analysis (files changed vs reduction)
- Outlier detection
- Efficiency rankings

### 4. Report Generation

Generate comprehensive markdown report:

```bash
python -m benchmark_research.reporting.report_generator \
  --comparison benchmark_research/results/comparison.json \
  --statistics benchmark_research/results/statistical_analysis.json \
  --commits benchmark_research/data/commits.json \
  --output benchmark_research/results/BENCHMARK_REPORT.md
```

**Report Sections:**
- Executive Summary
- Methodology
- Results (overall, by size, by language, by type)
- Statistical Analysis
- Visualizations
- Key Findings
- Recommendations
- Conclusion

## Key Results

From our initial benchmark of 30 commits:

- **92.1% average token reduction** (79,297 → 1,537 tokens)
- **98.1% cost savings** ($0.1189 → $0.0023)
- **77,760 tokens saved** across 30 commits
- **Consistent performance** (50% of commits achieve 95-100% reduction)
- **Scales with complexity** (medium commits: 97.1% reduction)

## Commit Classifications

### By Size
- **Small:** 1-2 files changed
- **Medium:** 3-10 files changed
- **Large:** 11-50 files changed
- **XLarge:** 50+ files changed

### By Language
- Python, JavaScript, TypeScript
- Config (JSON, YAML, TOML)
- Docs (Markdown, TXT)
- Other

### By Type
- feat, fix, refactor, docs, chore, test
- Extracted from conventional commit format

## Cost Calculation

- **Token Estimation:** Character count / 4
- **Pricing Model:** GPT-3.5-turbo ($0.0015 per 1K input tokens)
- **Formula:** (tokens / 1000) × $0.0015

## Dependencies

All dependencies are already in `pyproject.toml`:
- Standard library (subprocess, json, statistics, pathlib)
- Project modules (gai.utils for token estimation)

## Extending the Benchmark

### Add New Analysis

1. Create analyzer in `analyzers/`
2. Implement `analyze_commit()` method
3. Return standard result format
4. Add to `comparison_engine.py`

### Custom Metrics

1. Modify `comparison_engine.py` to add metrics
2. Update `statistical_analyzer.py` for new stats
3. Update `report_generator.py` to display results

### Different Cost Models

Update cost calculation in:
- `traditional_analyzer.py`
- `semantic_analyzer_wrapper.py`
- Cost per 1K tokens variable

## Troubleshooting

### "Not a git repository"

Ensure you're running from within a git repository:
```bash
git status  # Should not error
```

### "No commits found"

Adjust filters:
```bash
python -m benchmark_research.collectors.commit_collector --count 50
```

### Import errors

Ensure you're running from project root:
```bash
cd /path/to/own-cli
python benchmark_research/run_benchmark.py
```

## Contributing

To improve the benchmark suite:

1. Add support for more languages
2. Enhance statistical analysis methods
3. Add more visualizations
4. Improve report formatting
5. Add CI/CD integration

## License

Same as main project.

---

**Generated by:** Benchmark Research Suite
**Version:** 1.0.0
**Last Updated:** 2025-12-17

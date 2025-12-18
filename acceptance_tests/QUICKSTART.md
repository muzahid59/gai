# Quick Start Guide

## What Just Happened?

We built a **multi-language commit message accuracy verification framework** that:

✅ Analyzes code diffs to extract ground truth
✅ Parses commit messages to extract claims
✅ Verifies claims against reality
✅ Scores accuracy, completeness, and hallucinations

## Run the Demo

```bash
python3 acceptance_tests/examples/test_python_validation.py
```

**Output:**
```
Test Case 1: GOOD MESSAGE
  Accuracy: 91.7%
  Completeness: 87.5%
  Hallucination Rate: 8.3%
  → EXCELLENT

Test Case 2: VAGUE MESSAGE
  Accuracy: 0%
  Completeness: 0%
  → TOO VAGUE

Test Case 3: HALLUCINATING MESSAGE
  Accuracy: 0%
  Hallucination Rate: 100%
  → DANGEROUS
```

## Supported Languages

| Language | Support Level | Features |
|----------|--------------|----------|
| **Python** | ⭐⭐⭐ Full | Functions, classes, type hints, decorators, docstrings, validation, exceptions |
| **JavaScript/TypeScript** | ⭐⭐⭐ Full | Functions, classes, interfaces, types, async/await, imports/exports |
| **Go** | ⭐⭐⭐ Full | Functions, methods, structs, interfaces, error handling |
| **Other** | ⭐⭐ Fallback | Pattern-based detection (works but less accurate) |

## How It Works

### 1. Ground Truth Extraction

```python
# From this diff:
+def create_user(self, email: str, password: str) -> User:
+    if not email or '@' not in email:
+        raise ValueError("Invalid email")

# We extract:
{
    'function_added': 'create_user',
    'type_hints': ['str', 'User'],
    'validation': ['email format check'],
    'exception': 'ValueError'
}
```

### 2. Claim Extraction

```python
# From this commit message:
"Add email validation and type hints"

# We extract:
[
    Claim(type=ADD, subject='email validation'),
    Claim(type=ADD, subject='type hints')
]
```

### 3. Verification

```python
# We match claims against ground truth:
✓ "email validation" → FOUND (email format check in code)
✓ "type hints" → FOUND (str, User in code)

Score: 100% accurate
```

## Real Examples

### Example 1: Perfect Match

**Diff:** Added email validation
**Message:** "Add email validation"
**Score:** ✅ 100% Accuracy

### Example 2: Incomplete

**Diff:** Added email validation, password validation, type hints
**Message:** "Update user service"
**Score:** ⚠️ 0% Completeness (too vague)

### Example 3: Hallucination

**Diff:** Added email validation
**Message:** "Add OAuth2 and rate limiting"
**Score:** ❌ 100% Hallucination (completely wrong)

## Integration Example

### With Existing Benchmark Suite

```python
# In benchmark_research/run_benchmark.py

from acceptance_tests.test_runner import verify_commit_message

# After generating commit message
accuracy_report = verify_commit_message(diff, message, file_path)

results['accuracy'] = accuracy_report.accuracy_score
results['completeness'] = accuracy_report.completeness_score
results['hallucination_rate'] = accuracy_report.hallucination_rate
```

### As Git Hook

```bash
# .git/hooks/commit-msg
#!/bin/bash
python3 acceptance_tests/test_runner.py \
  --diff "$(git diff --cached)" \
  --message "$(cat $1)" \
  --file "$(git diff --cached --name-only | head -1)"

if [ $? -ne 0 ]; then
  echo "❌ Commit message quality too low"
  exit 1
fi
```

## Next Steps

1. **Try with your own code:**
   ```python
   from acceptance_tests.test_runner import verify_commit_message

   report = verify_commit_message(
       diff="your diff here",
       commit_message="your message here",
       file_path="file.py"
   )

   print(f"Accuracy: {report.accuracy_score}%")
   ```

2. **Add more languages:**
   - Create `rust_analyzer.py`
   - Follow the pattern in `python_analyzer.py`
   - Register with `AnalyzerFactory`

3. **Integrate with benchmarks:**
   - Add accuracy metrics to benchmark reports
   - Compare semantic vs traditional approaches
   - Track accuracy over time

4. **Use in CI/CD:**
   - Fail builds on low-quality commit messages
   - Generate warnings for incomplete messages
   - Track hallucination rates

## Key Metrics

- **Accuracy**: Are the claims true? (Target: >80%)
- **Completeness**: Did it mention important changes? (Target: >70%)
- **Hallucinations**: Did it make stuff up? (Target: <10%)

## Architecture

```
Diff → Language Analyzer → Ground Truth
                                ↓
Commit Message → Claim Extractor → Claims
                                ↓
            Verification Engine
                                ↓
            Accuracy Report (Scores + Details)
```

## What's Different About This Approach?

Most tools just check:
- ❌ Formatting (conventional commits)
- ❌ Length limits
- ❌ Keyword presence

This framework checks:
- ✅ **Factual correctness**
- ✅ **Completeness**
- ✅ **Hallucinations**
- ✅ **Language-aware analysis**

It's like having a code reviewer specifically for commit messages!

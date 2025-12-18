# Acceptance Testing Framework for Commit Message Accuracy

This framework automatically verifies the accuracy of AI-generated commit messages by comparing claims in the message against ground truth extracted from code diffs.

## Overview

The framework follows a three-step process:

1. **Extract Ground Truth** - Analyze the diff using language-specific parsers to determine what actually changed
2. **Extract Claims** - Parse the commit message to identify what it claims changed
3. **Verify** - Match claims against ground truth and score accuracy

## Features

### Multi-Language Support

- ✅ **Python** - Full AST-based analysis with type hints, decorators, docstrings
- ✅ **JavaScript/TypeScript** - Supports ES6+, async/await, interfaces, type annotations
- ✅ **Go** - Structs, interfaces, methods, error handling patterns
- ✅ **Universal Fallback** - Pattern-based analysis for any language

### What We Verify

✅ **Factual Accuracy** - Are the claims true?
✅ **Completeness** - Did it mention important changes?
✅ **Hallucinations** - Did it make stuff up?
✅ **Security Awareness** - Did it mention security fixes?
✅ **Breaking Changes** - Did it warn about API changes?

## Installation

```bash
# No extra dependencies needed - uses Python stdlib
cd acceptance_tests
python3 test_runner.py --help
```

## Usage

### Quick Start

Run the Python validation example:

```bash
python3 acceptance_tests/examples/test_python_validation.py
```

### Verify a Specific Commit Message

```bash
python3 acceptance_tests/test_runner.py \
  --diff path/to/diff.txt \
  --message "feat: add email validation" \
  --file user.py \
  --verbose
```

### Programmatic Usage

```python
from acceptance_tests.analyzers.factory import AnalyzerFactory
from acceptance_tests.extractors.claim_extractor import ClaimExtractor
from acceptance_tests.verifiers.verification_engine import VerificationEngine

# Analyze diff
analyzer = AnalyzerFactory.get_analyzer("file.py")
ground_truth = analyzer.analyze_diff(diff_content, "file.py")

# Extract claims from commit message
extractor = ClaimExtractor()
claims = extractor.extract_claims(commit_message)

# Verify
verifier = VerificationEngine()
report = verifier.verify(claims, ground_truth)

# Check scores
print(f"Accuracy: {report.accuracy_score}%")
print(f"Completeness: {report.completeness_score}%")
print(f"Hallucination Rate: {report.hallucination_rate}%")
```

## Architecture

```
acceptance_tests/
├── analyzers/           # Language-specific code analyzers
│   ├── base.py         # Base analyzer interface
│   ├── python_analyzer.py
│   ├── javascript_analyzer.py
│   ├── go_analyzer.py
│   └── factory.py      # Analyzer selection
│
├── extractors/          # Commit message analysis
│   └── claim_extractor.py
│
├── verifiers/           # Claim verification
│   └── verification_engine.py
│
├── examples/            # Example test cases
│   └── test_python_validation.py
│
└── test_runner.py       # Main CLI tool
```

## How It Works

### Example: Python Validation

**Diff:**
```python
+def create_user(self, email: str, password: str) -> User:
+    """Create a new user with validation."""
+    if not email or '@' not in email:
+        raise ValueError("Invalid email address")
+    if not password or len(password) < 8:
+        raise ValueError("Password must be at least 8 characters")
```

**Ground Truth Extracted:**
- Function modified: `create_user`
- Type hints added: `str`, `User`
- Docstring added
- Validation added: email format check
- Validation added: password length check
- Exception raised: `ValueError`

**Good Commit Message:**
```
fix(auth): add input validation to user creation

- Add email format validation (requires @ symbol)
- Add password length validation (minimum 8 characters)
- Add type hints and docstring
```

**Verification:**
- ✅ "email format validation" → TRUE (found `'@' not in email`)
- ✅ "password length validation" → TRUE (found `len(password) < 8`)
- ✅ "type hints" → TRUE (found `: str`, `-> User`)
- ✅ "docstring" → TRUE (found `"""..."""`)

**Score:** 100% Accuracy, 100% Completeness, 0% Hallucinations

### Example: Hallucinating Message

**Same Diff, Bad Message:**
```
feat(auth): add OAuth2 integration and rate limiting

- Implement OAuth2 authentication flow
- Add Redis caching
```

**Verification:**
- ✗ "OAuth2" → FALSE (no OAuth code in diff)
- ✗ "rate limiting" → FALSE (no rate limit code)
- ✗ "Redis caching" → FALSE (no Redis code)

**Score:** 0% Accuracy, 0% Completeness, 100% Hallucinations

## Scoring System

### Accuracy Score
```
(Verified Claims / Total Claims) × 100
```
Percentage of claims that are factually correct.

### Completeness Score
```
(Mentioned Changes / Total Important Changes) × 100
```
How well the message covers actual code changes.

### Hallucination Rate
```
(False Claims / Total Claims) × 100
```
Percentage of claims that are fabricated.

### Overall Score
```
(Accuracy + Completeness) / 2 - Hallucinations
```
Combined quality metric.

## Extending

### Add a New Language

```python
from acceptance_tests.analyzers.base import LanguageAnalyzer, GroundTruth, CodeChange

class RustAnalyzer(LanguageAnalyzer):
    @property
    def supported_extensions(self):
        return ['.rs']

    @property
    def language_name(self):
        return "Rust"

    def analyze_diff(self, diff_content, file_path):
        # Implement Rust-specific analysis
        truth = GroundTruth(file_path=file_path, language="Rust")
        # ... extract changes ...
        return truth

# Register
from acceptance_tests.analyzers.factory import AnalyzerFactory
AnalyzerFactory.register_analyzer(RustAnalyzer())
```

## Integration with Benchmarking

This framework can be integrated with the existing `benchmark_research/` suite to add accuracy metrics:

```python
from acceptance_tests.test_runner import verify_commit_message

# After generating commit message
report = verify_commit_message(diff, generated_message, file_path)

benchmark_results['accuracy'] = report.accuracy_score
benchmark_results['completeness'] = report.completeness_score
benchmark_results['hallucination_rate'] = report.hallucination_rate
```

## Real-World Applications

1. **CI/CD Quality Gates** - Reject PRs with low-quality commit messages
2. **AI Model Evaluation** - Compare semantic vs traditional approaches
3. **Developer Feedback** - Help humans write better commit messages
4. **Regression Testing** - Ensure commit message quality doesn't degrade

## Future Enhancements

- [ ] Multi-file diff analysis
- [ ] Semantic similarity scoring using embeddings
- [ ] LLM-based claim verification for complex cases
- [ ] Integration with git hooks
- [ ] Historical analysis of repository commits
- [ ] Language-specific best practices checking

## License

Same as parent project.

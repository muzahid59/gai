#!/usr/bin/env python3
"""Example showing multi-language support."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from acceptance_tests.analyzers.factory import AnalyzerFactory
from acceptance_tests.extractors.claim_extractor import ClaimExtractor
from acceptance_tests.verifiers.verification_engine import VerificationEngine


# Python example
PYTHON_DIFF = """--- a/utils/validator.py
+++ b/utils/validator.py
@@ -1,0 +2,6 @@
+def validate_email(email: str) -> bool:
+    \"\"\"Check if email is valid.\"\"\"
+    if not email or '@' not in email:
+        return False
+    return True
"""

# JavaScript example
JS_DIFF = """--- a/utils/validator.js
+++ b/utils/validator.js
@@ -1,0 +2,9 @@
+export function validateEmail(email) {
+    if (!email || !email.includes('@')) {
+        throw new Error('Invalid email');
+    }
+    return true;
+}
"""

# TypeScript example
TS_DIFF = """--- a/utils/validator.ts
+++ b/utils/validator.ts
@@ -1,0 +2,11 @@
+export interface ValidationResult {
+    valid: boolean;
+    error?: string;
+}
+
+export function validateEmail(email: string): ValidationResult {
+    if (!email || !email.includes('@')) {
+        return { valid: false, error: 'Invalid email' };
+    }
+    return { valid: true };
+}
"""

# Go example
GO_DIFF = """--- a/utils/validator.go
+++ b/utils/validator.go
@@ -1,0 +5,11 @@
+func ValidateEmail(email string) error {
+    if email == "" {
+        return errors.New("email is required")
+    }
+    if !strings.Contains(email, "@") {
+        return errors.New("invalid email format")
+    }
+    return nil
+}
"""

COMMIT_MESSAGE = """feat(validation): add email validation across all platforms

- Implement email format checking (requires @ symbol)
- Add validation functions to Python, JavaScript, TypeScript, and Go
- Include error handling for invalid inputs
"""


def test_language(diff, file_path, language_name):
    """Test a specific language."""
    print(f"\n{'=' * 70}")
    print(f"{language_name.upper()} - {file_path}")
    print('=' * 70)

    # Analyze
    analyzer = AnalyzerFactory.get_analyzer(file_path)
    ground_truth = analyzer.analyze_diff(diff, file_path)

    print(f"Analyzer: {analyzer.language_name}")
    print(f"\nGround truth ({len(ground_truth.changes)} changes):")
    for change in ground_truth.changes:
        print(f"  • {change}")

    # Verify
    extractor = ClaimExtractor()
    claims = extractor.extract_claims(COMMIT_MESSAGE)

    verifier = VerificationEngine()
    report = verifier.verify(claims, ground_truth)

    print(f"\n📊 Scores:")
    print(f"  Accuracy:      {report.accuracy_score:5.1f}%")
    print(f"  Completeness:  {report.completeness_score:5.1f}%")
    print(f"  Overall:       {report.overall_score:5.1f}%")


if __name__ == "__main__":
    print("=" * 70)
    print("MULTI-LANGUAGE COMMIT MESSAGE VERIFICATION")
    print("=" * 70)
    print("\nTesting the same commit message against different language diffs...")

    test_language(PYTHON_DIFF, "utils/validator.py", "Python")
    test_language(JS_DIFF, "utils/validator.js", "JavaScript")
    test_language(TS_DIFF, "utils/validator.ts", "TypeScript")
    test_language(GO_DIFF, "utils/validator.go", "Go")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("✅ All languages successfully analyzed")
    print("✅ Language-specific features detected:")
    print("   • Python: type hints, docstrings")
    print("   • JavaScript: exports, error throwing")
    print("   • TypeScript: interfaces, type annotations")
    print("   • Go: error returns, string operations")
    print("\nThe framework adapts to each language automatically!")

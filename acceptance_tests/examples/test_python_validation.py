"""Example test case: Python validation addition."""

# Sample diff for testing
DIFF = """--- a/auth/user.py
+++ b/auth/user.py
@@ -12,7 +12,13 @@ class UserService:
-    def create_user(self, email, password):
-        return self.db.insert(email, password)
+    def create_user(self, email: str, password: str) -> User:
+        \"\"\"Create a new user with validation.\"\"\"
+        if not email or '@' not in email:
+            raise ValueError("Invalid email address")
+        if not password or len(password) < 8:
+            raise ValueError("Password must be at least 8 characters")
+        return self.db.insert(email, password)
"""

# Good commit message
GOOD_MESSAGE = """fix(auth): add input validation to user creation

- Add email format validation (requires @ symbol)
- Add password length validation (minimum 8 characters)
- Add type hints to create_user method
- Add docstring for documentation
- Raise ValueError for invalid inputs
"""

# Bad commit message (vague)
BAD_MESSAGE_VAGUE = """fix(auth): update user service

- Make some improvements to user creation
"""

# Bad message (hallucinating)
BAD_MESSAGE_HALLUCINATION = """feat(auth): add OAuth2 integration and rate limiting

- Implement OAuth2 authentication flow
- Add rate limiting to prevent brute force attacks
- Add Redis caching for user sessions
"""


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Add parent directory to path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from acceptance_tests.analyzers.factory import AnalyzerFactory
    from acceptance_tests.extractors.claim_extractor import ClaimExtractor
    from acceptance_tests.verifiers.verification_engine import VerificationEngine

    # Analyze the diff
    analyzer = AnalyzerFactory.get_analyzer("auth/user.py")
    ground_truth = analyzer.analyze_diff(DIFF, "auth/user.py")

    print("=" * 70)
    print("GROUND TRUTH FROM DIFF ANALYSIS")
    print("=" * 70)
    print(f"File: {ground_truth.file_path}")
    print(f"Language: {ground_truth.language}")
    print(f"\nChanges detected ({len(ground_truth.changes)}):")
    for change in ground_truth.changes:
        print(f"  {change}")

    # Test Case 1: Good message
    print("\n" + "=" * 70)
    print("TEST CASE 1: GOOD COMMIT MESSAGE")
    print("=" * 70)
    print(GOOD_MESSAGE)

    extractor = ClaimExtractor()
    claims = extractor.extract_claims(GOOD_MESSAGE)

    print(f"\nClaims extracted ({len(claims)}):")
    for claim in claims:
        print(f"  {claim}")

    verifier = VerificationEngine()
    report = verifier.verify(claims, ground_truth)

    print(f"\n📊 RESULTS:")
    print(f"  Accuracy: {report.accuracy_score:.1f}%")
    print(f"  Completeness: {report.completeness_score:.1f}%")
    print(f"  Hallucination Rate: {report.hallucination_rate:.1f}%")
    print(f"  Overall Score: {report.overall_score:.1f}%")

    print(f"\n✓ Verified: {report.verified_claims}/{report.total_claims}")
    print(f"✗ False: {report.false_claims}/{report.total_claims}")

    # Test Case 2: Vague message
    print("\n" + "=" * 70)
    print("TEST CASE 2: VAGUE COMMIT MESSAGE")
    print("=" * 70)
    print(BAD_MESSAGE_VAGUE)

    claims = extractor.extract_claims(BAD_MESSAGE_VAGUE)
    print(f"\nClaims extracted ({len(claims)}):")
    for claim in claims:
        print(f"  {claim}")

    report = verifier.verify(claims, ground_truth)

    print(f"\n📊 RESULTS:")
    print(f"  Accuracy: {report.accuracy_score:.1f}%")
    print(f"  Completeness: {report.completeness_score:.1f}%")
    print(f"  Hallucination Rate: {report.hallucination_rate:.1f}%")
    print(f"  Overall Score: {report.overall_score:.1f}%")

    # Test Case 3: Hallucinating message
    print("\n" + "=" * 70)
    print("TEST CASE 3: HALLUCINATING COMMIT MESSAGE")
    print("=" * 70)
    print(BAD_MESSAGE_HALLUCINATION)

    claims = extractor.extract_claims(BAD_MESSAGE_HALLUCINATION)
    print(f"\nClaims extracted ({len(claims)}):")
    for claim in claims:
        print(f"  {claim}")

    report = verifier.verify(claims, ground_truth)

    print(f"\n📊 RESULTS:")
    print(f"  Accuracy: {report.accuracy_score:.1f}%")
    print(f"  Completeness: {report.completeness_score:.1f}%")
    print(f"  Hallucination Rate: {report.hallucination_rate:.1f}%")
    print(f"  Overall Score: {report.overall_score:.1f}%")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("✓ Good message: High accuracy, high completeness, low hallucinations")
    print("⚠ Vague message: Low completeness (misses details)")
    print("✗ Hallucinating message: Low accuracy, high hallucination rate")

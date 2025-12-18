"""
Acceptance Testing Framework for Commit Message Accuracy Verification.

This framework verifies the accuracy of AI-generated commit messages by:
1. Extracting ground truth from code diffs (language-specific analysis)
2. Extracting claims from commit messages
3. Verifying claims against ground truth
4. Scoring accuracy, completeness, and hallucinations
"""

__version__ = "0.1.0"

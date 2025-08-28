import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai.utils import estimate_tokens, split_diff_by_files, aggregate_commit_messages


def test_estimate_tokens():
    """Test token estimation."""
    text = "Hello world"  # 11 chars
    tokens = estimate_tokens(text)
    assert tokens == 2  # 11 // 4 = 2


def test_split_diff_by_files():
    """Test diff splitting by files."""
    large_diff = """--- a/file1.py
+++ b/file1.py
@@ -1,3 +1,4 @@
 def function1():
+    # New comment
     return True

--- a/file2.py
+++ b/file2.py
@@ -1,2 +1,3 @@
 def function2():
+    # Another comment
     return False"""
    
    chunks = split_diff_by_files(large_diff, max_tokens_per_chunk=50)
    assert len(chunks) >= 1
    assert all(estimate_tokens(chunk) <= 60 for chunk in chunks)  # Allow some variance


def test_aggregate_commit_messages():
    """Test message aggregation."""
    messages = [
        "feat(auth): add login system\n\n- implement JWT authentication\n- add password hashing",
        "fix(auth): resolve validation bug\n\n- fix email validation regex"
    ]
    
    result = aggregate_commit_messages(messages)
    assert result.startswith("feat(auth):")
    assert "multiple improvements" in result or "add login system" in result
    
    # Test oneline
    oneline_result = aggregate_commit_messages(messages, oneline=True)
    assert "\n" not in oneline_result


def test_aggregate_single_message():
    """Test aggregation with single message."""
    messages = ["feat: add new feature"]
    result = aggregate_commit_messages(messages)
    assert result == "feat: add new feature"


def test_aggregate_empty_messages():
    """Test aggregation with empty messages."""
    messages = []
    result = aggregate_commit_messages(messages)
    assert result == ""


def test_commit_type_priority():
    """Test that commit types are prioritized correctly in case of ties."""
    # Test feat vs fix (feat should win)
    messages = ["feat: add feature", "fix: fix bug"]
    result = aggregate_commit_messages(messages, oneline=True)
    assert result.startswith("feat:")
    
    # Test fix vs chore (fix should win)
    messages = ["fix: fix bug", "chore: update deps"]
    result = aggregate_commit_messages(messages, oneline=True)
    assert result.startswith("fix:")


def test_split_diff_respects_file_boundaries():
    """Test that diff splitting respects file boundaries."""
    diff_with_files = """--- a/small.py
+++ b/small.py
@@ -1,2 +1,3 @@
 def small():
+    # comment
     pass

--- a/large.py
+++ b/large.py
@@ -1,10 +1,20 @@
 def large_function():
+    # many
+    # new
+    # lines
+    # of
+    # comments
+    # and
+    # code
+    # changes
+    # here
     pass"""
    
    chunks = split_diff_by_files(diff_with_files, max_tokens_per_chunk=30)
    # Should create at least 2 chunks due to file boundaries
    assert len(chunks) >= 2

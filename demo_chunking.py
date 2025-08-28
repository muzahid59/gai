#!/usr/bin/env python3
"""
Demo script to test the chunking functionality with a large synthetic diff.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gai.utils import estimate_tokens, split_diff_by_files, aggregate_commit_messages


def create_large_diff():
    """Create a synthetic large diff for testing."""
    diff_parts = []
    
    # Add multiple files with changes
    for i in range(5):
        diff_parts.append(f"""--- a/file{i}.py
+++ b/file{i}.py
@@ -1,10 +1,15 @@
 import os
 import sys
 
 def function{i}():
+    # Added new comment for function {i}
+    # This is a significant change
     old_code = "previous implementation"
+    new_code = "improved implementation"
+    refactored_logic = True
     
     if old_code:
+        # Process the new logic
         return True
+    return new_code
 
""")
    
    return "\n".join(diff_parts)


def demo_chunking():
    """Demonstrate the chunking functionality."""
    print("=== Chunking Demo ===\n")
    
    # Create a large diff
    large_diff = create_large_diff()
    total_tokens = estimate_tokens(large_diff)
    
    print(f"Generated synthetic diff with {total_tokens} tokens")
    print(f"Diff preview (first 200 chars):\n{large_diff[:200]}...\n")
    
    # Test chunking with small limit
    max_tokens = 150
    print(f"Splitting diff with max_tokens_per_chunk = {max_tokens}")
    chunks = split_diff_by_files(large_diff, max_tokens_per_chunk=max_tokens)
    
    print(f"Split into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        chunk_tokens = estimate_tokens(chunk)
        print(f"  Chunk {i+1}: {chunk_tokens} tokens")
    
    # Demo message aggregation
    print("\n=== Message Aggregation Demo ===\n")
    
    sample_messages = [
        "feat(auth): add user authentication\n\n- implement JWT tokens\n- add login endpoint",
        "feat(api): add new endpoints\n\n- create user profile API\n- add data validation",
        "fix(auth): resolve token issues\n\n- fix token expiration\n- improve error handling"
    ]
    
    print("Individual messages:")
    for i, msg in enumerate(sample_messages):
        print(f"  {i+1}. {msg.split(chr(10))[0]}")
    
    # Aggregate
    aggregated = aggregate_commit_messages(sample_messages)
    print(f"\nAggregated message:\n{aggregated}")
    
    # Test oneline
    oneline = aggregate_commit_messages(sample_messages, oneline=True)
    print(f"\nOneline version:\n{oneline}")


if __name__ == "__main__":
    demo_chunking()

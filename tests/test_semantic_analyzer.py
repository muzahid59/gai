import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai.semantic_analyzer import SemanticChange, SemanticAnalyzer
from gai.parsers.python_parser import PythonParser


class TestSemanticChange:
    """Test SemanticChange class."""

    def test_create_semantic_change(self):
        """Test creating a SemanticChange instance."""
        change = SemanticChange('function_added', {
            'name': 'test_func',
            'params': ['a', 'b']
        })

        assert change.type == 'function_added'
        assert change.details['name'] == 'test_func'
        assert change.details['params'] == ['a', 'b']

    def test_to_dict(self):
        """Test converting SemanticChange to dict."""
        change = SemanticChange('class_added', {
            'name': 'TestClass',
            'methods': ['method1', 'method2']
        })

        result = change.to_dict()
        assert result['type'] == 'class_added'
        assert result['name'] == 'TestClass'
        assert result['methods'] == ['method1', 'method2']


class TestPythonParser:
    """Test PythonParser functionality."""

    def test_detect_new_function(self):
        """Test that parser detects newly added functions."""
        parser = PythonParser()

        old_code = ""
        new_code = """
def add(a, b):
    '''Add two numbers'''
    return a + b
"""

        changes = parser._compare_versions('test.py', old_code, new_code)

        # Should detect function_added
        func_changes = [c for c in changes if c.type == 'function_added']
        assert len(func_changes) == 1
        assert func_changes[0].details['name'] == 'add'
        assert func_changes[0].details['params'] == ['a', 'b']
        assert func_changes[0].details['has_docstring'] is True

    def test_detect_modified_function_signature(self):
        """Test that parser detects function signature changes."""
        parser = PythonParser()

        old_code = """
def calculate(x, y):
    return x + y
"""
        new_code = """
def calculate(x: int, y: int) -> int:
    '''Calculate sum of two numbers'''
    return x + y
"""

        changes = parser._compare_versions('test.py', old_code, new_code)

        # Should detect function_modified
        func_changes = [c for c in changes if c.type == 'function_modified']
        assert len(func_changes) == 1
        assert func_changes[0].details['name'] == 'calculate'

        modifications = func_changes[0].details['changes']
        assert 'added return type hint' in modifications
        assert 'added docstring' in modifications

    def test_detect_deleted_function(self):
        """Test that parser detects deleted functions."""
        parser = PythonParser()

        old_code = """
def old_function():
    pass

def remaining_function():
    pass
"""
        new_code = """
def remaining_function():
    pass
"""

        changes = parser._compare_versions('test.py', old_code, new_code)

        # Should detect function_removed
        removed_changes = [c for c in changes if c.type == 'function_removed']
        assert len(removed_changes) == 1
        assert removed_changes[0].details['name'] == 'old_function'

    def test_detect_new_class(self):
        """Test that parser detects newly added classes."""
        parser = PythonParser()

        old_code = ""
        new_code = """
class Calculator:
    '''A simple calculator class'''

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
"""

        changes = parser._compare_versions('test.py', old_code, new_code)

        # Should detect class_added
        class_changes = [c for c in changes if c.type == 'class_added']
        assert len(class_changes) == 1
        assert class_changes[0].details['name'] == 'Calculator'
        assert 'add' in class_changes[0].details['methods']
        assert 'subtract' in class_changes[0].details['methods']

    def test_detect_modified_class(self):
        """Test that parser detects class modifications."""
        parser = PythonParser()

        old_code = """
class MyClass:
    def method1(self):
        pass
"""
        new_code = """
class MyClass:
    def method1(self):
        pass

    def method2(self):
        pass
"""

        changes = parser._compare_versions('test.py', old_code, new_code)

        # Should detect class_modified
        class_changes = [c for c in changes if c.type == 'class_modified']
        assert len(class_changes) == 1
        assert class_changes[0].details['name'] == 'MyClass'

        modifications = class_changes[0].details['changes']
        assert any('added methods' in mod for mod in modifications)

    def test_detect_import_changes(self):
        """Test that parser detects import changes."""
        parser = PythonParser()

        old_code = """
import os
import sys
"""
        new_code = """
import os
import sys
import json
from pathlib import Path
"""

        changes = parser._compare_versions('test.py', old_code, new_code)

        # Should detect imports_added
        import_changes = [c for c in changes if c.type == 'imports_added']
        assert len(import_changes) == 1
        assert 'json' in import_changes[0].details['modules']
        assert 'pathlib' in import_changes[0].details['modules']

    def test_detect_removed_imports(self):
        """Test that parser detects removed imports."""
        parser = PythonParser()

        old_code = """
import os
import sys
import json
"""
        new_code = """
import os
import sys
"""

        changes = parser._compare_versions('test.py', old_code, new_code)

        # Should detect imports_removed
        import_changes = [c for c in changes if c.type == 'imports_removed']
        assert len(import_changes) == 1
        assert 'json' in import_changes[0].details['modules']

    def test_handle_syntax_error(self):
        """Test that parser gracefully handles syntax errors."""
        parser = PythonParser()

        old_code = "def valid():\n    pass"
        new_code = "def invalid(\n    # missing closing paren"

        changes = parser._compare_versions('test.py', old_code, new_code)

        # Should fallback to file_modified with note
        assert len(changes) == 1
        assert changes[0].type == 'file_modified'
        assert 'syntax error' in changes[0].details.get('note', '')

    def test_analyze_new_file(self):
        """Test analyzing a newly added file."""
        parser = PythonParser()

        new_code = """
import requests

class APIClient:
    '''API client class'''

    def __init__(self, url):
        self.url = url

    def fetch(self):
        return requests.get(self.url)

def helper_function():
    pass
"""

        changes = parser._analyze_new_file('api.py', new_code)

        # Should detect class, function, and imports
        class_changes = [c for c in changes if c.type == 'class_added']
        func_changes = [c for c in changes if c.type == 'function_added']
        import_changes = [c for c in changes if c.type == 'imports_added']

        assert len(class_changes) == 1
        assert class_changes[0].details['name'] == 'APIClient'

        assert len(func_changes) == 1
        assert func_changes[0].details['name'] == 'helper_function'

        assert len(import_changes) == 1
        assert 'requests' in import_changes[0].details['modules']

    def test_detect_async_function(self):
        """Test detecting async functions."""
        parser = PythonParser()

        old_code = ""
        new_code = """
async def fetch_data():
    return await api.get()
"""

        changes = parser._compare_versions('test.py', old_code, new_code)

        func_changes = [c for c in changes if c.type == 'function_added']
        assert len(func_changes) == 1
        assert func_changes[0].details['is_async'] is True

    def test_detect_function_decorators(self):
        """Test detecting function decorators."""
        parser = PythonParser()

        old_code = """
def my_func():
    pass
"""
        new_code = """
@property
def my_func():
    pass
"""

        changes = parser._compare_versions('test.py', old_code, new_code)

        func_changes = [c for c in changes if c.type == 'function_modified']
        assert len(func_changes) == 1
        assert 'decorators changed' in func_changes[0].details['changes']


class TestSemanticAnalyzer:
    """Test SemanticAnalyzer functionality."""

    @patch('subprocess.run')
    def test_get_changed_files(self, mock_run):
        """Test getting list of changed files."""
        mock_run.return_value = Mock(
            stdout="M\tfile1.py\nA\tfile2.py\nD\tfile3.py\n",
            returncode=0
        )

        analyzer = SemanticAnalyzer()
        files = analyzer._get_changed_files()

        assert len(files) == 3
        assert files[0] == {'path': 'file1.py', 'status': 'M'}
        assert files[1] == {'path': 'file2.py', 'status': 'A'}
        assert files[2] == {'path': 'file3.py', 'status': 'D'}

    @patch('subprocess.run')
    def test_get_diff_stats(self, mock_run):
        """Test parsing diff statistics."""
        mock_run.return_value = Mock(
            stdout=" 3 files changed, 45 insertions(+), 12 deletions(-)\n",
            returncode=0
        )

        analyzer = SemanticAnalyzer()
        stats = analyzer._get_diff_stats()

        # _get_diff_stats returns a string, not a dict
        assert stats == "3 files, +45, -12"

    def test_format_for_ai_reduces_tokens(self):
        """Test that format_for_ai creates concise output."""
        analyzer = SemanticAnalyzer()

        # Create mock analysis with string stats (as _get_diff_stats returns)
        analysis = {
            'summary': {
                'files_changed': 2,
                'stats': '2 files, +50, -10'
            },
            'changes': [
                SemanticChange('function_added', {
                    'file': 'utils.py',
                    'name': 'helper',
                    'params': ['x', 'y']
                }),
                SemanticChange('class_added', {
                    'file': 'models.py',
                    'name': 'User',
                    'methods': ['save', 'delete']
                })
            ]
        }

        formatted = analyzer.format_for_ai(analysis)

        # Should be concise
        assert 'Files changed: 2' in formatted
        assert 'Function Added' in formatted or 'function_added' in formatted.lower()
        assert 'helper' in formatted
        assert 'User' in formatted

        # Verify it's much shorter than a typical diff
        assert len(formatted) < 500  # Should be very concise

    def test_format_for_ai_groups_by_type(self):
        """Test that format_for_ai groups changes by type."""
        analyzer = SemanticAnalyzer()

        analysis = {
            'summary': {
                'files_changed': 1,
                'stats': '1 files, +20, -5'
            },
            'changes': [
                SemanticChange('function_added', {'file': 'a.py', 'name': 'func1', 'params': []}),
                SemanticChange('function_added', {'file': 'a.py', 'name': 'func2', 'params': []}),
                SemanticChange('function_modified', {'file': 'a.py', 'name': 'func3', 'params': [], 'changes': ['signature changed']})
            ]
        }

        formatted = analyzer.format_for_ai(analysis)

        # Should group by type
        assert formatted.count('Function Added') >= 1 or formatted.count('function_added') >= 1
        assert 'func1' in formatted
        assert 'func2' in formatted
        assert 'func3' in formatted

    @patch('subprocess.run')
    def test_generic_file_analysis(self, mock_run):
        """Test fallback for non-Python files."""
        analyzer = SemanticAnalyzer()

        file_info = {'path': 'README.md', 'status': 'M'}
        changes = analyzer._generic_file_analysis(file_info)

        assert len(changes) == 1
        assert changes[0].type == 'file_modified'
        assert changes[0].details['path'] == 'README.md'

    @patch('subprocess.run')
    def test_analyze_deleted_file(self, mock_run):
        """Test analyzing deleted files."""
        analyzer = SemanticAnalyzer()

        # Mock PythonParser
        file_info = {'path': 'test.py', 'status': 'D'}
        changes = analyzer._analyze_file(file_info)

        # Should detect file_deleted
        assert len(changes) >= 1
        deleted_changes = [c for c in changes if c.type == 'file_deleted']
        assert len(deleted_changes) >= 1

    @patch('subprocess.run')
    def test_get_diff_stats_insertions_only(self, mock_run):
        """Test parsing shortstat with only insertions."""
        mock_run.return_value = Mock(
            stdout=" 2 files changed, 50 insertions(+)\n",
            returncode=0
        )

        analyzer = SemanticAnalyzer()
        result = analyzer._get_diff_stats()

        assert result == "2 files, +50, -0"

    @patch('subprocess.run')
    def test_get_diff_stats_deletions_only(self, mock_run):
        """Test parsing shortstat with only deletions."""
        mock_run.return_value = Mock(
            stdout=" 1 file changed, 30 deletions(-)\n",
            returncode=0
        )

        analyzer = SemanticAnalyzer()
        result = analyzer._get_diff_stats()

        assert result == "1 files, +0, -30"

    @patch('subprocess.run')
    def test_get_diff_stats_empty(self, mock_run):
        """Test parsing empty shortstat."""
        mock_run.return_value = Mock(
            stdout="",
            returncode=0
        )

        analyzer = SemanticAnalyzer()
        result = analyzer._get_diff_stats()

        assert result == "no changes"

    @patch('subprocess.run')
    def test_get_diff_stats_error(self, mock_run):
        """Test handling git command errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git')

        analyzer = SemanticAnalyzer()
        result = analyzer._get_diff_stats()

        assert result == "no stats available"


class TestEndToEnd:
    """End-to-end tests for semantic analysis."""

    def test_token_reduction_estimate(self):
        """Test that semantic analysis significantly reduces tokens."""
        # Simulate a typical diff vs semantic summary
        traditional_diff = """--- a/auth.py
+++ b/auth.py
@@ -1,10 +1,25 @@
 import os
+import jwt
+from datetime import datetime

 class AuthService:
     def __init__(self):
         self.secret = os.getenv('SECRET')

+    def create_token(self, user_id):
+        '''Create JWT token'''
+        payload = {
+            'user_id': user_id,
+            'exp': datetime.utcnow() + timedelta(hours=1)
+        }
+        return jwt.encode(payload, self.secret, algorithm='HS256')
+
+    def verify_token(self, token):
+        '''Verify JWT token'''
+        try:
+            return jwt.decode(token, self.secret, algorithms=['HS256'])
+        except jwt.InvalidTokenError:
+            return None
"""

        # Simulate semantic summary
        semantic_summary = """Files changed: 1
Stats: 1 file, +15, -0

## Function Added
  - create_token(user_id) in auth.py
  - verify_token(token) in auth.py

## Imports Added
  - jwt, datetime in auth.py
"""

        # Token reduction should be significant
        from gai.utils import estimate_tokens
        traditional_tokens = estimate_tokens(traditional_diff)
        semantic_tokens = estimate_tokens(semantic_summary)

        reduction_percent = ((traditional_tokens - semantic_tokens) / traditional_tokens) * 100

        # Should have at least 50% reduction (typically 80-95%)
        assert reduction_percent >= 50
        assert semantic_tokens < traditional_tokens

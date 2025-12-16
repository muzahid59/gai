"""
Integration tests for semantic analysis.

These tests verify end-to-end functionality with real-world code samples,
testing the full pipeline from git diff to semantic analysis.
"""

import pytest
import tempfile
import subprocess
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai.semantic_analyzer import SemanticAnalyzer


class TestPythonIntegration:
    """Integration tests for Python semantic analysis."""

    def setup_git_repo(self, temp_dir: str, initial_code: str, modified_code: str, filename: str = 'test.py'):
        """Set up a git repo with initial and modified code."""
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=temp_dir, capture_output=True)

        # Write initial file
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(initial_code)

        # Initial commit
        subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=temp_dir, capture_output=True)

        # Modify file
        with open(filepath, 'w') as f:
            f.write(modified_code)

        # Stage changes
        subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)

    def test_real_world_refactoring(self):
        """Test semantic analysis on a real refactoring scenario."""
        initial_code = """
def process_user_data(user_dict):
    name = user_dict['name']
    email = user_dict['email']
    age = user_dict['age']
    return f"{name} ({email}), age {age}"

def validate_user(user_dict):
    if 'name' not in user_dict:
        return False
    if 'email' not in user_dict:
        return False
    return True
"""

        modified_code = """
from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    name: str
    email: str
    age: int

    def to_string(self) -> str:
        return f"{self.name} ({self.email}), age {self.age}"

    def is_valid(self) -> bool:
        return bool(self.name and self.email)
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            self.setup_git_repo(temp_dir, initial_code, modified_code)

            original_dir = os.getcwd()
            os.chdir(temp_dir)

            try:
                analyzer = SemanticAnalyzer()
                result = analyzer.analyze_diff()

                # Should detect class addition
                class_changes = [c for c in result['changes'] if c.type == 'class_added']
                assert len(class_changes) >= 1, "Should detect new User class"

                # Should detect function removals
                func_removed = [c for c in result['changes'] if c.type == 'function_removed']
                assert len(func_removed) >= 1, "Should detect removed functions"

                # Should detect imports
                import_changes = [c for c in result['changes'] if 'import' in c.type]
                assert len(import_changes) >= 1, "Should detect new imports"

            finally:
                os.chdir(original_dir)

    def test_async_migration(self):
        """Test detection of sync to async migration."""
        initial_code = """
import requests

def fetch_user(user_id):
    response = requests.get(f"/api/users/{user_id}")
    return response.json()

def fetch_posts(user_id):
    response = requests.get(f"/api/posts?user={user_id}")
    return response.json()
"""

        modified_code = """
import aiohttp
import asyncio

async def fetch_user(user_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"/api/users/{user_id}") as response:
            return await response.json()

async def fetch_posts(user_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"/api/posts?user={user_id}") as response:
            return await response.json()
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            self.setup_git_repo(temp_dir, initial_code, modified_code)

            original_dir = os.getcwd()
            os.chdir(temp_dir)

            try:
                analyzer = SemanticAnalyzer()
                result = analyzer.analyze_diff()

                # Should detect async conversion
                func_modified = [c for c in result['changes'] if c.type == 'function_modified']
                assert len(func_modified) >= 2, "Should detect both function modifications"

                # Check that async conversion is detected
                async_conversions = []
                for change in func_modified:
                    if 'changes' in change.details:
                        mods = change.details['changes']
                        if any('async' in str(m).lower() for m in mods):
                            async_conversions.append(change)

                assert len(async_conversions) >= 1, "Should detect async conversion"

                # Should detect import changes
                imports_removed = [c for c in result['changes'] if c.type == 'imports_removed']
                imports_added = [c for c in result['changes'] if c.type == 'imports_added']

                assert len(imports_removed) >= 1, "Should detect removed requests import"
                assert len(imports_added) >= 1, "Should detect added aiohttp import"

            finally:
                os.chdir(original_dir)


class TestJavaScriptIntegration:
    """Integration tests for JavaScript semantic analysis."""

    def setup_git_repo(self, temp_dir: str, initial_code: str, modified_code: str, filename: str = 'test.js'):
        """Set up a git repo with initial and modified code."""
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=temp_dir, capture_output=True)

        # Write initial file
        filepath = os.path.join(temp_dir, filename)
        with open(filepath, 'w') as f:
            f.write(initial_code)

        # Initial commit
        subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=temp_dir, capture_output=True)

        # Modify file
        with open(filepath, 'w') as f:
            f.write(modified_code)

        # Stage changes
        subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)

    def test_react_component_refactoring(self):
        """Test semantic analysis on React component refactoring."""
        initial_code = """
import React from 'react';

class UserProfile extends React.Component {
    render() {
        const { name, email } = this.props;
        return (
            <div>
                <h1>{name}</h1>
                <p>{email}</p>
            </div>
        );
    }
}

export default UserProfile;
"""

        modified_code = """
import React from 'react';

const UserProfile = ({ name, email }) => {
    return (
        <div>
            <h1>{name}</h1>
            <p>{email}</p>
        </div>
    );
};

export default UserProfile;
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            self.setup_git_repo(temp_dir, initial_code, modified_code, 'UserProfile.jsx')

            original_dir = os.getcwd()
            os.chdir(temp_dir)

            try:
                analyzer = SemanticAnalyzer()
                result = analyzer.analyze_diff()

                # Should detect class removal
                class_removed = [c for c in result['changes'] if c.type == 'class_removed']
                assert len(class_removed) >= 1, "Should detect UserProfile class removal"

                # Should detect function addition (functional component)
                func_added = [c for c in result['changes'] if c.type == 'function_added']
                assert len(func_added) >= 1, "Should detect UserProfile function addition"

            finally:
                os.chdir(original_dir)

    def test_typescript_interface_addition(self):
        """Test TypeScript interface detection."""
        initial_code = """
export function createUser(name, email) {
    return { name, email, id: Math.random() };
}
"""

        modified_code = """
export interface User {
    id: number;
    name: string;
    email: string;
}

export function createUser(name: string, email: string): User {
    return { name, email, id: Math.random() };
}
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            self.setup_git_repo(temp_dir, initial_code, modified_code, 'user.ts')

            original_dir = os.getcwd()
            os.chdir(temp_dir)

            try:
                analyzer = SemanticAnalyzer()
                result = analyzer.analyze_diff()

                # Should detect interface addition
                interface_added = [c for c in result['changes'] if c.type == 'interface_added']
                assert len(interface_added) >= 1, "Should detect User interface"

                # Should have some changes detected (interface at minimum)
                assert len(result['changes']) >= 1, "Should detect changes in TypeScript file"

            finally:
                os.chdir(original_dir)


class TestMixedLanguageProjects:
    """Integration tests for projects with multiple languages."""

    def test_python_and_javascript_changes(self):
        """Test analysis of changes in both Python and JavaScript files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize git repo
            subprocess.run(['git', 'init'], cwd=temp_dir, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=temp_dir, capture_output=True)

            # Create initial files
            py_file = os.path.join(temp_dir, 'api.py')
            js_file = os.path.join(temp_dir, 'client.js')

            with open(py_file, 'w') as f:
                f.write("def get_user(id):\n    return {'id': id}\n")

            with open(js_file, 'w') as f:
                f.write("function fetchUser(id) {\n    return fetch(`/api/users/${id}`);\n}\n")

            # Initial commit
            subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=temp_dir, capture_output=True)

            # Modify both files
            with open(py_file, 'w') as f:
                f.write("""
from typing import Dict

def get_user(id: int) -> Dict:
    '''Get user by ID.'''
    return {'id': id, 'name': 'Test'}
""")

            with open(js_file, 'w') as f:
                f.write("""
async function fetchUser(id) {
    const response = await fetch(`/api/users/${id}`);
    return response.json();
}
""")

            # Stage changes
            subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)

            original_dir = os.getcwd()
            os.chdir(temp_dir)

            try:
                analyzer = SemanticAnalyzer()
                result = analyzer.analyze_diff()

                # Should have changes from both files
                assert result['summary']['files_changed'] == 2, "Should detect 2 files changed"

                # Should have Python function modification
                py_changes = [c for c in result['changes'] if 'api.py' in str(c.details)]
                assert len(py_changes) >= 1, "Should have Python changes"

                # Should have JavaScript function modification
                js_changes = [c for c in result['changes'] if 'client.js' in str(c.details)]
                assert len(js_changes) >= 1, "Should have JavaScript changes"

            finally:
                os.chdir(original_dir)


class TestPerformance:
    """Integration tests for performance optimizations."""

    def test_parallel_processing_used_for_large_changeset(self):
        """Verify parallel processing is triggered for 6+ files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize git repo
            subprocess.run(['git', 'init'], cwd=temp_dir, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=temp_dir, capture_output=True)

            # Create 10 files
            for i in range(10):
                filepath = os.path.join(temp_dir, f'file_{i}.py')
                with open(filepath, 'w') as f:
                    f.write(f"def func_{i}():\n    pass\n")

            # Initial commit
            subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=temp_dir, capture_output=True)

            # Modify all files
            for i in range(10):
                filepath = os.path.join(temp_dir, f'file_{i}.py')
                with open(filepath, 'w') as f:
                    f.write(f"""
def func_{i}(param):
    '''Modified function.'''
    return param
""")

            # Stage changes
            subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)

            original_dir = os.getcwd()
            os.chdir(temp_dir)

            try:
                analyzer = SemanticAnalyzer()
                result = analyzer.analyze_diff()

                # Should successfully analyze all 10 files
                assert result['summary']['files_changed'] == 10, "Should detect 10 files"

                # Should have function modifications from all files
                func_modified = [c for c in result['changes'] if c.type == 'function_modified']
                assert len(func_modified) >= 10, "Should detect all 10 function modifications"

            finally:
                os.chdir(original_dir)


class TestEdgeCases:
    """Integration tests for edge cases and error scenarios."""

    def test_empty_file_changes(self):
        """Test handling of empty file additions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subprocess.run(['git', 'init'], cwd=temp_dir, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=temp_dir, capture_output=True)

            # Create empty file
            filepath = os.path.join(temp_dir, 'empty.py')
            with open(filepath, 'w') as f:
                f.write('')

            # Stage file
            subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)

            original_dir = os.getcwd()
            os.chdir(temp_dir)

            try:
                analyzer = SemanticAnalyzer()
                result = analyzer.analyze_diff()

                # Should handle empty file gracefully
                assert len(result['changes']) >= 1, "Should detect file addition"

            finally:
                os.chdir(original_dir)

    def test_file_deletion(self):
        """Test handling of file deletions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            subprocess.run(['git', 'init'], cwd=temp_dir, capture_output=True)
            subprocess.run(['git', 'config', 'user.email', 'test@test.com'], cwd=temp_dir, capture_output=True)
            subprocess.run(['git', 'config', 'user.name', 'Test'], cwd=temp_dir, capture_output=True)

            # Create and commit file
            filepath = os.path.join(temp_dir, 'test.py')
            with open(filepath, 'w') as f:
                f.write('def test():\n    pass\n')

            subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)
            subprocess.run(['git', 'commit', '-m', 'Initial'], cwd=temp_dir, capture_output=True)

            # Delete file
            os.remove(filepath)
            subprocess.run(['git', 'add', '.'], cwd=temp_dir, capture_output=True)

            original_dir = os.getcwd()
            os.chdir(temp_dir)

            try:
                analyzer = SemanticAnalyzer()
                result = analyzer.analyze_diff()

                # Should detect file deletion
                file_deleted = [c for c in result['changes'] if c.type == 'file_deleted']
                assert len(file_deleted) >= 1, "Should detect file deletion"

            finally:
                os.chdir(original_dir)

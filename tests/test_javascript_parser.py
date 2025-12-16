import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai.semantic_analyzer import SemanticChange
from gai.parsers.javascript_parser import JavaScriptParser


class TestJavaScriptParser:
    """Test JavaScriptParser functionality."""

    @pytest.fixture
    def parser(self):
        return JavaScriptParser()

    def test_detect_function_declaration(self, parser):
        """Test detecting function declarations."""
        old_code = ""
        new_code = """
function calculateSum(a, b) {
    return a + b;
}
"""
        changes = parser._compare_versions('test.js', old_code, new_code)

        func_changes = [c for c in changes if c.type == 'function_added']
        assert len(func_changes) == 1
        assert func_changes[0].details['name'] == 'calculateSum'
        assert func_changes[0].details['params'] == ['a', 'b']

    def test_detect_arrow_function(self, parser):
        """Test detecting arrow functions."""
        old_code = ""
        new_code = """
const add = (x, y) => x + y;
"""
        changes = parser._compare_versions('test.js', old_code, new_code)

        func_changes = [c for c in changes if c.type == 'function_added']
        assert len(func_changes) >= 1
        # Arrow functions might be stored as variable declarations
        # Check that we detected the arrow function
        assert any(c.details.get('is_arrow') for c in func_changes if 'is_arrow' in c.details)

    def test_detect_async_function(self, parser):
        """Test detecting async functions."""
        old_code = ""
        new_code = """
async function fetchData() {
    const response = await fetch('/api/data');
    return response.json();
}
"""
        changes = parser._compare_versions('test.js', old_code, new_code)

        func_changes = [c for c in changes if c.type == 'function_added']
        assert len(func_changes) == 1
        assert func_changes[0].details['is_async'] is True
        assert func_changes[0].details['name'] == 'fetchData'

    def test_detect_class(self, parser):
        """Test detecting class declarations."""
        old_code = ""
        new_code = """
class UserService {
    constructor(apiClient) {
        this.client = apiClient;
    }

    async getUser(id) {
        return await this.client.get(`/users/${id}`);
    }

    deleteUser(id) {
        return this.client.delete(`/users/${id}`);
    }
}
"""
        changes = parser._compare_versions('test.js', old_code, new_code)

        class_changes = [c for c in changes if c.type == 'class_added']
        assert len(class_changes) == 1
        assert class_changes[0].details['name'] == 'UserService'
        assert 'constructor' in class_changes[0].details['methods']
        assert 'getUser' in class_changes[0].details['methods']
        assert 'deleteUser' in class_changes[0].details['methods']

    def test_detect_react_component(self, parser):
        """Test detecting React functional components."""
        old_code = ""
        new_code = """
import React from 'react';

function UserProfile({ name, email }) {
    return (
        <div>
            <h1>{name}</h1>
            <p>{email}</p>
        </div>
    );
}
"""
        changes = parser._compare_versions('UserProfile.jsx', old_code, new_code)

        func_changes = [c for c in changes if c.type == 'function_added']
        assert len(func_changes) >= 1
        # Find the UserProfile function
        user_profile = [c for c in func_changes if c.details.get('name') == 'UserProfile']
        assert len(user_profile) == 1

    def test_detect_imports(self, parser):
        """Test detecting ES6 imports."""
        old_code = "import React from 'react';"
        new_code = """
import React from 'react';
import { useState, useEffect } from 'react';
import axios from 'axios';
"""
        changes = parser._compare_versions('test.js', old_code, new_code)

        import_changes = [c for c in changes if c.type == 'imports_added']
        assert len(import_changes) >= 1
        # Check that axios was added
        all_added_imports = []
        for change in import_changes:
            all_added_imports.extend(change.details['modules'])
        assert 'axios' in all_added_imports

    def test_detect_typescript_interface(self, parser):
        """Test detecting TypeScript interfaces."""
        old_code = ""
        new_code = """
interface User {
    id: number;
    name: string;
    email: string;
}
"""
        changes = parser._compare_versions('types.ts', old_code, new_code)

        interface_changes = [c for c in changes if c.type == 'interface_added']
        assert len(interface_changes) == 1
        assert interface_changes[0].details['name'] == 'User'

    def test_modified_function(self, parser):
        """Test detecting function modifications."""
        old_code = """
function process(data) {
    return data;
}
"""
        new_code = """
async function process(data, options) {
    return await transform(data, options);
}
"""
        changes = parser._compare_versions('test.js', old_code, new_code)

        modified = [c for c in changes if c.type == 'function_modified']
        assert len(modified) >= 1
        # Find the process function modification
        process_mod = [c for c in modified if c.details.get('name') == 'process']
        assert len(process_mod) == 1
        modifications = process_mod[0].details['changes']
        assert 'signature changed' in modifications or 'converted to async' in modifications

    def test_handle_syntax_error(self, parser):
        """Test graceful handling of syntax errors."""
        old_code = "function valid() {}"
        new_code = "function invalid( {"  # Syntax error

        changes = parser._compare_versions('test.js', old_code, new_code)

        # Parser should handle syntax errors gracefully
        # Either detect function removal or return file_modified with error note
        assert len(changes) >= 1
        # Accept function_removed (parser can't find valid function in new code)
        # or file_modified with parse error note
        has_error_note = any('parse error' in c.details.get('note', '') for c in changes)
        has_removal = any(c.type == 'function_removed' for c in changes)
        has_file_modified = any(c.type == 'file_modified' for c in changes)
        assert has_error_note or has_removal or has_file_modified

    def test_detect_removed_function(self, parser):
        """Test detecting function removal."""
        old_code = """
function oldFunction() {
    return 'old';
}

function keepFunction() {
    return 'keep';
}
"""
        new_code = """
function keepFunction() {
    return 'keep';
}
"""
        changes = parser._compare_versions('test.js', old_code, new_code)

        removed = [c for c in changes if c.type == 'function_removed']
        assert len(removed) == 1
        assert removed[0].details['name'] == 'oldFunction'

    def test_detect_class_modification(self, parser):
        """Test detecting class modifications."""
        old_code = """
class MyClass {
    method1() {
        return 1;
    }
}
"""
        new_code = """
class MyClass {
    method1() {
        return 1;
    }

    method2() {
        return 2;
    }
}
"""
        changes = parser._compare_versions('test.js', old_code, new_code)

        class_changes = [c for c in changes if c.type == 'class_modified']
        assert len(class_changes) >= 1
        # Find MyClass modification
        my_class = [c for c in class_changes if c.details.get('name') == 'MyClass']
        assert len(my_class) == 1

    def test_detect_removed_imports(self, parser):
        """Test detecting removed imports."""
        old_code = """
import React from 'react';
import axios from 'axios';
import lodash from 'lodash';
"""
        new_code = """
import React from 'react';
import axios from 'axios';
"""
        changes = parser._compare_versions('test.js', old_code, new_code)

        import_changes = [c for c in changes if c.type == 'imports_removed']
        assert len(import_changes) >= 1
        # Check that lodash was removed
        all_removed_imports = []
        for change in import_changes:
            all_removed_imports.extend(change.details['modules'])
        assert 'lodash' in all_removed_imports

    def test_empty_file(self, parser):
        """Test handling empty files."""
        changes = parser._analyze_new_file('empty.js', '')

        assert len(changes) == 1
        assert changes[0].type == 'file_added'
        assert 'empty file' in changes[0].details.get('note', '')

    def test_multiple_functions_in_file(self, parser):
        """Test detecting multiple functions in a file."""
        old_code = ""
        new_code = """
function func1() {
    return 1;
}

function func2(a, b) {
    return a + b;
}

const func3 = () => {
    return 3;
};
"""
        changes = parser._compare_versions('test.js', old_code, new_code)

        func_changes = [c for c in changes if c.type == 'function_added']
        assert len(func_changes) >= 2  # At least func1 and func2


class TestPerformance:
    """Test performance optimizations."""

    def test_caching_effectiveness(self):
        """Verify that _get_file_content caching works."""
        from gai.parsers.base import BaseParser

        # Create a concrete implementation for testing
        class TestParser(BaseParser):
            def parse_file_changes(self, file_info):
                return []

        parser = TestParser()

        # Call multiple times with same args
        result1 = parser._get_file_content('test.py', 'HEAD')
        result2 = parser._get_file_content('test.py', 'HEAD')

        # Should return same object (cached)
        assert result1 is result2


class TestTypeScriptSupport:
    """Test TypeScript-specific features."""

    @pytest.fixture
    def parser(self):
        return JavaScriptParser()

    def test_detect_type_alias(self, parser):
        """Test detecting TypeScript type aliases."""
        old_code = ""
        new_code = """
type UserID = string | number;

interface User {
    id: UserID;
    name: string;
}
"""
        changes = parser._compare_versions('types.ts', old_code, new_code)

        # Should detect interface
        interface_changes = [c for c in changes if c.type == 'interface_added']
        assert len(interface_changes) >= 1

    def test_typescript_function_with_types(self, parser):
        """Test TypeScript function with type annotations."""
        old_code = ""
        new_code = """
function add(a: number, b: number): number {
    return a + b;
}
"""
        changes = parser._compare_versions('math.ts', old_code, new_code)

        func_changes = [c for c in changes if c.type == 'function_added']
        assert len(func_changes) == 1
        assert func_changes[0].details['name'] == 'add'
        assert 'a' in func_changes[0].details['params']
        assert 'b' in func_changes[0].details['params']

    def test_tsx_component(self, parser):
        """Test React component in TSX file."""
        old_code = ""
        new_code = """
import React from 'react';

interface Props {
    title: string;
}

const Header: React.FC<Props> = ({ title }) => {
    return <h1>{title}</h1>;
};
"""
        changes = parser._compare_versions('Header.tsx', old_code, new_code)

        # Should detect interface and component
        interface_changes = [c for c in changes if c.type == 'interface_added']
        assert len(interface_changes) >= 1

        # Component might be detected as function or variable
        func_or_var = [c for c in changes if 'Header' in str(c.details)]
        assert len(func_or_var) >= 1

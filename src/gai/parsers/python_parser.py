"""
Python-specific parser using AST (Abstract Syntax Tree).

This parser analyzes Python files to extract semantic information about
functions, classes, imports, and other code structures.
"""

import ast
from typing import List, Dict, Set
from .base import BaseParser
from gai.semantic_analyzer import SemanticChange
from gai.logger import logger


class PythonParser(BaseParser):
    """Parse Python files using AST."""

    def parse_file_changes(self, file_info: Dict) -> List[SemanticChange]:
        """
        Analyze Python file changes semantically.

        Args:
            file_info: Dict with 'path' and 'status' keys

        Returns:
            List of SemanticChange objects
        """
        filepath = file_info['path']
        status = file_info['status']

        logger.debug(f"Parsing Python file: {filepath} (status: {status})")

        if status == 'D':
            # File deleted
            return [SemanticChange('file_deleted', {'path': filepath})]

        if status == 'A':
            # File added - analyze new content
            new_content = self._get_file_content(filepath, ':0')  # staged content
            if not new_content:
                # Try to read from filesystem
                try:
                    with open(filepath, 'r') as f:
                        new_content = f.read()
                except Exception:
                    pass

            return self._analyze_new_file(filepath, new_content)

        # File modified - compare old vs new
        old_content = self._get_file_content(filepath, 'HEAD')
        new_content = self._get_file_content(filepath, ':0')  # staged content

        if not new_content:
            # Try to read from filesystem
            try:
                with open(filepath, 'r') as f:
                    new_content = f.read()
            except Exception:
                pass

        return self._compare_versions(filepath, old_content, new_content)

    def _analyze_new_file(self, filepath: str, content: str) -> List[SemanticChange]:
        """
        Analyze newly added Python file.

        Args:
            filepath: Path to file
            content: File content

        Returns:
            List of SemanticChange objects
        """
        changes = []

        if not content:
            return [SemanticChange('file_added', {
                'path': filepath,
                'note': 'empty file'
            })]

        try:
            tree = ast.parse(content)

            # Extract functions (only top-level for now)
            functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
            for func in functions:
                changes.append(SemanticChange('function_added', {
                    'file': filepath,
                    'name': func.name,
                    'params': [arg.arg for arg in func.args.args],
                    'is_async': isinstance(func, ast.AsyncFunctionDef),
                    'has_docstring': ast.get_docstring(func) is not None,
                    'decorators': [self._get_decorator_name(d) for d in func.decorator_list]
                }))

            # Extract classes
            classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
            for cls in classes:
                methods = [n.name for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                changes.append(SemanticChange('class_added', {
                    'file': filepath,
                    'name': cls.name,
                    'methods': methods,
                    'bases': [self._get_base_name(b) for b in cls.bases],
                    'has_docstring': ast.get_docstring(cls) is not None
                }))

            # Extract imports
            imports = self._extract_imports(tree)
            if imports:
                changes.append(SemanticChange('imports_added', {
                    'file': filepath,
                    'modules': list(imports)
                }))

            logger.debug(f"New file {filepath}: {len(functions)} functions, {len(classes)} classes")

        except SyntaxError as e:
            logger.warning(f"Syntax error in {filepath}: {e}")
            changes.append(SemanticChange('file_added', {
                'path': filepath,
                'note': f'syntax error: {str(e)}'
            }))

        return changes if changes else [SemanticChange('file_added', {'path': filepath})]

    def _compare_versions(self, filepath: str, old: str, new: str) -> List[SemanticChange]:
        """
        Compare old and new versions to detect changes.

        Args:
            filepath: Path to file
            old: Old file content
            new: New file content

        Returns:
            List of SemanticChange objects
        """
        changes = []

        if not new:
            logger.warning(f"No new content for {filepath}")
            return [SemanticChange('file_modified', {'path': filepath})]

        try:
            old_tree = ast.parse(old) if old else None
            new_tree = ast.parse(new)

            # Extract functions from both versions
            old_functions = self._extract_functions(old_tree) if old_tree else {}
            new_functions = self._extract_functions(new_tree)

            # Extract classes from both versions
            old_classes = self._extract_classes(old_tree) if old_tree else {}
            new_classes = self._extract_classes(new_tree)

            # Detect new functions
            for name in set(new_functions.keys()) - set(old_functions.keys()):
                func_info = new_functions[name]
                changes.append(SemanticChange('function_added', {
                    'file': filepath,
                    'name': name,
                    **func_info
                }))

            # Detect modified functions
            for name in set(new_functions.keys()) & set(old_functions.keys()):
                old_func = old_functions[name]
                new_func = new_functions[name]
                modifications = self._detect_function_modifications(old_func, new_func)

                if modifications:
                    changes.append(SemanticChange('function_modified', {
                        'file': filepath,
                        'name': name,
                        'params': new_func['params'],
                        'changes': modifications
                    }))

            # Detect deleted functions
            for name in set(old_functions.keys()) - set(new_functions.keys()):
                changes.append(SemanticChange('function_removed', {
                    'file': filepath,
                    'name': name
                }))

            # Detect new classes
            for name in set(new_classes.keys()) - set(old_classes.keys()):
                cls_info = new_classes[name]
                changes.append(SemanticChange('class_added', {
                    'file': filepath,
                    'name': name,
                    **cls_info
                }))

            # Detect modified classes
            for name in set(new_classes.keys()) & set(old_classes.keys()):
                old_cls = old_classes[name]
                new_cls = new_classes[name]

                # Check for method changes
                old_methods = set(old_cls['methods'])
                new_methods = set(new_cls['methods'])

                added_methods = new_methods - old_methods
                removed_methods = old_methods - new_methods

                if added_methods or removed_methods or old_cls['bases'] != new_cls['bases']:
                    class_changes = []
                    if added_methods:
                        class_changes.append(f"added methods: {', '.join(list(added_methods)[:3])}")
                    if removed_methods:
                        class_changes.append(f"removed methods: {', '.join(list(removed_methods)[:3])}")
                    if old_cls['bases'] != new_cls['bases']:
                        class_changes.append("inheritance changed")

                    changes.append(SemanticChange('class_modified', {
                        'file': filepath,
                        'name': name,
                        'methods': list(new_methods),
                        'changes': class_changes
                    }))

            # Detect deleted classes
            for name in set(old_classes.keys()) - set(new_classes.keys()):
                changes.append(SemanticChange('class_removed', {
                    'file': filepath,
                    'name': name
                }))

            # Detect import changes
            old_imports = self._extract_imports(old_tree) if old_tree else set()
            new_imports = self._extract_imports(new_tree)

            added_imports = new_imports - old_imports
            removed_imports = old_imports - new_imports

            if added_imports:
                changes.append(SemanticChange('imports_added', {
                    'file': filepath,
                    'modules': list(added_imports)
                }))

            if removed_imports:
                changes.append(SemanticChange('imports_removed', {
                    'file': filepath,
                    'modules': list(removed_imports)
                }))

            logger.debug(f"Modified file {filepath}: {len(changes)} semantic changes detected")

        except SyntaxError as e:
            logger.warning(f"Syntax error comparing versions of {filepath}: {e}")
            changes.append(SemanticChange('file_modified', {
                'path': filepath,
                'note': f'syntax error: {str(e)}'
            }))

        return changes if changes else [SemanticChange('file_modified', {'path': filepath})]

    def _extract_functions(self, tree: ast.AST) -> Dict:
        """
        Extract all top-level function definitions.

        Args:
            tree: AST tree

        Returns:
            Dict mapping function name to function info
        """
        if not tree:
            return {}

        functions = {}
        for node in tree.body if hasattr(tree, 'body') else []:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions[node.name] = {
                    'params': [arg.arg for arg in node.args.args],
                    'has_return_annotation': node.returns is not None,
                    'has_docstring': ast.get_docstring(node) is not None,
                    'is_async': isinstance(node, ast.AsyncFunctionDef),
                    'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
                }

        return functions

    def _extract_classes(self, tree: ast.AST) -> Dict:
        """
        Extract all top-level class definitions.

        Args:
            tree: AST tree

        Returns:
            Dict mapping class name to class info
        """
        if not tree:
            return {}

        classes = {}
        for node in tree.body if hasattr(tree, 'body') else []:
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                classes[node.name] = {
                    'methods': methods,
                    'bases': [self._get_base_name(b) for b in node.bases]
                }

        return classes

    def _extract_imports(self, tree: ast.AST) -> Set[str]:
        """
        Extract all import statements.

        Args:
            tree: AST tree

        Returns:
            Set of imported module names
        """
        if not tree:
            return set()

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)

        return imports

    def _detect_function_modifications(self, old: Dict, new: Dict) -> List[str]:
        """
        Detect what changed in a function.

        Args:
            old: Old function info dict
            new: New function info dict

        Returns:
            List of modification descriptions
        """
        modifications = []

        # Check parameter changes
        if old['params'] != new['params']:
            modifications.append('signature changed')

        # Check type annotations
        if not old['has_return_annotation'] and new['has_return_annotation']:
            modifications.append('added return type hint')
        elif old['has_return_annotation'] and not new['has_return_annotation']:
            modifications.append('removed return type hint')

        # Check docstring
        if not old['has_docstring'] and new['has_docstring']:
            modifications.append('added docstring')
        elif old['has_docstring'] and not new['has_docstring']:
            modifications.append('removed docstring')

        # Check async conversion
        if not old['is_async'] and new['is_async']:
            modifications.append('converted to async')
        elif old['is_async'] and not new['is_async']:
            modifications.append('converted to sync')

        # Check decorators
        if old['decorators'] != new['decorators']:
            modifications.append('decorators changed')

        return modifications

    def _get_decorator_name(self, decorator: ast.AST) -> str:
        """
        Extract decorator name from AST node.

        Args:
            decorator: AST decorator node

        Returns:
            Decorator name as string
        """
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        return 'unknown'

    def _get_base_name(self, base: ast.AST) -> str:
        """
        Extract base class name from AST node.

        Args:
            base: AST base class node

        Returns:
            Base class name as string
        """
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return base.attr
        return 'unknown'

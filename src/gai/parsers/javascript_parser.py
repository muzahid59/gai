"""
JavaScript/TypeScript parser using tree-sitter.

Supports: .js, .jsx, .ts, .tsx files
Extracts: functions, classes, imports, exports, variables
"""

from tree_sitter_languages import get_parser
from typing import List, Dict, Set
from .base import BaseParser
from gai.semantic_analyzer import SemanticChange
from gai.logger import logger


class JavaScriptParser(BaseParser):
    """Parse JavaScript and TypeScript files using tree-sitter."""

    def __init__(self):
        """Initialize JS/TS parsers."""
        self.js_parser = get_parser('javascript')
        self.ts_parser = get_parser('typescript')
        self.jsx_parser = get_parser('tsx')  # Handles both JSX and TSX
        logger.debug("Initialized JavaScript/TypeScript parser")

    def parse_file_changes(self, file_info: Dict) -> List[SemanticChange]:
        """
        Analyze JavaScript/TypeScript file changes semantically.

        Args:
            file_info: Dict with 'path' and 'status' keys

        Returns:
            List of SemanticChange objects
        """
        filepath = file_info['path']
        status = file_info['status']

        logger.debug(f"Parsing JS/TS file: {filepath} (status: {status})")

        if status == 'D':
            return [SemanticChange('file_deleted', {'path': filepath})]

        if status == 'A':
            new_content = self._get_file_content(filepath, ':0')
            if not new_content:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        new_content = f.read()
                except Exception:
                    pass
            return self._analyze_new_file(filepath, new_content)

        # Modified file - compare versions
        old_content = self._get_file_content(filepath, 'HEAD')
        new_content = self._get_file_content(filepath, ':0')

        if not new_content:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    new_content = f.read()
            except Exception:
                pass

        return self._compare_versions(filepath, old_content, new_content)

    def _get_parser_for_file(self, filepath: str):
        """Select appropriate parser based on file extension."""
        if filepath.endswith('.ts'):
            return self.ts_parser
        elif filepath.endswith('.tsx'):
            return self.jsx_parser
        elif filepath.endswith('.jsx'):
            return self.jsx_parser
        else:  # .js
            return self.js_parser

    def _analyze_new_file(self, filepath: str, content: str) -> List[SemanticChange]:
        """Analyze newly added JS/TS file."""
        changes = []

        if not content:
            return [SemanticChange('file_added', {
                'path': filepath,
                'note': 'empty file'
            })]

        try:
            parser = self._get_parser_for_file(filepath)
            tree = parser.parse(bytes(content, 'utf8'))
            root = tree.root_node

            # Extract functions (includes arrow functions, async functions)
            functions = self._extract_functions(root, content)
            for func_info in functions:
                changes.append(SemanticChange('function_added', {
                    'file': filepath,
                    **func_info
                }))

            # Extract classes (including React components)
            classes = self._extract_classes(root, content)
            for class_info in classes:
                changes.append(SemanticChange('class_added', {
                    'file': filepath,
                    **class_info
                }))

            # Extract imports/exports
            imports = self._extract_imports(root, content)
            if imports:
                changes.append(SemanticChange('imports_added', {
                    'file': filepath,
                    'modules': list(imports)
                }))

            # TypeScript-specific: interfaces and types
            if filepath.endswith(('.ts', '.tsx')):
                interfaces = self._extract_interfaces(root, content)
                for interface_info in interfaces:
                    changes.append(SemanticChange('interface_added', {
                        'file': filepath,
                        **interface_info
                    }))

            logger.debug(f"New file {filepath}: {len(functions)} functions, {len(classes)} classes")

        except Exception as e:
            logger.warning(f"Parse error in {filepath}: {e}")
            changes.append(SemanticChange('file_added', {
                'path': filepath,
                'note': f'parse error: {str(e)}'
            }))

        return changes if changes else [SemanticChange('file_added', {'path': filepath})]

    def _compare_versions(self, filepath: str, old: str, new: str) -> List[SemanticChange]:
        """Compare old and new versions using tree-sitter."""
        changes = []

        if not new:
            logger.warning(f"No new content for {filepath}")
            return [SemanticChange('file_modified', {'path': filepath})]

        try:
            parser = self._get_parser_for_file(filepath)

            old_tree = parser.parse(bytes(old, 'utf8')) if old else None
            new_tree = parser.parse(bytes(new, 'utf8'))

            # Extract from both versions
            old_functions = self._extract_functions_dict(old_tree.root_node, old) if old_tree else {}
            new_functions = self._extract_functions_dict(new_tree.root_node, new)

            old_classes = self._extract_classes_dict(old_tree.root_node, old) if old_tree else {}
            new_classes = self._extract_classes_dict(new_tree.root_node, new)

            # Detect new functions
            for name in set(new_functions.keys()) - set(old_functions.keys()):
                changes.append(SemanticChange('function_added', {
                    'file': filepath,
                    'name': name,
                    **new_functions[name]
                }))

            # Detect modified functions
            for name in set(new_functions.keys()) & set(old_functions.keys()):
                modifications = self._detect_function_modifications(
                    old_functions[name],
                    new_functions[name]
                )
                if modifications:
                    changes.append(SemanticChange('function_modified', {
                        'file': filepath,
                        'name': name,
                        'params': new_functions[name].get('params', []),
                        'changes': modifications
                    }))

            # Detect deleted functions
            for name in set(old_functions.keys()) - set(new_functions.keys()):
                changes.append(SemanticChange('function_removed', {
                    'file': filepath,
                    'name': name
                }))

            # Same for classes...
            for name in set(new_classes.keys()) - set(old_classes.keys()):
                changes.append(SemanticChange('class_added', {
                    'file': filepath,
                    'name': name,
                    **new_classes[name]
                }))

            # Detect modified classes
            for name in set(new_classes.keys()) & set(old_classes.keys()):
                old_cls = old_classes[name]
                new_cls = new_classes[name]

                old_methods = set(old_cls.get('methods', []))
                new_methods = set(new_cls.get('methods', []))

                added_methods = new_methods - old_methods
                removed_methods = old_methods - new_methods

                if added_methods or removed_methods:
                    class_changes = []
                    if added_methods:
                        class_changes.append(f"added methods: {', '.join(list(added_methods)[:3])}")
                    if removed_methods:
                        class_changes.append(f"removed methods: {', '.join(list(removed_methods)[:3])}")

                    changes.append(SemanticChange('class_modified', {
                        'file': filepath,
                        'name': name,
                        'methods': list(new_methods),
                        'changes': class_changes
                    }))

            for name in set(old_classes.keys()) - set(new_classes.keys()):
                changes.append(SemanticChange('class_removed', {
                    'file': filepath,
                    'name': name
                }))

            # Detect import changes
            old_imports = self._extract_imports(old_tree.root_node, old) if old_tree else set()
            new_imports = self._extract_imports(new_tree.root_node, new)

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

            # TypeScript-specific: interfaces and types
            if filepath.endswith(('.ts', '.tsx')):
                old_interfaces = self._extract_interfaces_dict(old_tree.root_node, old) if old_tree else {}
                new_interfaces = self._extract_interfaces_dict(new_tree.root_node, new)

                # Detect new interfaces
                for name in set(new_interfaces.keys()) - set(old_interfaces.keys()):
                    changes.append(SemanticChange('interface_added', {
                        'file': filepath,
                        'name': name
                    }))

                # Detect removed interfaces
                for name in set(old_interfaces.keys()) - set(new_interfaces.keys()):
                    changes.append(SemanticChange('interface_removed', {
                        'file': filepath,
                        'name': name
                    }))

            logger.debug(f"Modified file {filepath}: {len(changes)} semantic changes")

        except Exception as e:
            logger.warning(f"Parse error comparing {filepath}: {e}")
            changes.append(SemanticChange('file_modified', {
                'path': filepath,
                'note': f'parse error: {str(e)}'
            }))

        return changes if changes else [SemanticChange('file_modified', {'path': filepath})]

    def _extract_functions(self, root_node, source_code: str) -> List[Dict]:
        """
        Extract all function definitions using tree-sitter queries.

        Handles:
        - function declarations
        - arrow functions
        - async functions
        - generator functions
        - method definitions
        - arrow functions assigned to variables
        """
        functions = []

        # Tree-sitter query for function declarations
        query_patterns = [
            'function_declaration',
            'method_definition',
            'function_expression',
        ]

        for pattern in query_patterns:
            nodes = self._find_nodes_by_type(root_node, pattern)
            for node in nodes:
                func_info = self._parse_function_node(node, source_code)
                if func_info:
                    functions.append(func_info)

        # Handle arrow functions assigned to variables
        # e.g., const add = (x, y) => x + y;
        variable_declarators = self._find_nodes_by_type(root_node, 'variable_declarator')
        for declarator in variable_declarators:
            # Check if the initializer is an arrow function
            init_node = declarator.child_by_field_name('value')
            if init_node and init_node.type == 'arrow_function':
                name_node = declarator.child_by_field_name('name')
                if name_node:
                    name = source_code[name_node.start_byte:name_node.end_byte]
                    params_node = init_node.child_by_field_name('parameters')
                    params = self._extract_params(params_node, source_code) if params_node else []

                    # Check if async
                    node_text = source_code[init_node.start_byte:init_node.end_byte]
                    is_async = node_text.strip().startswith('async ')

                    functions.append({
                        'name': name,
                        'params': params,
                        'is_async': is_async,
                        'is_arrow': True,
                    })

        return functions

    def _extract_functions_dict(self, root_node, source_code: str) -> Dict:
        """Extract functions as a dict keyed by name."""
        functions = self._extract_functions(root_node, source_code)
        return {f['name']: f for f in functions if 'name' in f and f['name'] != '<anonymous>'}

    def _parse_function_node(self, node, source_code: str) -> Dict:
        """Parse tree-sitter function node into metadata."""
        # Extract function name
        name_node = node.child_by_field_name('name')
        name = source_code[name_node.start_byte:name_node.end_byte] if name_node else '<anonymous>'

        # Extract parameters
        params_node = node.child_by_field_name('parameters')
        params = self._extract_params(params_node, source_code) if params_node else []

        # Check if async
        node_text = source_code[node.start_byte:node.end_byte]
        is_async = node_text.strip().startswith('async ')

        # Check if arrow function
        is_arrow = node.type == 'arrow_function'

        return {
            'name': name,
            'params': params,
            'is_async': is_async,
            'is_arrow': is_arrow,
        }

    def _extract_classes(self, root_node, source_code: str) -> List[Dict]:
        """Extract class declarations."""
        classes = []

        class_nodes = self._find_nodes_by_type(root_node, 'class_declaration')

        for node in class_nodes:
            name_node = node.child_by_field_name('name')
            name = source_code[name_node.start_byte:name_node.end_byte] if name_node else '<anonymous>'

            # Extract methods
            body_node = node.child_by_field_name('body')
            methods = []
            if body_node:
                method_nodes = self._find_nodes_by_type(body_node, 'method_definition')
                for m in method_nodes:
                    method_name_node = m.child_by_field_name('name')
                    if method_name_node:
                        method_name = source_code[method_name_node.start_byte:method_name_node.end_byte]
                        methods.append(method_name)

            classes.append({
                'name': name,
                'methods': methods
            })

        return classes

    def _extract_classes_dict(self, root_node, source_code: str) -> Dict:
        """Extract classes as dict keyed by name."""
        classes = self._extract_classes(root_node, source_code)
        return {c['name']: c for c in classes if c['name'] != '<anonymous>'}

    def _extract_imports(self, root_node, source_code: str) -> Set[str]:
        """Extract import/require statements."""
        imports = set()

        # ES6 imports: import { x } from 'module'
        import_nodes = self._find_nodes_by_type(root_node, 'import_statement')
        for node in import_nodes:
            source_node = node.child_by_field_name('source')
            if source_node:
                module = source_code[source_node.start_byte:source_node.end_byte].strip('\'"')
                imports.add(module)

        # CommonJS requires: const x = require('module')
        # (Would need more complex traversal - skip for MVP)

        return imports

    def _extract_interfaces(self, root_node, source_code: str) -> List[Dict]:
        """Extract TypeScript interfaces and type aliases."""
        interfaces = []

        # TypeScript interface declarations
        interface_nodes = self._find_nodes_by_type(root_node, 'interface_declaration')
        for node in interface_nodes:
            name_node = node.child_by_field_name('name')
            name = source_code[name_node.start_byte:name_node.end_byte] if name_node else '<anonymous>'
            if name != '<anonymous>':
                interfaces.append({'name': name})

        return interfaces

    def _extract_interfaces_dict(self, root_node, source_code: str) -> Dict:
        """Extract interfaces as dict keyed by name."""
        interfaces = self._extract_interfaces(root_node, source_code)
        return {i['name']: i for i in interfaces}

    def _find_nodes_by_type(self, node, node_type: str) -> List:
        """Recursively find all nodes of a given type."""
        nodes = []

        if node.type == node_type:
            nodes.append(node)

        for child in node.children:
            nodes.extend(self._find_nodes_by_type(child, node_type))

        return nodes

    def _extract_params(self, params_node, source_code: str) -> List[str]:
        """Extract parameter names from parameters node."""
        params = []

        for child in params_node.children:
            if child.type in ['identifier', 'required_parameter', 'optional_parameter']:
                # Handle both JS and TS parameter nodes
                if child.child_count > 0:
                    # TS parameter with type annotation
                    name_node = child.children[0]
                else:
                    name_node = child

                param_name = source_code[name_node.start_byte:name_node.end_byte]
                if param_name and param_name not in ('(', ')', ',', '{', '}'):
                    params.append(param_name)

        return params

    def _detect_function_modifications(self, old: Dict, new: Dict) -> List[str]:
        """Detect what changed in a function."""
        modifications = []

        if old.get('params') != new.get('params'):
            modifications.append('signature changed')

        if not old.get('is_async') and new.get('is_async'):
            modifications.append('converted to async')
        elif old.get('is_async') and not new.get('is_async'):
            modifications.append('converted to sync')

        return modifications

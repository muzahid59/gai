"""JavaScript/TypeScript code analyzer."""

import re
from typing import List
from .base import LanguageAnalyzer, GroundTruth, CodeChange, ChangeType


class JavaScriptAnalyzer(LanguageAnalyzer):
    """Analyzer for JavaScript and TypeScript code."""

    @property
    def supported_extensions(self) -> List[str]:
        return ['.js', '.jsx', '.ts', '.tsx', '.mjs']

    @property
    def language_name(self) -> str:
        return "JavaScript/TypeScript"

    def analyze_diff(self, diff_content: str, file_path: str) -> GroundTruth:
        """Analyze JavaScript/TypeScript diff."""
        truth = GroundTruth(file_path=file_path, language=self.language_name)

        added_lines = self.extract_added_lines(diff_content)
        removed_lines = self.extract_removed_lines(diff_content)

        # Detect TypeScript vs JavaScript
        is_typescript = file_path.endswith(('.ts', '.tsx'))
        truth.metadata['is_typescript'] = is_typescript

        # Analyze added code
        truth.changes.extend(self._analyze_functions(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_classes(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_imports(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_exports(added_lines))

        if is_typescript:
            truth.changes.extend(self._analyze_interfaces(added_lines))
            truth.changes.extend(self._analyze_types(added_lines))
            truth.changes.extend(self._analyze_type_annotations(added_lines))

        truth.changes.extend(self._analyze_async_await(added_lines))
        truth.changes.extend(self._analyze_validation(added_lines))
        truth.changes.extend(self._analyze_error_handling(added_lines))

        # Analyze removed code
        truth.changes.extend(self._analyze_functions(removed_lines, ChangeType.REMOVED))
        truth.changes.extend(self._analyze_classes(removed_lines, ChangeType.REMOVED))

        # Metadata
        truth.metadata['lines_added'] = len(added_lines)
        truth.metadata['lines_removed'] = len(removed_lines)
        truth.metadata['is_new_file'] = self.is_new_file(diff_content)

        return truth

    def _analyze_functions(self, lines: List[str], change_type: ChangeType) -> List[CodeChange]:
        """Extract function definitions (regular, arrow, async)."""
        changes = []

        patterns = [
            # function name() {}
            (r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\((.*?)\)', 'function'),
            # const name = () => {}
            (r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\((.*?)\)\s*=>', 'arrow'),
            # const name = function() {}
            (r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function\s*\((.*?)\)', 'function_expression'),
            # method() {}
            (r'(?:async\s+)?(\w+)\s*\((.*?)\)\s*\{', 'method'),
        ]

        for line in lines:
            for pattern, func_type in patterns:
                match = re.search(pattern, line)
                if match:
                    func_name = match.group(1)
                    params = match.group(2) if match.lastindex >= 2 else ""

                    details = {
                        'type': func_type,
                        'parameters': params.strip()
                    }

                    if 'async' in line:
                        details['async'] = True

                    if 'export' in line:
                        details['exported'] = True

                    # Extract return type for TypeScript
                    return_type_match = re.search(r'\)\s*:\s*([^{=]+)', line)
                    if return_type_match:
                        details['return_type'] = return_type_match.group(1).strip()

                    changes.append(CodeChange(
                        change_type=change_type,
                        category='function',
                        name=func_name,
                        details=details
                    ))
                    break

        return changes

    def _analyze_classes(self, lines: List[str], change_type: ChangeType) -> List[CodeChange]:
        """Extract class definitions."""
        changes = []
        pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?'

        for line in lines:
            match = re.search(pattern, line)
            if match:
                class_name = match.group(1)
                extends = match.group(2) if match.lastindex >= 2 else None

                details = {}
                if extends:
                    details['extends'] = extends
                if 'export' in line:
                    details['exported'] = True

                changes.append(CodeChange(
                    change_type=change_type,
                    category='class',
                    name=class_name,
                    details=details
                ))

        return changes

    def _analyze_imports(self, lines: List[str], change_type: ChangeType) -> List[CodeChange]:
        """Extract import statements."""
        changes = []

        for line in lines:
            line = line.strip()
            if line.startswith('import '):
                # import { x } from 'module'
                match = re.search(r"import\s+(?:{([^}]+)}|\w+)\s+from\s+['\"]([^'\"]+)['\"]", line)
                if match:
                    imports = match.group(1) if match.group(1) else 'default'
                    module = match.group(2)

                    changes.append(CodeChange(
                        change_type=change_type,
                        category='import',
                        name=module,
                        details={'imports': imports.strip()}
                    ))
            elif line.startswith('const ') and 'require(' in line:
                # const x = require('module')
                match = re.search(r"require\(['\"]([^'\"]+)['\"]\)", line)
                if match:
                    module = match.group(1)
                    changes.append(CodeChange(
                        change_type=change_type,
                        category='import',
                        name=module,
                        details={'type': 'require'}
                    ))

        return changes

    def _analyze_exports(self, lines: List[str]) -> List[CodeChange]:
        """Extract export statements."""
        changes = []

        for line in lines:
            if 'export ' in line:
                # export { x, y }
                match = re.search(r'export\s+{([^}]+)}', line)
                if match:
                    exports = match.group(1).strip()
                    changes.append(CodeChange(
                        change_type=ChangeType.ADDED,
                        category='export',
                        name=exports,
                        details={'line': line.strip()}
                    ))

        return changes

    def _analyze_interfaces(self, lines: List[str]) -> List[CodeChange]:
        """Extract TypeScript interface definitions."""
        changes = []
        pattern = r'(?:export\s+)?interface\s+(\w+)'

        for line in lines:
            match = re.search(pattern, line)
            if match:
                interface_name = match.group(1)
                details = {}
                if 'export' in line:
                    details['exported'] = True

                changes.append(CodeChange(
                    change_type=ChangeType.ADDED,
                    category='interface',
                    name=interface_name,
                    details=details
                ))

        return changes

    def _analyze_types(self, lines: List[str]) -> List[CodeChange]:
        """Extract TypeScript type definitions."""
        changes = []
        pattern = r'(?:export\s+)?type\s+(\w+)\s*='

        for line in lines:
            match = re.search(pattern, line)
            if match:
                type_name = match.group(1)
                details = {}
                if 'export' in line:
                    details['exported'] = True

                changes.append(CodeChange(
                    change_type=ChangeType.ADDED,
                    category='type_alias',
                    name=type_name,
                    details=details
                ))

        return changes

    def _analyze_type_annotations(self, lines: List[str]) -> List[CodeChange]:
        """Detect TypeScript type annotations."""
        has_annotations = False

        for line in lines:
            # Check for type annotations
            if re.search(r':\s*\w+(?:<[^>]+>)?', line):
                has_annotations = True
                break

        if has_annotations:
            return [CodeChange(
                change_type=ChangeType.ADDED,
                category='type_annotation',
                name='type annotations',
                details={'description': 'Type annotations added'}
            )]

        return []

    def _analyze_async_await(self, lines: List[str]) -> List[CodeChange]:
        """Detect async/await usage."""
        changes = []

        for line in lines:
            if 'await ' in line and 'async' not in line:
                changes.append(CodeChange(
                    change_type=ChangeType.ADDED,
                    category='async_pattern',
                    name='await usage',
                    details={'line': line.strip()}
                ))

        return changes

    def _analyze_validation(self, lines: List[str]) -> List[CodeChange]:
        """Extract validation logic."""
        changes = []

        validation_patterns = [
            (r'if\s*\(\s*!(\w+)', 'falsy check'),
            (r'if\s*\(\s*(\w+)\s*===\s*null', 'null check'),
            (r'if\s*\(\s*(\w+)\s*===\s*undefined', 'undefined check'),
            (r'if\s*\(\s*typeof\s+(\w+)', 'type check'),
            (r'if\s*\(\s*(\w+)\.length', 'length check'),
        ]

        for line in lines:
            for pattern, description in validation_patterns:
                match = re.search(pattern, line)
                if match:
                    var_name = match.group(1) if match.lastindex >= 1 else 'value'
                    changes.append(CodeChange(
                        change_type=ChangeType.ADDED,
                        category='validation',
                        name=f'{var_name} validation',
                        details={
                            'type': description,
                            'line': line.strip()
                        }
                    ))

        return changes

    def _analyze_error_handling(self, lines: List[str]) -> List[CodeChange]:
        """Extract error handling patterns."""
        changes = []

        for line in lines:
            # throw new Error
            if 'throw new' in line or 'throw ' in line:
                match = re.search(r'throw\s+(?:new\s+)?(\w+(?:Error)?)', line)
                if match:
                    error_type = match.group(1)
                    changes.append(CodeChange(
                        change_type=ChangeType.ADDED,
                        category='exception',
                        name=error_type,
                        details={'action': 'thrown', 'line': line.strip()}
                    ))

            # try/catch
            if re.match(r'\s*try\s*{', line):
                changes.append(CodeChange(
                    change_type=ChangeType.ADDED,
                    category='error_handling',
                    name='try-catch block',
                    details={'line': line.strip()}
                ))

        return changes

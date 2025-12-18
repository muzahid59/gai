"""Python-specific code analyzer using AST parsing."""

import re
import ast
from typing import List
from .base import LanguageAnalyzer, GroundTruth, CodeChange, ChangeType


class PythonAnalyzer(LanguageAnalyzer):
    """Analyzer for Python code using AST when possible."""

    @property
    def supported_extensions(self) -> List[str]:
        return ['.py', '.pyw']

    @property
    def language_name(self) -> str:
        return "Python"

    def analyze_diff(self, diff_content: str, file_path: str) -> GroundTruth:
        """Analyze Python diff using AST and pattern matching."""
        truth = GroundTruth(file_path=file_path, language=self.language_name)

        added_lines = self.extract_added_lines(diff_content)
        removed_lines = self.extract_removed_lines(diff_content)

        # Analyze added code
        truth.changes.extend(self._analyze_functions(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_classes(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_imports(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_decorators(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_type_hints(added_lines))
        truth.changes.extend(self._analyze_validation(added_lines))
        truth.changes.extend(self._analyze_exceptions(added_lines))
        truth.changes.extend(self._analyze_docstrings(added_lines))

        # Analyze removed code
        truth.changes.extend(self._analyze_functions(removed_lines, ChangeType.REMOVED))
        truth.changes.extend(self._analyze_classes(removed_lines, ChangeType.REMOVED))

        # Metadata
        truth.metadata['lines_added'] = len(added_lines)
        truth.metadata['lines_removed'] = len(removed_lines)
        truth.metadata['is_new_file'] = self.is_new_file(diff_content)
        truth.metadata['is_deleted_file'] = self.is_deleted_file(diff_content)

        return truth

    def _analyze_functions(self, lines: List[str], change_type: ChangeType) -> List[CodeChange]:
        """Extract function definitions."""
        changes = []
        # Pattern: def function_name(params) -> return_type:
        pattern = r'def\s+(\w+)\s*\((.*?)\)(?:\s*->\s*([^:]+))?:'

        for line in lines:
            match = re.search(pattern, line)
            if match:
                func_name = match.group(1)
                params = match.group(2).strip() if match.group(2) else ""
                return_type = match.group(3).strip() if match.group(3) else None

                details = {'parameters': params}
                if return_type:
                    details['return_type'] = return_type

                # Check if async
                if 'async def' in line:
                    details['async'] = True

                changes.append(CodeChange(
                    change_type=change_type,
                    category='function',
                    name=func_name,
                    details=details
                ))

        return changes

    def _analyze_classes(self, lines: List[str], change_type: ChangeType) -> List[CodeChange]:
        """Extract class definitions."""
        changes = []
        pattern = r'class\s+(\w+)(?:\((.*?)\))?:'

        for line in lines:
            match = re.search(pattern, line)
            if match:
                class_name = match.group(1)
                bases = match.group(2).strip() if match.group(2) else None

                details = {}
                if bases:
                    details['inherits_from'] = bases

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
            if line.startswith('import ') or line.startswith('from '):
                # Extract module name
                if line.startswith('from '):
                    match = re.match(r'from\s+([\w.]+)', line)
                    if match:
                        module = match.group(1)
                        changes.append(CodeChange(
                            change_type=change_type,
                            category='import',
                            name=module,
                            details={'statement': line}
                        ))
                else:
                    match = re.match(r'import\s+([\w.]+)', line)
                    if match:
                        module = match.group(1)
                        changes.append(CodeChange(
                            change_type=change_type,
                            category='import',
                            name=module,
                            details={'statement': line}
                        ))

        return changes

    def _analyze_decorators(self, lines: List[str], change_type: ChangeType) -> List[CodeChange]:
        """Extract decorator usage."""
        changes = []
        pattern = r'@(\w+)(?:\((.*?)\))?'

        for line in lines:
            match = re.search(pattern, line.strip())
            if match:
                decorator_name = match.group(1)
                args = match.group(2) if match.group(2) else None

                details = {}
                if args:
                    details['arguments'] = args

                changes.append(CodeChange(
                    change_type=change_type,
                    category='decorator',
                    name=decorator_name,
                    details=details
                ))

        return changes

    def _analyze_type_hints(self, lines: List[str]) -> List[CodeChange]:
        """Detect if type hints were added."""
        changes = []
        has_type_hints = False

        for line in lines:
            # Check for parameter type hints or return type hints
            if ': ' in line and 'def ' in line:
                has_type_hints = True
            elif '->' in line and 'def ' in line:
                has_type_hints = True

        if has_type_hints:
            changes.append(CodeChange(
                change_type=ChangeType.ADDED,
                category='type_hint',
                name='type hints',
                details={'description': 'Type annotations added'}
            ))

        return changes

    def _analyze_validation(self, lines: List[str]) -> List[CodeChange]:
        """Extract validation logic."""
        changes = []

        validation_patterns = [
            (r'if\s+not\s+(\w+)', 'empty/None check'),
            (r'if\s+(\w+)\s+is\s+None', 'None check'),
            (r'if\s+(\w+)\s*<\s*0', 'negative value check'),
            (r'if\s+(\w+)\s*<=\s*0', 'non-positive check'),
            (r'if\s+len\((\w+)\)', 'length check'),
            (r'if\s+not\s+isinstance\((\w+)', 'type check'),
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

    def _analyze_exceptions(self, lines: List[str]) -> List[CodeChange]:
        """Extract exception handling and raising."""
        changes = []

        for line in lines:
            # Exception raising
            raise_match = re.search(r'raise\s+(\w+(?:Error|Exception))', line)
            if raise_match:
                exception_type = raise_match.group(1)
                changes.append(CodeChange(
                    change_type=ChangeType.ADDED,
                    category='exception',
                    name=exception_type,
                    details={'action': 'raised', 'line': line.strip()}
                ))

            # Try/except blocks
            if re.match(r'\s*try:', line):
                changes.append(CodeChange(
                    change_type=ChangeType.ADDED,
                    category='error_handling',
                    name='try-except block',
                    details={'line': line.strip()}
                ))

        return changes

    def _analyze_docstrings(self, lines: List[str]) -> List[CodeChange]:
        """Detect docstring additions."""
        changes = []
        has_docstring = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                has_docstring = True
                break

        if has_docstring:
            changes.append(CodeChange(
                change_type=ChangeType.ADDED,
                category='documentation',
                name='docstring',
                details={'description': 'Documentation added'}
            ))

        return changes

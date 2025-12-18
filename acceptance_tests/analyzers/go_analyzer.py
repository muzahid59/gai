"""Go code analyzer."""

import re
from typing import List
from .base import LanguageAnalyzer, GroundTruth, CodeChange, ChangeType


class GoAnalyzer(LanguageAnalyzer):
    """Analyzer for Go code."""

    @property
    def supported_extensions(self) -> List[str]:
        return ['.go']

    @property
    def language_name(self) -> str:
        return "Go"

    def analyze_diff(self, diff_content: str, file_path: str) -> GroundTruth:
        """Analyze Go diff."""
        truth = GroundTruth(file_path=file_path, language=self.language_name)

        added_lines = self.extract_added_lines(diff_content)
        removed_lines = self.extract_removed_lines(diff_content)

        # Analyze added code
        truth.changes.extend(self._analyze_functions(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_methods(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_structs(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_interfaces(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_imports(added_lines, ChangeType.ADDED))
        truth.changes.extend(self._analyze_error_handling(added_lines))
        truth.changes.extend(self._analyze_validation(added_lines))

        # Analyze removed code
        truth.changes.extend(self._analyze_functions(removed_lines, ChangeType.REMOVED))
        truth.changes.extend(self._analyze_structs(removed_lines, ChangeType.REMOVED))

        # Metadata
        truth.metadata['lines_added'] = len(added_lines)
        truth.metadata['lines_removed'] = len(removed_lines)
        truth.metadata['is_new_file'] = self.is_new_file(diff_content)
        truth.metadata['is_test_file'] = file_path.endswith('_test.go')

        return truth

    def _analyze_functions(self, lines: List[str], change_type: ChangeType) -> List[CodeChange]:
        """Extract function definitions."""
        changes = []
        # Pattern: func name(params) (return_types) {
        pattern = r'func\s+(\w+)\s*\((.*?)\)(?:\s*\((.*?)\)|\s+(\w+(?:\.\w+)?))?\s*{'

        for line in lines:
            match = re.search(pattern, line)
            if match:
                func_name = match.group(1)
                params = match.group(2).strip() if match.group(2) else ""
                # Return type can be in group 3 (multiple returns) or 4 (single return)
                return_type = (match.group(3) or match.group(4) or "").strip()

                details = {'parameters': params}
                if return_type:
                    details['return_type'] = return_type

                changes.append(CodeChange(
                    change_type=change_type,
                    category='function',
                    name=func_name,
                    details=details
                ))

        return changes

    def _analyze_methods(self, lines: List[str], change_type: ChangeType) -> List[CodeChange]:
        """Extract method definitions with receivers."""
        changes = []
        # Pattern: func (r Receiver) methodName(params) return_type {
        pattern = r'func\s+\((\w+)\s+\*?(\w+)\)\s+(\w+)\s*\((.*?)\)(?:\s*\((.*?)\)|\s+(\w+(?:\.\w+)?))?\s*{'

        for line in lines:
            match = re.search(pattern, line)
            if match:
                receiver_var = match.group(1)
                receiver_type = match.group(2)
                method_name = match.group(3)
                params = match.group(4).strip() if match.group(4) else ""
                return_type = (match.group(5) or match.group(6) or "").strip()

                is_pointer = '*' in line.split(method_name)[0]

                details = {
                    'receiver': f'{receiver_var} {receiver_type}',
                    'pointer_receiver': is_pointer,
                    'parameters': params
                }
                if return_type:
                    details['return_type'] = return_type

                changes.append(CodeChange(
                    change_type=change_type,
                    category='method',
                    name=f'{receiver_type}.{method_name}',
                    details=details
                ))

        return changes

    def _analyze_structs(self, lines: List[str], change_type: ChangeType) -> List[CodeChange]:
        """Extract struct definitions."""
        changes = []
        pattern = r'type\s+(\w+)\s+struct\s*{'

        for line in lines:
            match = re.search(pattern, line)
            if match:
                struct_name = match.group(1)
                changes.append(CodeChange(
                    change_type=change_type,
                    category='struct',
                    name=struct_name,
                    details={}
                ))

        return changes

    def _analyze_interfaces(self, lines: List[str], change_type: ChangeType) -> List[CodeChange]:
        """Extract interface definitions."""
        changes = []
        pattern = r'type\s+(\w+)\s+interface\s*{'

        for line in lines:
            match = re.search(pattern, line)
            if match:
                interface_name = match.group(1)
                changes.append(CodeChange(
                    change_type=change_type,
                    category='interface',
                    name=interface_name,
                    details={}
                ))

        return changes

    def _analyze_imports(self, lines: List[str], change_type: ChangeType) -> List[CodeChange]:
        """Extract import statements."""
        changes = []

        for line in lines:
            line = line.strip()
            # Single import: import "package"
            if line.startswith('import ') and '"' in line:
                match = re.search(r'import\s+"([^"]+)"', line)
                if match:
                    package = match.group(1)
                    changes.append(CodeChange(
                        change_type=change_type,
                        category='import',
                        name=package,
                        details={}
                    ))
            # Import within block: "package" or alias "package"
            elif '"' in line and not line.startswith('//'):
                match = re.search(r'(?:(\w+)\s+)?"([^"]+)"', line)
                if match:
                    alias = match.group(1)
                    package = match.group(2)
                    details = {}
                    if alias:
                        details['alias'] = alias

                    changes.append(CodeChange(
                        change_type=change_type,
                        category='import',
                        name=package,
                        details=details
                    ))

        return changes

    def _analyze_error_handling(self, lines: List[str]) -> List[CodeChange]:
        """Extract error handling patterns."""
        changes = []

        for line in lines:
            # if err != nil
            if re.search(r'if\s+err\s*!=\s*nil', line):
                changes.append(CodeChange(
                    change_type=ChangeType.ADDED,
                    category='error_handling',
                    name='error check',
                    details={
                        'pattern': 'if err != nil',
                        'line': line.strip()
                    }
                ))

            # return ..., error
            if re.search(r'return\s+.*,\s*(?:err|error|nil|\w+Error)', line):
                changes.append(CodeChange(
                    change_type=ChangeType.ADDED,
                    category='error_handling',
                    name='error return',
                    details={'line': line.strip()}
                ))

            # fmt.Errorf or errors.New
            if 'fmt.Errorf' in line or 'errors.New' in line:
                changes.append(CodeChange(
                    change_type=ChangeType.ADDED,
                    category='error_creation',
                    name='error message',
                    details={'line': line.strip()}
                ))

        return changes

    def _analyze_validation(self, lines: List[str]) -> List[CodeChange]:
        """Extract validation logic."""
        changes = []

        validation_patterns = [
            (r'if\s+(\w+)\s*==\s*nil', 'nil check'),
            (r'if\s+(\w+)\s*==\s*""', 'empty string check'),
            (r'if\s+len\((\w+)\)', 'length check'),
            (r'if\s+(\w+)\s*<\s*0', 'negative value check'),
            (r'if\s+(\w+)\s*<=\s*0', 'non-positive check'),
        ]

        for line in lines:
            for pattern, description in validation_patterns:
                match = re.search(pattern, line)
                if match:
                    var_name = match.group(1)
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

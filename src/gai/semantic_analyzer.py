"""
Semantic diff analyzer - extracts meaningful information from code changes.

This module analyzes git diffs semantically rather than as raw text,
extracting structured information about functions, classes, imports, etc.
"""

from typing import Dict, List
from pathlib import Path
import subprocess
import re

from gai.logger import logger


class SemanticChange:
    """Represents a semantic change (function added, class modified, etc.)"""

    def __init__(self, change_type: str, details: Dict):
        """
        Initialize a semantic change.

        Args:
            change_type: Type of change (e.g., "function_added", "class_modified")
            details: Dictionary with change-specific details
        """
        self.type = change_type
        self.details = details

    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        return {"type": self.type, **self.details}

    def __repr__(self):
        return f"SemanticChange({self.type}, {self.details})"


class SemanticAnalyzer:
    """Main class for analyzing git diffs semantically."""

    def __init__(self):
        """Initialize the semantic analyzer."""
        self.parsers = {}
        self._register_parsers()

    def _register_parsers(self):
        """Register language-specific parsers."""
        try:
            from gai.parsers.python_parser import PythonParser
            self.parsers['.py'] = PythonParser()
            logger.debug("Registered Python parser")
        except ImportError:
            logger.warning("Could not import PythonParser")

    def analyze_diff(self) -> Dict:
        """
        Analyze staged git changes semantically.

        Returns:
            Dictionary with 'summary' and 'changes' keys
        """
        logger.info("Starting semantic diff analysis")

        # 1. Get list of changed files
        files = self._get_changed_files()
        logger.debug(f"Found {len(files)} changed files")

        # 2. Get file-level stats
        stats = self._get_diff_stats()

        # 3. Analyze each file semantically
        all_changes = []
        for file_info in files:
            changes = self._analyze_file(file_info)
            if changes:
                all_changes.extend(changes)
                logger.debug(f"File {file_info['path']}: {len(changes)} semantic changes")

        # 4. Build structured summary
        result = {
            "summary": {
                "files_changed": len(files),
                "stats": stats
            },
            "changes": all_changes
        }

        logger.info(f"Semantic analysis complete: {len(all_changes)} total changes")
        return result

    def _get_changed_files(self) -> List[Dict]:
        """
        Get list of staged files with their status.

        Returns:
            List of dicts with 'path' and 'status' keys
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--staged", "--name-status"],
                capture_output=True,
                text=True,
                check=True
            )

            files = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('\t', 1)
                if len(parts) == 2:
                    status, filepath = parts
                    files.append({
                        'path': filepath,
                        'status': status  # A=added, M=modified, D=deleted
                    })

            return files

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get changed files: {e}")
            return []

    def _get_diff_stats(self) -> str:
        """
        Get high-level diff statistics.

        Returns:
            String describing changes (e.g., "3 files, +45, -12")
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--staged", "--shortstat"],
                capture_output=True,
                text=True,
                check=True
            )

            # Parse output like: "3 files changed, 45 insertions(+), 12 deletions(-)"
            output = result.stdout.strip()
            if not output:
                return "no changes"

            # Extract numbers
            match = re.search(r'(\d+) file', output)
            files = match.group(1) if match else "0"

            match = re.search(r'(\d+) insertion', output)
            insertions = match.group(1) if match else "0"

            match = re.search(r'(\d+) deletion', output)
            deletions = match.group(1) if match else "0"

            return f"{files} files, +{insertions}, -{deletions}"

        except subprocess.CalledProcessError:
            return "no stats available"

    def _analyze_file(self, file_info: Dict) -> List[SemanticChange]:
        """
        Analyze a single file's changes.

        Args:
            file_info: Dict with 'path' and 'status'

        Returns:
            List of SemanticChange objects
        """
        filepath = file_info['path']
        ext = Path(filepath).suffix

        # Check if we have a parser for this file type
        if ext not in self.parsers:
            # Fallback to generic analysis
            return self._generic_file_analysis(file_info)

        # Use language-specific parser
        try:
            parser = self.parsers[ext]
            return parser.parse_file_changes(file_info)
        except Exception as e:
            logger.error(f"Error parsing {filepath}: {e}")
            return self._generic_file_analysis(file_info)

    def _generic_file_analysis(self, file_info: Dict) -> List[SemanticChange]:
        """
        Fallback for non-code files.

        Args:
            file_info: Dict with 'path' and 'status'

        Returns:
            List with single SemanticChange
        """
        status = file_info['status']
        filepath = file_info['path']

        change_type_map = {
            'A': 'file_added',
            'M': 'file_modified',
            'D': 'file_deleted'
        }

        change_type = change_type_map.get(status, 'file_changed')

        return [SemanticChange(change_type, {"path": filepath})]

    def format_for_ai(self, analysis: Dict) -> str:
        """
        Convert semantic analysis to concise prompt for AI.
        This is the key function that reduces tokens.

        Args:
            analysis: Dict from analyze_diff()

        Returns:
            Formatted string for AI consumption
        """
        lines = []

        # Summary
        summary = analysis['summary']
        lines.append(f"Files changed: {summary['files_changed']}")
        lines.append(f"Stats: {summary['stats']}")
        lines.append("")

        # Group changes by type
        changes_by_type = {}
        for change in analysis['changes']:
            change_dict = change.to_dict()
            ctype = change_dict['type']
            if ctype not in changes_by_type:
                changes_by_type[ctype] = []
            changes_by_type[ctype].append(change_dict)

        # Format each group
        for change_type, changes in sorted(changes_by_type.items()):
            # Make heading readable
            heading = change_type.replace('_', ' ').title()
            lines.append(f"## {heading}")

            for change in changes:
                formatted = self._format_change(change)
                lines.append(f"  - {formatted}")

            lines.append("")

        result = "\n".join(lines)
        logger.debug(f"Formatted analysis: {len(result)} characters")
        return result

    def _format_change(self, change: Dict) -> str:
        """
        Format a single change for readability.

        Args:
            change: Dict with 'type' and other keys

        Returns:
            Formatted string
        """
        change_type = change['type']

        # Function added/modified/removed
        if 'function_added' in change_type or 'function_modified' in change_type:
            name = change.get('name', 'unknown')
            params = change.get('params', [])
            file = change.get('file', '')
            param_str = ', '.join(params) if params else ''

            result = f"{name}({param_str})"
            if file:
                result += f" in {file}"

            if 'changes' in change:
                modifications = ', '.join(change['changes'])
                result += f" ({modifications})"

            return result

        # Function removed
        elif 'function_removed' in change_type:
            name = change.get('name', 'unknown')
            file = change.get('file', '')
            result = f"{name}"
            if file:
                result += f" in {file}"
            return result

        # Class added/modified
        elif 'class' in change_type:
            name = change.get('name', 'unknown')
            methods = change.get('methods', [])
            file = change.get('file', '')

            result = f"{name} with {len(methods)} method(s)"
            if file:
                result += f" in {file}"
            return result

        # Imports
        elif 'import' in change_type:
            modules = change.get('modules', [])
            file = change.get('file', '')
            modules_str = ', '.join(list(modules)[:5])  # Limit to 5
            if len(modules) > 5:
                modules_str += f" and {len(modules) - 5} more"

            result = f"{modules_str}"
            if file:
                result += f" in {file}"
            return result

        # File operations
        elif 'file' in change_type:
            return change.get('path', 'unknown file')

        # Default
        return str(change)

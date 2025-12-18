"""Base classes for language analyzers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Set
from enum import Enum


class ChangeType(Enum):
    """Types of code changes."""
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"


@dataclass
class CodeChange:
    """Represents a specific code change extracted from a diff."""
    change_type: ChangeType
    category: str  # e.g., 'function', 'class', 'import', 'validation'
    name: str
    details: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0  # How confident we are in this extraction

    def __repr__(self):
        return f"CodeChange({self.change_type.value} {self.category}: {self.name})"


@dataclass
class GroundTruth:
    """Ground truth extracted from analyzing a diff."""
    file_path: str
    language: str
    changes: List[CodeChange] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_changes_by_category(self, category: str) -> List[CodeChange]:
        """Get all changes of a specific category."""
        return [c for c in self.changes if c.category == category]

    def get_changes_by_type(self, change_type: ChangeType) -> List[CodeChange]:
        """Get all changes of a specific type."""
        return [c for c in self.changes if c.change_type == change_type]

    def get_all_names(self) -> Set[str]:
        """Get all names mentioned in changes."""
        return {c.name for c in self.changes}


class LanguageAnalyzer(ABC):
    """Base class for language-specific analyzers."""

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """File extensions this analyzer supports."""
        pass

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Human-readable language name."""
        pass

    @abstractmethod
    def analyze_diff(self, diff_content: str, file_path: str) -> GroundTruth:
        """
        Analyze a diff and extract ground truth.

        Args:
            diff_content: The unified diff content
            file_path: Path to the file being analyzed

        Returns:
            GroundTruth object with extracted changes
        """
        pass

    def extract_added_lines(self, diff_content: str) -> List[str]:
        """Extract lines that were added (start with +)."""
        lines = []
        for line in diff_content.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                lines.append(line[1:])  # Remove the + prefix
        return lines

    def extract_removed_lines(self, diff_content: str) -> List[str]:
        """Extract lines that were removed (start with -)."""
        lines = []
        for line in diff_content.split('\n'):
            if line.startswith('-') and not line.startswith('---'):
                lines.append(line[1:])  # Remove the - prefix
        return lines

    def is_new_file(self, diff_content: str) -> bool:
        """Check if this is a new file being added."""
        return '/dev/null' in diff_content.split('\n')[0]

    def is_deleted_file(self, diff_content: str) -> bool:
        """Check if this is a file being deleted."""
        lines = diff_content.split('\n')
        return len(lines) > 1 and '/dev/null' in lines[1]


class UniversalAnalyzer(LanguageAnalyzer):
    """
    Fallback analyzer using pattern matching.
    Works for any language but less accurate than language-specific analyzers.
    """

    @property
    def supported_extensions(self) -> List[str]:
        return ["*"]  # Supports all

    @property
    def language_name(self) -> str:
        return "Universal (Pattern-based)"

    def analyze_diff(self, diff_content: str, file_path: str) -> GroundTruth:
        """Use pattern matching to extract basic information."""
        import re

        truth = GroundTruth(file_path=file_path, language="unknown")
        added_lines = self.extract_added_lines(diff_content)
        removed_lines = self.extract_removed_lines(diff_content)

        # Universal patterns that work across languages
        patterns = {
            'function': [
                r'(def|function|func|fn|func\s+\(.*?\))\s+(\w+)',
                r'(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>',  # Arrow functions
            ],
            'class': [
                r'(class|struct|interface|type)\s+(\w+)',
            ],
            'import': [
                r'(import|require|include|use|from)\s+(.+)',
            ],
            'validation': [
                r'if\s+.*(?:nil|null|None|undefined|empty)',
                r'(?:raise|throw)\s+\w+Error',
            ],
            'error_handling': [
                r'try\s*\{',
                r'catch\s*\(',
                r'if\s+err\s*!=',
            ],
        }

        # Analyze added lines
        for line in added_lines:
            for category, pattern_list in patterns.items():
                for pattern in pattern_list:
                    match = re.search(pattern, line)
                    if match:
                        name = match.group(2) if match.lastindex >= 2 else line.strip()[:50]
                        truth.changes.append(CodeChange(
                            change_type=ChangeType.ADDED,
                            category=category,
                            name=name,
                            details={'line': line.strip()},
                            confidence=0.7  # Lower confidence for pattern matching
                        ))

        # Track file-level changes
        if self.is_new_file(diff_content):
            truth.metadata['new_file'] = True
        if self.is_deleted_file(diff_content):
            truth.metadata['deleted_file'] = True

        truth.metadata['lines_added'] = len(added_lines)
        truth.metadata['lines_removed'] = len(removed_lines)

        return truth

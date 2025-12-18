"""Factory for creating language-specific analyzers."""

from pathlib import Path
from typing import Optional
from .base import LanguageAnalyzer, UniversalAnalyzer
from .python_analyzer import PythonAnalyzer
from .javascript_analyzer import JavaScriptAnalyzer
from .go_analyzer import GoAnalyzer


class AnalyzerFactory:
    """Factory for creating appropriate analyzers based on file extension."""

    _analyzers = [
        PythonAnalyzer(),
        JavaScriptAnalyzer(),
        GoAnalyzer(),
    ]

    _fallback = UniversalAnalyzer()

    @classmethod
    def get_analyzer(cls, file_path: str) -> LanguageAnalyzer:
        """
        Get the appropriate analyzer for a file.

        Args:
            file_path: Path to the file

        Returns:
            Language-specific analyzer or universal fallback
        """
        ext = Path(file_path).suffix.lower()

        for analyzer in cls._analyzers:
            if ext in analyzer.supported_extensions:
                return analyzer

        # Fallback to universal analyzer
        return cls._fallback

    @classmethod
    def register_analyzer(cls, analyzer: LanguageAnalyzer):
        """Register a custom analyzer."""
        cls._analyzers.insert(0, analyzer)  # Higher priority for custom analyzers

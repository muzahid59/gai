"""
Language-specific parsers for semantic diff analysis.

This package contains parsers that extract semantic information from code changes.
Each parser understands the structure of a specific programming language.
"""

from .base import BaseParser

__all__ = ['BaseParser']

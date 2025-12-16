"""
Base parser abstract class for language-specific parsers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict
from functools import lru_cache
import subprocess


class BaseParser(ABC):
    """Base class for language-specific parsers."""

    @abstractmethod
    def parse_file_changes(self, file_info: Dict) -> List['SemanticChange']:
        """
        Parse changes for a specific file.

        Args:
            file_info: Dictionary containing 'path' and 'status' (A/M/D)

        Returns:
            List of SemanticChange objects
        """
        pass

    @lru_cache(maxsize=256)
    def _get_file_content(self, filepath: str, revision: str) -> str:
        """
        Get file content from git at specific revision.

        PERFORMANCE: Cached using LRU cache to avoid repeated git show calls.
        Typical scenario: 50 files changed, each needs HEAD and :0 = 100 git calls
        With cache: Only 100 unique calls, subsequent accesses are instant

        Args:
            filepath: Path to the file
            revision: Git revision (e.g., 'HEAD', ':0' for staged)

        Returns:
            File content as string, or empty string if not found
        """
        try:
            result = subprocess.run(
                ["git", "show", f"{revision}:{filepath}"],
                capture_output=True,
                text=True,
                check=False,
                timeout=30  # Prevent hanging on large files
            )

            if result.returncode != 0:
                # Check if file is binary or doesn't exist
                if b'binary file' in result.stderr.encode():
                    from gai.logger import logger
                    logger.debug(f"Skipping binary file: {filepath}")
                    return ""
                return ""

            # Check file size (warn if > 1MB)
            content = result.stdout
            if len(content) > 1_000_000:  # 1MB
                from gai.logger import logger
                logger.warning(f"Large file detected: {filepath} ({len(content)} bytes)")

            return content

        except subprocess.TimeoutExpired:
            from gai.logger import logger
            logger.error(f"Timeout reading file: {filepath}")
            return ""
        except Exception as e:
            from gai.logger import logger
            logger.error(f"Error reading file {filepath}: {e}")
            return ""

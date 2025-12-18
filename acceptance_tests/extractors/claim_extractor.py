"""Extract claims from commit messages."""

import re
from dataclasses import dataclass
from typing import List, Set
from enum import Enum


class ClaimType(Enum):
    """Types of claims that can be made in commit messages."""
    ADD = "add"
    REMOVE = "remove"
    FIX = "fix"
    UPDATE = "update"
    REFACTOR = "refactor"
    IMPROVE = "improve"
    SECURITY = "security"
    BREAKING_CHANGE = "breaking_change"


@dataclass
class Claim:
    """A single claim extracted from a commit message."""
    claim_type: ClaimType
    subject: str  # What the claim is about (e.g., "email validation")
    details: str = ""
    confidence: float = 1.0

    def __repr__(self):
        return f"Claim({self.claim_type.value}: {self.subject})"


class ClaimExtractor:
    """Extracts verifiable claims from commit messages."""

    # Action verbs mapped to claim types
    ACTION_VERBS = {
        ClaimType.ADD: [
            'add', 'adding', 'added', 'create', 'creating', 'created',
            'introduce', 'introducing', 'introduced', 'implement', 'implementing', 'implemented'
        ],
        ClaimType.REMOVE: [
            'remove', 'removing', 'removed', 'delete', 'deleting', 'deleted',
            'drop', 'dropping', 'dropped'
        ],
        ClaimType.FIX: [
            'fix', 'fixing', 'fixed', 'resolve', 'resolving', 'resolved',
            'correct', 'correcting', 'corrected', 'patch', 'patching', 'patched'
        ],
        ClaimType.UPDATE: [
            'update', 'updating', 'updated', 'modify', 'modifying', 'modified',
            'change', 'changing', 'changed', 'revise', 'revising', 'revised'
        ],
        ClaimType.REFACTOR: [
            'refactor', 'refactoring', 'refactored', 'restructure', 'restructuring', 'restructured',
            'reorganize', 'reorganizing', 'reorganized'
        ],
        ClaimType.IMPROVE: [
            'improve', 'improving', 'improved', 'optimize', 'optimizing', 'optimized',
            'enhance', 'enhancing', 'enhanced'
        ],
        ClaimType.SECURITY: [
            'secure', 'securing', 'secured', 'harden', 'hardening', 'hardened',
            'sanitize', 'sanitizing', 'sanitized'
        ],
    }

    # Technical terms to look for
    TECH_TERMS = {
        'function': ['function', 'method', 'func'],
        'class': ['class', 'struct', 'interface', 'type'],
        'validation': ['validation', 'validate', 'check', 'verify'],
        'error_handling': ['error handling', 'exception', 'try-catch', 'error check'],
        'type_hint': ['type hint', 'type annotation', 'typing'],
        'documentation': ['docstring', 'documentation', 'comment', 'doc'],
        'test': ['test', 'testing', 'spec', 'unittest'],
        'import': ['import', 'dependency', 'package', 'module'],
        'async': ['async', 'await', 'asynchronous', 'promise'],
        'cache': ['cache', 'caching', 'memoize'],
        'database': ['database', 'db', 'query', 'sql'],
        'api': ['api', 'endpoint', 'route'],
        'security': ['security', 'sql injection', 'xss', 'csrf', 'authentication', 'authorization'],
    }

    def extract_claims(self, commit_message: str) -> List[Claim]:
        """
        Extract claims from a commit message.

        Args:
            commit_message: The commit message to analyze

        Returns:
            List of claims found in the message
        """
        claims = []

        # Normalize message
        message = commit_message.lower()

        # Check for breaking changes
        if 'breaking change' in message or 'breaking:' in message:
            claims.append(Claim(
                claim_type=ClaimType.BREAKING_CHANGE,
                subject='breaking change',
                details=self._extract_breaking_change_details(commit_message)
            ))

        # Extract action-based claims
        claims.extend(self._extract_action_claims(message, commit_message))

        # Extract technology-specific claims
        claims.extend(self._extract_tech_claims(message))

        # Extract security-related claims
        claims.extend(self._extract_security_claims(message))

        # Extract specific entities mentioned (file names, function names, etc.)
        claims.extend(self._extract_entity_claims(commit_message))

        return claims

    def _extract_action_claims(self, message: str, original_message: str) -> List[Claim]:
        """Extract claims based on action verbs."""
        claims = []

        for claim_type, verbs in self.ACTION_VERBS.items():
            for verb in verbs:
                # Look for patterns like "add X", "adding X"
                pattern = rf'\b{verb}\b\s+([^,.\n]+)'
                matches = re.finditer(pattern, message)

                for match in matches:
                    subject = match.group(1).strip()
                    # Clean up the subject
                    subject = subject.split(' to ')[0]  # Remove "to X" parts
                    subject = subject.split(' for ')[0]  # Remove "for X" parts
                    subject = subject.split(' with ')[0]  # Remove "with X" parts

                    if len(subject) > 3:  # Skip very short subjects
                        claims.append(Claim(
                            claim_type=claim_type,
                            subject=subject,
                            confidence=0.8
                        ))

        return claims

    def _extract_tech_claims(self, message: str) -> List[Claim]:
        """Extract technology/pattern-specific claims."""
        claims = []

        for category, terms in self.TECH_TERMS.items():
            for term in terms:
                if term in message:
                    claims.append(Claim(
                        claim_type=ClaimType.ADD,  # Default to ADD
                        subject=category,
                        details=f'mentions {term}',
                        confidence=0.7
                    ))
                    break  # Only add once per category

        return claims

    def _extract_security_claims(self, message: str) -> List[Claim]:
        """Extract security-related claims."""
        claims = []

        security_keywords = [
            'sql injection', 'xss', 'csrf', 'injection', 'sanitize',
            'validate input', 'escape', 'authentication', 'authorization',
            'permission', 'access control'
        ]

        for keyword in security_keywords:
            if keyword in message:
                claims.append(Claim(
                    claim_type=ClaimType.SECURITY,
                    subject=keyword,
                    confidence=0.9
                ))

        return claims

    def _extract_entity_claims(self, message: str) -> List[Claim]:
        """Extract mentions of specific entities (functions, classes, files)."""
        claims = []

        # Look for code entities in backticks or CamelCase/snake_case
        patterns = [
            r'`([a-zA-Z_][a-zA-Z0-9_]*)`',  # Backtick entities
            r'\b([A-Z][a-z]+[A-Z]\w*)\b',   # CamelCase
            r'\b([a-z]+_[a-z_]+)\b',         # snake_case
        ]

        entities = set()
        for pattern in patterns:
            matches = re.finditer(pattern, message)
            for match in matches:
                entity = match.group(1)
                if len(entity) > 2 and entity not in entities:
                    entities.add(entity)
                    claims.append(Claim(
                        claim_type=ClaimType.ADD,  # Assume mentioned entities were added/modified
                        subject=entity,
                        details='named entity',
                        confidence=0.6
                    ))

        return claims

    def _extract_breaking_change_details(self, message: str) -> str:
        """Extract details about breaking changes."""
        lines = message.split('\n')
        for i, line in enumerate(lines):
            if 'breaking change' in line.lower():
                # Return the next line(s) as details
                if i + 1 < len(lines):
                    return lines[i + 1].strip()
        return ""

    def extract_keywords(self, commit_message: str) -> Set[str]:
        """Extract important keywords from commit message."""
        keywords = set()

        # Get all claim subjects
        claims = self.extract_claims(commit_message)
        for claim in claims:
            keywords.add(claim.subject)

        # Add technology terms found
        message_lower = commit_message.lower()
        for category, terms in self.TECH_TERMS.items():
            for term in terms:
                if term in message_lower:
                    keywords.add(category)

        return keywords

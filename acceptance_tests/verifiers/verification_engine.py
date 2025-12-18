"""Engine for verifying commit message claims against code ground truth."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Set
from ..analyzers.base import GroundTruth, CodeChange, ChangeType
from ..extractors.claim_extractor import Claim, ClaimType


@dataclass
class VerificationResult:
    """Result of verifying a single claim."""
    claim: Claim
    verified: bool
    confidence: float
    evidence: List[CodeChange] = field(default_factory=list)
    reason: str = ""


@dataclass
class AccuracyReport:
    """Overall accuracy report for a commit message."""
    total_claims: int
    verified_claims: int
    false_claims: int
    missing_facts: int

    verification_results: List[VerificationResult] = field(default_factory=list)
    ground_truth: GroundTruth = None

    @property
    def accuracy_score(self) -> float:
        """Percentage of claims that are factually correct."""
        if self.total_claims == 0:
            return 0.0
        return (self.verified_claims / self.total_claims) * 100

    @property
    def completeness_score(self) -> float:
        """How well the message covers the actual changes."""
        if not self.ground_truth:
            return 0.0

        total_changes = len(self.ground_truth.changes)
        if total_changes == 0:
            return 100.0

        # Count how many ground truth changes are mentioned
        mentioned = set()
        for result in self.verification_results:
            if result.verified:
                for evidence in result.evidence:
                    mentioned.add(id(evidence))

        return (len(mentioned) / total_changes) * 100

    @property
    def hallucination_rate(self) -> float:
        """Percentage of claims that are false."""
        if self.total_claims == 0:
            return 0.0
        return (self.false_claims / self.total_claims) * 100

    @property
    def overall_score(self) -> float:
        """Combined score (accuracy + completeness - hallucinations)."""
        return (self.accuracy_score + self.completeness_score) / 2 - self.hallucination_rate


class VerificationEngine:
    """Verifies commit message claims against ground truth from code analysis."""

    def __init__(self, fuzzy_match_threshold: float = 0.6):
        """
        Initialize verification engine.

        Args:
            fuzzy_match_threshold: Minimum similarity for fuzzy string matching (0-1)
        """
        self.fuzzy_threshold = fuzzy_match_threshold

    def verify(self, claims: List[Claim], ground_truth: GroundTruth) -> AccuracyReport:
        """
        Verify claims against ground truth.

        Args:
            claims: List of claims extracted from commit message
            ground_truth: Ground truth extracted from diff analysis

        Returns:
            AccuracyReport with verification results
        """
        results = []
        verified_count = 0
        false_count = 0

        for claim in claims:
            result = self._verify_claim(claim, ground_truth)
            results.append(result)

            if result.verified:
                verified_count += 1
            else:
                false_count += 1

        # Count missing important changes
        missing = self._find_missing_changes(claims, ground_truth)

        return AccuracyReport(
            total_claims=len(claims),
            verified_claims=verified_count,
            false_claims=false_count,
            missing_facts=len(missing),
            verification_results=results,
            ground_truth=ground_truth
        )

    def _verify_claim(self, claim: Claim, truth: GroundTruth) -> VerificationResult:
        """Verify a single claim against ground truth."""

        # Map claim types to change types
        change_type_map = {
            ClaimType.ADD: ChangeType.ADDED,
            ClaimType.REMOVE: ChangeType.REMOVED,
            ClaimType.FIX: ChangeType.MODIFIED,
            ClaimType.UPDATE: ChangeType.MODIFIED,
            ClaimType.REFACTOR: ChangeType.MODIFIED,
        }

        expected_change_type = change_type_map.get(claim.claim_type)

        # Search for evidence in ground truth
        evidence = []

        # Check if claim subject matches any change names
        for change in truth.changes:
            if expected_change_type and change.change_type != expected_change_type:
                continue

            # Exact match
            if self._is_match(claim.subject, change.name):
                evidence.append(change)

            # Check in category
            elif self._is_match(claim.subject, change.category):
                evidence.append(change)

            # Check in details
            elif self._match_in_details(claim.subject, change.details):
                evidence.append(change)

        # Determine if verified
        verified = len(evidence) > 0
        confidence = claim.confidence if verified else 0.0

        # Adjust confidence based on evidence quality
        if evidence:
            confidence = min(1.0, confidence + len(evidence) * 0.1)

        reason = self._generate_reason(claim, evidence, verified)

        return VerificationResult(
            claim=claim,
            verified=verified,
            confidence=confidence,
            evidence=evidence,
            reason=reason
        )

    def _is_match(self, claim_text: str, truth_text: str) -> bool:
        """Check if two strings match (exact or fuzzy)."""
        claim_text = claim_text.lower().strip()
        truth_text = truth_text.lower().strip()

        # Exact match
        if claim_text == truth_text:
            return True

        # One contains the other
        if claim_text in truth_text or truth_text in claim_text:
            return True

        # Fuzzy match using word overlap
        claim_words = set(claim_text.split())
        truth_words = set(truth_text.split())

        if not claim_words or not truth_words:
            return False

        overlap = len(claim_words & truth_words)
        similarity = overlap / max(len(claim_words), len(truth_words))

        return similarity >= self.fuzzy_threshold

    def _match_in_details(self, claim_text: str, details: Dict[str, Any]) -> bool:
        """Check if claim text matches anything in change details."""
        claim_text = claim_text.lower()

        for key, value in details.items():
            value_str = str(value).lower()
            if claim_text in value_str or value_str in claim_text:
                return True

        return False

    def _generate_reason(self, claim: Claim, evidence: List[CodeChange], verified: bool) -> str:
        """Generate human-readable reason for verification result."""
        if verified:
            if len(evidence) == 1:
                return f"Found in code: {evidence[0]}"
            else:
                return f"Found {len(evidence)} matching changes in code"
        else:
            return f"No evidence found for '{claim.subject}' in diff"

    def _find_missing_changes(self, claims: List[Claim], truth: GroundTruth) -> List[CodeChange]:
        """Find important changes that weren't mentioned in claims."""
        mentioned = set()

        # Collect all names mentioned in claims
        for claim in claims:
            mentioned.add(claim.subject.lower())

        # Find unmention important changes
        missing = []
        important_categories = {'function', 'class', 'method', 'struct', 'interface'}

        for change in truth.changes:
            if change.category in important_categories:
                if change.name.lower() not in mentioned:
                    # Check if any claim mentions this change
                    is_mentioned = False
                    for claim in claims:
                        if self._is_match(claim.subject, change.name):
                            is_mentioned = True
                            break

                    if not is_mentioned:
                        missing.append(change)

        return missing

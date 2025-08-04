from abc import ABC, abstractmethod

from typing import List, Dict

class Provider(ABC):
    @abstractmethod
    def generate_commit_message(self, diff, oneline: bool = False):
        pass

    @abstractmethod
    def analyze_diff_for_commits(self, diff: str) -> List[Dict]:
        """
        Analyzes a git diff and suggests logical commit boundaries/descriptions.
        Returns a list of dictionaries, where each dict represents a suggested commit.
        Example: [{'description': 'Fix login bug'}, {'description': 'Add user profile page'}]
        """
        pass

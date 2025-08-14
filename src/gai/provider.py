from abc import ABC, abstractmethod


class Provider(ABC):
    @abstractmethod
    def generate_commit_message(self, diff, oneline: bool = False):
        pass

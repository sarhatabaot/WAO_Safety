from abc import ABC, abstractmethod


class SafetyChecker(ABC):
    """
    This is supposed to be a base class for all safety checkers
    """
    @abstractmethod
    def is_safe(self, project, measurements) -> bool:
        pass

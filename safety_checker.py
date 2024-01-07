from abc import ABC, abstractmethod


class SafetyChecker(ABC):
    @abstractmethod
    def is_safe(self, project, measurements) -> bool:
        pass

"""Shared interface for relative mouse output."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class Sink(ABC):
    """Receive relative motion, button changes and wheel steps.

    Buttons are numbered 1 (left), 2 (right), and 3 (middle). A sink used
    as a context manager closes on exit, including when the body raises.
    """

    @abstractmethod
    def move(self, dx: int, dy: int) -> None:
        """Move by the requested relative displacement."""

    @abstractmethod
    def button(self, btn: int, down: bool) -> None:
        """Press or release a button; reject other numbers with ValueError."""

    @abstractmethod
    def scroll(self, n: int) -> None:
        """Scroll by signed wheel steps."""

    @abstractmethod
    def close(self) -> None:
        """Finish output and release resources."""

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

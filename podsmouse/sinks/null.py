"""Recording sink for tests and hardware-free runs."""

from .base import Sink


class NullSink(Sink):
    """Record calls in order without producing mouse output.

    ``calls`` contains ("move", dx, dy), ("button", btn, down),
    ("scroll", n), and ("close",) tuples. Each instance owns its list.
    Close calls are recorded too; this sink has no resources to release.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str | int | bool, ...]] = []

    def move(self, dx: int, dy: int) -> None:
        self.calls.append(("move", dx, dy))

    def button(self, btn: int, down: bool) -> None:
        if btn not in (1, 2, 3):
            raise ValueError("button must be 1 (left), 2 (right), or 3 (middle)")
        self.calls.append(("button", btn, down))

    def scroll(self, n: int) -> None:
        self.calls.append(("scroll", n))

    def close(self) -> None:
        self.calls.append(("close",))

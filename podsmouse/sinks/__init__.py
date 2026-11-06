"""Mouse output interfaces and implementations."""

from .base import Sink
from .null import NullSink

__all__ = ["Sink", "NullSink"]

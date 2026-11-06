"""Mouse output interfaces and implementations."""

from .base import Sink
from .hid_gadget import HidSink
from .null import NullSink

__all__ = ["Sink", "NullSink", "HidSink"]

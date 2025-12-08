from __future__ import annotations

from enum import Enum
from typing import Protocol as TypingProtocol, TYPE_CHECKING, List

if TYPE_CHECKING:
    from .rules import Rule


class Direction(str, Enum):
    IN = "IN"
    OUT = "OUT"
    FORWARD = "FORWARD"

    @property
    def chain(self) -> str:
        return {
            Direction.IN: "INPUT",
            Direction.OUT: "OUTPUT",
            Direction.FORWARD: "FORWARD",
        }[self]


class Protocol(str, Enum):
    TCP = "TCP"
    UDP = "UDP"
    ICMP = "ICMP"

    @property
    def cli_value(self) -> str:
        return self.value.lower()


class IDatabaseService(TypingProtocol):
    def save(self, rules: List["Rule"]) -> None:
        ...

    def load(self) -> List["Rule"]:
        ...

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Type
from uuid import UUID, uuid4

from .types import Direction, Protocol


@dataclass
class Rule(ABC):
    direction: Direction
    protocol: Protocol
    port: Optional[int] = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.protocol != Protocol.ICMP and self.port is None:
            raise ValueError("Port is required for TCP and UDP rules")
        if self.port is not None and not 0 < self.port <= 65535:
            raise ValueError("Port must be between 1 and 65535")

    @property
    def type_name(self) -> str:
        return self.__class__.__name__.replace("Rule", "").upper()

    @property
    def short_id(self) -> str:
        return str(self.id).split("-")[0]

    def _build_command(self, target: str) -> str:
        parts = ["iptables", "-A", self.direction.chain, "-p", self.protocol.cli_value]
        if self.protocol != Protocol.ICMP and self.port is not None:
            parts += ["--dport", str(self.port)]
        parts += ["-j", target]
        return " ".join(parts)

    @abstractmethod
    def get_command(self) -> str:
        ...

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": str(self.id),
            "direction": self.direction.value,
            "protocol": self.protocol.value,
            "port": self.port,
            "type": self.__class__.__name__,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Rule":
        rule_type = data.get("type")
        rule_cls = _RULE_TYPES.get(rule_type)
        if not rule_cls:
            raise ValueError(f"Unknown rule type: {rule_type}")
        port_value = data.get("port")
        return rule_cls(
            direction=Direction(data["direction"]),
            protocol=Protocol(data["protocol"]),
            port=int(port_value) if port_value is not None else None,
            id=UUID(data["id"]),
        )


class AllowRule(Rule):
    def get_command(self) -> str:
        return self._build_command("ACCEPT")


class DenyRule(Rule):
    def get_command(self) -> str:
        return self._build_command("DROP")


class RejectRule(Rule):
    def get_command(self) -> str:
        return self._build_command("REJECT")


_RULE_TYPES: Dict[str, Type[Rule]] = {
    "AllowRule": AllowRule,
    "DenyRule": DenyRule,
    "RejectRule": RejectRule,
}

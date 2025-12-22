from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from domain.rules import Rule
from domain.types import IDatabaseService


class JsonDatabase(IDatabaseService):
    _instance: Optional["JsonDatabase"] = None

    def __init__(self, file_path: Path | str) -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls, file_path: Path | str | None = None) -> "JsonDatabase":
        """Singleton accessor; optional custom path for tests."""
        target_path = Path(file_path) if file_path else None
        if cls._instance is None:
            cls._instance = cls(target_path or cls._default_path())
        elif target_path and target_path != cls._instance.file_path:
            cls._instance = cls(target_path)
        return cls._instance

    @staticmethod
    def _default_path() -> Path:
        base_dir = Path(__file__).resolve().parents[2]
        return base_dir / "data" / "rules.json"

    def save(self, rules: List[Rule]) -> None:
        """Persist rules to disk as JSON."""
        payload = [rule.to_dict() for rule in rules]
        with self.file_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def load(self) -> List[Rule]:
        """Load rules from disk; empty list on first run or parse error."""
        if not self.file_path.exists():
            return []
        try:
            with self.file_path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except json.JSONDecodeError:
            return []

        rules: List[Rule] = []
        for item in raw:
            try:
                rules.append(Rule.from_dict(item))
            except (ValueError, KeyError, TypeError):
                continue
        return rules

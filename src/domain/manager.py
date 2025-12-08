from __future__ import annotations

import subprocess
from typing import Callable, List, Optional
from uuid import UUID

from .rules import Rule
from .types import IDatabaseService
from .firewall_backend import FirewallBackend


class FirewallError(Exception):
    pass


class CommandExecutionError(FirewallError):
    def __init__(self, command: str, stderr: str) -> None:
        super().__init__(f"Failed to run '{command}': {stderr}")
        self.command = command
        self.stderr = stderr


class FirewallManager:
    def __init__(self, db: IDatabaseService) -> None:
        self.db = db
        self.rules: List[Rule] = self.db.load()
        self.backend = FirewallBackend.get_backend()

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)
        self.db.save(self.rules)

    def update_rule(self, rule_id: str | UUID, new_rule: Rule) -> bool:
        normalized = str(rule_id)
        for idx, rule in enumerate(self.rules):
            if str(rule.id) == normalized:
                new_rule.id = rule.id
                self.rules[idx] = new_rule
                self.db.save(self.rules)
                return True
        return False

    def get_rule(self, rule_id: str | UUID) -> Optional[Rule]:
        normalized = str(rule_id)
        for rule in self.rules:
            if str(rule.id) == normalized:
                return rule
        return None

    def remove_rule(self, rule_id: str | UUID) -> bool:
        normalized = str(rule_id)
        for idx, rule in enumerate(self.rules):
            if str(rule.id) == normalized:
                del self.rules[idx]
                self.db.save(self.rules)
                return True
        return False

    def apply_configuration(
        self,
        execute: bool = True,
        runner: Optional[Callable[[str], None]] = None,
    ) -> List[str]:
        commands = [rule.get_command(self.backend) for rule in self.rules]
        if not execute:
            return commands

        # Remove any previously applied rules tagged by this tool before re-applying.
        self.backend.cleanup_existing_rules(runner=runner)
        for command in commands:
            self.backend.run_command(command, runner)
        return commands

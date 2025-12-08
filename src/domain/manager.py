from __future__ import annotations

import shlex
import subprocess
from typing import Callable, List, Optional
from uuid import UUID

from .rules import Rule
from .types import IDatabaseService


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

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)
        self.db.save(self.rules)

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
        commands = [rule.get_command() for rule in self.rules]
        if not execute:
            return commands

        for command in commands:
            self._run_command(command, runner)
        return commands

    def _run_command(
        self,
        command: str,
        runner: Optional[Callable[[str], None]] = None,
    ) -> None:
        if runner:
            runner(command)
            return

        completed = subprocess.run(
            shlex.split(command),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise CommandExecutionError(command, completed.stderr.strip())

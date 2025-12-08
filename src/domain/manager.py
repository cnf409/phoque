from __future__ import annotations

import subprocess
import shlex
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
        commands = [rule.get_command() for rule in self.rules]
        if not execute:
            return commands

        # Remove any previously applied rules tagged by this tool before re-applying.
        self._cleanup_existing_rules(runner=runner)
        for command in commands:
            self._run_command(command, runner)
        return commands

    def _run_command(
        self,
        command: str,
        runner: Optional[Callable[[str], None]] = None,
        ignore_errors: bool = False,
    ) -> None:
        if runner:
            runner(command)
            return

        completed = subprocess.run(
            command if isinstance(command, list) else shlex.split(command),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 and not ignore_errors:
            raise CommandExecutionError(command, completed.stderr.strip())

    def _cleanup_existing_rules(
        self,
        runner: Optional[Callable[[str], None]] = None,
    ) -> None:
        for chain in ("INPUT", "OUTPUT", "FORWARD"):
            list_cmd = f"iptables -S {chain}"
            completed = subprocess.run(
                list_cmd.split(),
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                continue
            for line in completed.stdout.splitlines():
                if 'comment "phoque-' not in line and "comment phoque-" not in line:
                    continue
                if not line.startswith("-A"):
                    continue
                delete_cmd = line.replace("-A", "-D", 1)
                full_cmd = f"iptables {delete_cmd}"
                self._run_command(full_cmd, runner, ignore_errors=True)

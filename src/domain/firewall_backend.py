from __future__ import annotations

import platform
import shlex
import subprocess
from abc import ABC, abstractmethod
from typing import List, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .rules import Rule


class FirewallBackend(ABC):
    """Abstract base class for firewall backends."""

    @abstractmethod
    def build_add_command(self, rule: "Rule", target: str) -> str:
        """Build command to add a firewall rule."""
        ...

    @abstractmethod
    def build_delete_command(self, rule: "Rule", target: str) -> str:
        """Build command to delete a firewall rule."""
        ...

    @abstractmethod
    def cleanup_existing_rules(
        self,
        runner: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Remove previously applied rules tagged by this tool."""
        ...

    @abstractmethod
    def run_command(
        self,
        command: str,
        runner: Optional[Callable[[str], None]] = None,
        ignore_errors: bool = False,
    ) -> None:
        """Execute a firewall command."""
        ...

    @staticmethod
    def get_backend() -> "FirewallBackend":
        """Return the appropriate backend for the current OS."""
        system = platform.system().lower()
        if system == "windows":
            return WindowsFirewallBackend()
        elif system == "linux":
            return LinuxFirewallBackend()
        else:
            raise RuntimeError(f"Unsupported operating system: {system}")


class LinuxFirewallBackend(FirewallBackend):
    """iptables backend for Linux systems."""

    def build_add_command(self, rule: "Rule", target: str) -> str:
        from .rules import Rule
        from .types import Protocol

        parts = [
            "iptables",
            "-A",
            rule.direction.chain,
            "-p",
            rule.protocol.cli_value,
        ]
        if rule.protocol != Protocol.ICMP and rule.port not in (None, "*"):
            parts += ["--dport", self._format_port_for_cli(rule.port)]
        parts += ["-m", "comment", "--comment", rule.comment]
        parts += ["-j", target]
        return " ".join(parts)

    def build_delete_command(self, rule: "Rule", target: str) -> str:
        return self.build_add_command(rule, target).replace("iptables -A", "iptables -D", 1)

    def cleanup_existing_rules(
        self,
        runner: Optional[Callable[[str], None]] = None,
    ) -> None:
        for chain in ("INPUT", "OUTPUT", "FORWARD"):
            list_cmd = f"iptables -S {chain}"
            completed = subprocess.run(
                shlex.split(list_cmd),
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
                self.run_command(full_cmd, runner, ignore_errors=True)

    def run_command(
        self,
        command: str,
        runner: Optional[Callable[[str], None]] = None,
        ignore_errors: bool = False,
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
        if completed.returncode != 0 and not ignore_errors:
            from .manager import CommandExecutionError
            raise CommandExecutionError(command, completed.stderr.strip())

    def _format_port_for_cli(self, port: str) -> str:
        return port.replace("-", ":")


class WindowsFirewallBackend(FirewallBackend):
    """Windows Firewall backend using netsh advfirewall."""

    def build_add_command(self, rule: "Rule", target: str) -> str:
        from .types import Direction, Protocol

        # Map direction to Windows firewall direction
        if rule.direction == Direction.IN:
            direction = "in"
        elif rule.direction == Direction.OUT:
            direction = "out"
        else:
            # FORWARD not directly supported in Windows Firewall
            # We'll create both in and out rules for this case
            direction = "in"

        # Map target to Windows action
        action_map = {
            "ACCEPT": "allow",
            "DROP": "block",
            "REJECT": "block",  # Windows doesn't have reject, use block
        }
        action = action_map.get(target, "block")

        # Build the rule name with our tag for identification
        rule_name = f"phoque-{rule.short_id}"

        parts = [
            "netsh",
            "advfirewall",
            "firewall",
            "add",
            "rule",
            f'name="{rule_name}"',
            f"dir={direction}",
            f"action={action}",
        ]

        # Add protocol
        if rule.protocol == Protocol.ICMP:
            parts.append("protocol=icmpv4")
        else:
            parts.append(f"protocol={rule.protocol.cli_value}")

        # Add port if applicable
        if rule.protocol != Protocol.ICMP and rule.port not in (None, "*"):
            port_value = self._format_port_for_windows(rule.port)
            parts.append(f"localport={port_value}")

        parts.append("enable=yes")

        return " ".join(parts)

    def build_delete_command(self, rule: "Rule", target: str) -> str:
        rule_name = f"phoque-{rule.short_id}"
        return f'netsh advfirewall firewall delete rule name="{rule_name}"'

    def cleanup_existing_rules(
        self,
        runner: Optional[Callable[[str], None]] = None,
    ) -> None:
        # Directly delete rules with our naming pattern - more reliable than parsing
        # Try to delete any rules starting with "phoque-"
        # We'll use a simple approach: list rules and extract names with our prefix
        
        list_cmd = "netsh advfirewall firewall show rule name=all"
        completed = subprocess.run(
            list_cmd,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return

        # Parse output to find our rules - handle multiple languages
        rules_to_delete = set()
        for line in completed.stdout.splitlines():
            line = line.strip()
            # Look for lines containing "phoque-" which is our rule naming pattern
            # Works regardless of language (Rule Name: / Nom de la règle:)
            if ":" in line and "phoque-" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    potential_name = parts[1].strip()
                    if potential_name.startswith("phoque-"):
                        rules_to_delete.add(potential_name)

        # Delete each rule we found
        for rule_name in rules_to_delete:
            delete_cmd = f'netsh advfirewall firewall delete rule name="{rule_name}"'
            self.run_command(delete_cmd, runner, ignore_errors=True)

    def run_command(
        self,
        command: str,
        runner: Optional[Callable[[str], None]] = None,
        ignore_errors: bool = False,
    ) -> None:
        if runner:
            runner(command)
            return

        # Windows needs shell=True for netsh commands
        completed = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0 and not ignore_errors:
            from .manager import CommandExecutionError
            stderr = completed.stderr.strip() or completed.stdout.strip()
            raise CommandExecutionError(command, stderr)

    def _format_port_for_windows(self, port: str) -> str:
        """Format port for Windows netsh (uses '-' for ranges)."""
        return port.replace(":", "-")

from __future__ import annotations

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(SCRIPT_DIR)

# Avoid shadowing stdlib modules when running this file directly.
if sys.path and sys.path[0] == SCRIPT_DIR:
    sys.path.pop(0)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from services.app import FirewallApp


def main() -> None:
    app = FirewallApp()
    app.run()

if __name__ == "__main__":
    main()
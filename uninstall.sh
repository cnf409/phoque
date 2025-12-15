#!/bin/bash

# Get the directory where the script is located
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

LAUNCHER_PATH="/usr/local/bin/phoque"

echo "Uninstalling phoque."

# Remove launcher
if [ -f "$LAUNCHER_PATH" ]; then
    echo "Removing $LAUNCHER_PATH."
    if rm "$LAUNCHER_PATH" 2>/dev/null; then
        echo "Successfully removed $LAUNCHER_PATH"
    else
        echo "Requires root to remove $LAUNCHER_PATH"
        sudo rm "$LAUNCHER_PATH"
    fi
else
    echo "Phoque is not installed (command not found)."
fi

# Remove virtual environment
if [ -d "$INSTALL_DIR/.venv" ]; then
    echo "Removing virtual environment (.venv)."
    rm -rf "$INSTALL_DIR/.venv"
    echo "Virtual environment removed."
else
    echo "Virtual environment not found."
fi

echo "Uninstallation complete."

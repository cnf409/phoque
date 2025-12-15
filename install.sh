#!/bin/bash

# Get the directory where the script is located
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo "Installing phoque from $INSTALL_DIR."

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    echo "Creating virtual environment."
    python3 -m venv "$INSTALL_DIR/.venv"
else
    echo "Virtual environment already exists."
fi

# Install requirements
echo "Installing requirements..."
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Create launcher script content
LAUNCHER_TEMP=$(mktemp)
cat <<EOF > "$LAUNCHER_TEMP"
#!/bin/bash
# Launcher for phoque
cd "$INSTALL_DIR"

# Check if running as root
if [ "\$EUID" -ne 0 ]; then
  exec sudo -E "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/src/domain/main.py" "\$@"
else
  exec "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/src/domain/main.py" "\$@"
fi
EOF

chmod +x "$LAUNCHER_TEMP"

LAUNCHER_PATH="/usr/local/bin/phoque"
echo "Installing command to $LAUNCHER_PATH."

# Move the launcher to the target location
if mv "$LAUNCHER_TEMP" "$LAUNCHER_PATH" 2>/dev/null; then
    echo "Successfully installed to $LAUNCHER_PATH"
else
    echo "Requires root to install to $LAUNCHER_PATH"
    sudo mv "$LAUNCHER_TEMP" "$LAUNCHER_PATH"
    sudo chmod +x "$LAUNCHER_PATH"
fi

echo "Installation complete!"
echo "You can now run 'phoque'."

#!/usr/bin/env bash
# ============================================
#  Music Suite 2-in-1 — Portable Launcher
#  Works on macOS, Linux, and WSL/Git Bash
# ============================================

set -e  # Exit on errors

# ---- Navigate to script's own directory ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  Launching Music Suite 2-in-1..."
echo "========================================"
echo ""

# ---- Detect Python ----
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        # Make sure it's Python 3
        version=$("$cmd" --version 2>&1 | grep -oP '\d+' | head -1)
        if [ "$version" = "3" ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo ""
    echo "ERROR: Python 3 is not installed or not in your PATH."
    echo ""
    echo "Install it from: https://www.python.org/downloads/"
    echo "  macOS:   brew install python3"
    echo "  Ubuntu:  sudo apt install python3 python3-pip python3-venv"
    echo "  Windows: Download from python.org and check 'Add to PATH'"
    echo ""
    read -rp "Press Enter to exit..."
    exit 1
fi

echo "Using Python: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"

# ---- Detect FFmpeg ----
if ! command -v ffmpeg &>/dev/null; then
    echo ""
    echo "WARNING: ffmpeg is not installed or not in your PATH."
    echo "  Downloading and format conversion will not work without it."
    echo ""
    echo "Install it from: https://ffmpeg.org/download.html"
    echo "  macOS:   brew install ffmpeg"
    echo "  Ubuntu:  sudo apt install ffmpeg"
    echo "  Windows: Download from https://www.gyan.dev/ffmpeg/builds/"
    echo ""
fi

# ---- Create & activate virtual environment (keeps things portable) ----
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
fi

# Activate: works on both Linux/macOS and Git Bash/WSL
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
    source "$VENV_DIR/Scripts/activate"
fi

echo "Virtual environment active: $VIRTUAL_ENV"

# ---- Install / update dependencies ----
echo "Checking dependencies..."
pip install -r requirements.txt --quiet --upgrade

# ---- Launch the app ----
echo ""
echo "Starting server and opening browser..."
echo "  → http://localhost:8000"
echo ""
python combined_app.py

# ---- Cleanup on exit ----
echo ""
echo "Server stopped."
read -rp "Press Enter to exit..."

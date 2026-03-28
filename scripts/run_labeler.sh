#!/bin/bash

# --- CONFIGURATION ---
# Get the directory where THIS script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Path to your virtual environment
VENV_PATH="$PROJECT_ROOT/.venv/bin/activate"

# Source environment variables if .env exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# --- EXECUTION ---
# Activate venv and run the labeler (labeling the last 50 unread emails)
source "$VENV_PATH"
python3 "$SCRIPT_DIR/label_inbox.py" --limit 50 --unread-only >> "$PROJECT_ROOT/labeler_log.txt" 2>&1

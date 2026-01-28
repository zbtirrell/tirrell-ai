#!/bin/bash
# Convert Markdown to Google Docs
# Usage: ./upload.sh input.md [--title "Document Title"] [--folder FOLDER_ID]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/upload.py" "$@"

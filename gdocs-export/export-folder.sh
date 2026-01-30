#!/bin/bash
# Export all Google Docs from a Drive folder to markdown
# Usage: export-folder.sh --folder <URL_OR_ID> --output <DIR>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the Python script with all arguments
python3 "$SCRIPT_DIR/export_folder.py" "$@"

#!/bin/bash
# Google Docs to Markdown Exporter
# Exports Google Documents to local markdown files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/gdoc2md.py"

show_help() {
  cat << 'EOF'
Usage: export.sh [options]

Export a Google Document to a local markdown file.

Required (one of):
  -u, --url URL         Full Google Docs URL
  -d, --doc-id ID       Google Docs document ID

Optional:
  -o, --output FILE     Output markdown file path (default: auto-generated)
  --force               Overwrite existing file without prompting
  --split-sections      Split document into separate files by major headings
  --split-tabs          Split document into separate files by tabs (one per tab)
  -h, --help            Show this help

Examples:
  export.sh --url "https://docs.google.com/document/d/DOC_ID/edit" --output "doc.md"
  export.sh --doc-id "DOC_ID" --output "doc.md"
  export.sh --url "https://docs.google.com/document/d/DOC_ID/edit"
EOF
}

# Parse arguments
DOC_URL=""
DOC_ID=""
OUTPUT_FILE=""
FORCE=false
SPLIT_SECTIONS=false
SPLIT_TABS=false

while [[ $# -gt 0 ]]; do
  case $1 in
    -u|--url)
      DOC_URL="$2"
      shift 2
      ;;
    -d|--doc-id)
      DOC_ID="$2"
      shift 2
      ;;
    -o|--output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    --force)
      FORCE=true
      shift
      ;;
    --split-sections)
      SPLIT_SECTIONS=true
      shift
      ;;
    --split-tabs)
      SPLIT_TABS=true
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      show_help
      exit 1
      ;;
  esac
done

# Extract document ID from URL if provided
if [[ -n "$DOC_URL" ]]; then
  # Extract ID from various Google Docs URL formats
  if [[ "$DOC_URL" =~ /document/d/([a-zA-Z0-9_-]+) ]]; then
    DOC_ID="${BASH_REMATCH[1]}"
  else
    echo "Error: Could not extract document ID from URL: $DOC_URL" >&2
    exit 1
  fi
fi

# Validate document ID
if [[ -z "$DOC_ID" ]]; then
  echo "Error: Document ID or URL required" >&2
  show_help
  exit 1
fi

# Check if Python script exists
if [[ ! -f "$PYTHON_SCRIPT" ]]; then
  echo "Error: Python script not found: $PYTHON_SCRIPT" >&2
  exit 1
fi

# Check if output file exists and prompt for confirmation
if [[ -n "$OUTPUT_FILE" && -f "$OUTPUT_FILE" && "$FORCE" != "true" ]]; then
  read -p "File $OUTPUT_FILE already exists. Overwrite? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
  fi
fi

# Run Python script
CMD_ARGS=(
  --doc-id "$DOC_ID"
)

if [[ -n "$OUTPUT_FILE" ]]; then
  CMD_ARGS+=(--output "$OUTPUT_FILE")
fi

if [[ "$FORCE" == "true" ]]; then
  CMD_ARGS+=(--force)
fi

if [[ "$SPLIT_SECTIONS" == "true" ]]; then
  CMD_ARGS+=(--split-sections)
fi

if [[ "$SPLIT_TABS" == "true" ]]; then
  CMD_ARGS+=(--split-tabs)
fi

python3 "$PYTHON_SCRIPT" "${CMD_ARGS[@]}"


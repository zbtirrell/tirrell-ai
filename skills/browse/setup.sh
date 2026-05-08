#!/bin/bash
# First-time setup for the z:browse skill.
# Installs Bun deps + downloads Playwright Chromium.
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if ! command -v bun >/dev/null 2>&1; then
  echo "Bun not found. Install with: curl -fsSL https://bun.sh/install | bash"
  exit 1
fi

echo "Installing Bun deps..."
bun install

echo "Installing Playwright Chromium..."
bunx playwright install chromium

echo "Done. Test with: $DIR/browse goto https://example.com"

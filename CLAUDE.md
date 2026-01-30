# tirrell-ai

Skills library for Claude Code: Google Docs integration, document workflows, and productivity tools.

## Plugin Alias: z

Install with `/plugin install z` after adding from marketplace.

## Skills

### gdocs-upload

Convert markdown files to Google Docs with rich formatting.

**Invocation:** `/gdocs-upload` or ask Claude to "upload markdown to Google Docs"

**What It Does:**
- Converts markdown files to Google Docs format
- Uploads to Google Drive with automatic conversion
- Preserves document URLs on re-upload (in-place updates)
- Applies custom styling: Proxima Nova headings, table borders, header rows

**Example Prompts:**
- "Upload my-document.md to Google Docs"
- "Convert the README to a Google Doc"
- "Sync strategy.md with Google Docs"

**Files:** `gdocs-upload/`

---

### gdocs-export

Export Google Documents to local markdown files.

**Invocation:** `/gdocs-export` or ask Claude to "download Google Doc as markdown"

**What It Does:**
- Exports Google Docs to markdown format
- Supports single doc or entire folder export
- Can split documents by sections (H1/H2)
- Preserves formatting, headings, lists, tables, links

**Example Prompts:**
- "Export this Google Doc to markdown: [url]"
- "Download the strategy doc as markdown"
- "Export all docs in this Drive folder"

**Files:** `gdocs-export/`

---

## Prerequisites

Both skills require:
1. Google API credentials configured (`GOOGLE_CLIENT_SECRET_FILE` environment variable)
2. Python dependencies (`google-api-python-client`, `google-auth`, etc.)

gdocs-upload also requires:
- Pandoc installed (`brew install pandoc`)

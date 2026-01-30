# tirrell-ai

Skills library for Claude Code: Google Docs integration, document workflows, and productivity tools.

## Plugin Alias: z

Install with `/plugin install z` after adding from marketplace.

## Skills

### gdocs

Convert markdown files to Google Docs with rich formatting.

**Invocation:** `/gdocs` or ask Claude to "upload markdown to Google Docs"

**What It Does:**
- Converts markdown files to Google Docs format
- Uploads to Google Drive with automatic conversion
- Preserves document URLs on re-upload (in-place updates)
- Applies custom styling: Proxima Nova headings, table borders, header rows

**Example Prompts:**
- "Upload my-document.md to Google Docs"
- "Convert the README to a Google Doc"
- "Sync strategy.md with Google Docs"
- "Update the Google Doc for notes.md"

**Prerequisites:**
1. Pandoc installed (`brew install pandoc`)
2. Google API credentials configured (`GOOGLE_CLIENT_SECRET_FILE` environment variable)
3. Python dependencies (`google-api-python-client`, `google-auth`, etc.)

**Files:**
- `upload.sh` - Shell wrapper script
- `upload.py` - Main Python implementation
- `reference-template.docx` - Default styling template
- `SKILL.md` - Skill documentation and frontmatter

---
name: gdocs
description: Convert markdown files to Google Docs with rich formatting. Use when user asks to upload markdown to Google Docs, convert markdown to gdocs, or sync markdown with Google Drive. Supports in-place updates preserving URLs, text styling (bold, italic, links), tables with borders and headers, and Proxima Nova font for headings.
allowed-tools: [Bash]
---

# Markdown to Google Docs

Convert markdown files to Google Docs and upload to Google Drive with rich formatting.

## Quick Start

```bash
# Upload markdown as a new Google Doc
.claude/skills/markdown-to-google-docs/upload.sh input.md

# With custom title
.claude/skills/markdown-to-google-docs/upload.sh input.md --title "My Document"

# Upload to specific Drive folder
.claude/skills/markdown-to-google-docs/upload.sh input.md --folder "1abc123FolderId"

# Force create new doc (ignore existing ID)
.claude/skills/markdown-to-google-docs/upload.sh input.md --new
```

## Options

| Option | Description |
|--------|-------------|
| `input` | Input markdown file (required) |
| `-t, --title TITLE` | Document title (default: filename without extension) |
| `-f, --folder ID` | Google Drive folder ID to upload to |
| `--reference-doc FILE` | Word template (.docx) for custom styling |
| `--keep-docx` | Keep the intermediate .docx file |
| `--new` | Force create new doc (ignore existing ID in file) |
| `--no-save-id` | Don't save doc ID to markdown file |

## Features

- **In-place updates** - Re-running preserves the existing Google Doc URL
- **Text formatting** - Bold, italic, underline, links (including in tables)
- **Custom styling applied automatically**:
  - Proxima Nova font for headings
  - Table borders (0.5pt, dark gray)
  - Table header row: bold + light gray background
  - Vertical center alignment in table cells
  - Space after paragraphs
- **Rate limit handling** - Waits and retries without creating duplicate docs

## Prerequisites

### 1. Pandoc

```bash
brew install pandoc
```

### 2. Google API Credentials

Set the path to your OAuth client secret:

```bash
export GOOGLE_CLIENT_SECRET_FILE="/path/to/client-secret.json"
```

First run will open browser for authentication.

### 3. Python Dependencies

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

## How It Works

1. Converts markdown to `.docx` using pandoc
2. Uploads to Google Drive as a Google Doc
3. Applies custom styling via Google Docs API
4. Saves the doc ID as a comment in your markdown file:
   ```markdown
   <!-- google-doc-id: 1abc123... -->

   # Your Document
   ...
   ```
5. Future runs update the same document, preserving the URL

## Examples

### Basic Upload

```bash
.claude/skills/markdown-to-google-docs/upload.sh notes.md
# Output: https://docs.google.com/document/d/xxx/edit
```

### Custom Title

```bash
.claude/skills/markdown-to-google-docs/upload.sh slack-post.txt --title "TikTok Strategy Update"
```

### With Custom Styling

Create a reference Word doc with your preferred styles, then:

```bash
.claude/skills/markdown-to-google-docs/upload.sh report.md --reference-doc template.docx
```

## Formatting Notes

The conversion uses pandoc which handles:
- Headings (H1-H6)
- Bold, italic, strikethrough
- Bullet and numbered lists
- Code blocks (monospace font)
- Tables (basic support)
- Links

**Known limitations:**
- Complex tables may not render perfectly
- Code block syntax highlighting is lost
- Some markdown extensions may not convert

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "pandoc: command not found" | Install pandoc: `brew install pandoc` |
| "GOOGLE_CLIENT_SECRET_FILE not set" | Set the environment variable with path to your OAuth credentials |
| "Permission denied" | Re-authenticate by deleting `~/.google-drive-upload-token.json` and running again |
| Tables look wrong | Try simplifying table structure or use `--reference-doc` with custom table styles |
| Rate limit errors | Wait 60 seconds and retry |

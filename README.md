# Markdown to Google Docs

Convert markdown files to Google Docs with rich formatting, preserving styles and links.

## Features

- **In-place updates** - Re-running on the same markdown file updates the existing Google Doc, preserving the URL
- **Text formatting** - Bold, italic, underline, strikethrough, links (including in tables)
- **Custom styling applied automatically**:
  - Proxima Nova font for headings
  - Table borders (0.5pt, dark gray)
  - Table header row: bold text + light gray background
  - Vertical center alignment in table cells
  - 11pt font in tables
  - Space after paragraphs
- **Rate limit handling** - Automatically waits and retries without creating duplicate docs

## Quick Start

```bash
# Upload markdown as a new Google Doc
./upload.sh document.md

# Update an existing doc (if markdown contains google-doc-id comment)
./upload.sh document.md

# Force create new doc (ignore existing ID)
./upload.sh document.md --new
```

## Installation

### Prerequisites

1. **Pandoc**
   ```bash
   brew install pandoc
   ```

2. **Python dependencies**
   ```bash
   pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
   ```

3. **Google API credentials**

   Set up OAuth credentials in Google Cloud Console and export the path:
   ```bash
   export GOOGLE_CLIENT_SECRET_FILE="/path/to/client-secret.json"
   ```

   First run will open browser for authentication.

## Usage

```bash
./upload.sh <input.md> [options]
```

### Options

| Option | Description |
|--------|-------------|
| `-t, --title TITLE` | Document title (default: filename) |
| `-f, --folder ID` | Google Drive folder ID to upload to |
| `--reference-doc FILE` | Word template for base styling |
| `--keep-docx` | Keep intermediate .docx file |
| `--new` | Force create new doc (ignore existing ID) |
| `--no-save-id` | Don't save doc ID to markdown file |

### Examples

```bash
# Basic upload
./upload.sh notes.md

# Custom title
./upload.sh report.md --title "Q1 Report"

# Upload to specific folder
./upload.sh doc.md --folder "1abc123FolderId"

# Keep the intermediate Word file
./upload.sh doc.md --keep-docx
```

## How It Works

1. **Converts** markdown to .docx using pandoc
2. **Uploads** to Google Drive with conversion to Google Docs format
3. **Applies styling** via Google Docs API (headings, tables, spacing)
4. **Saves doc ID** as HTML comment in markdown for future updates:
   ```markdown
   <!-- google-doc-id: 1abc123... -->

   # Your Document
   ...
   ```

## URL Preservation

When you run the script on a markdown file that already has a `google-doc-id` comment, it updates the existing document in place rather than creating a new one. This preserves:

- The document URL (for sharing links)
- The document's location in Drive
- Sharing permissions

If an update fails (e.g., rate limit), the script exits with an error and preserves the original document rather than creating a duplicate.

## Formatting Support

| Markdown | Result |
|----------|--------|
| `**bold**` | **bold** |
| `*italic*` | *italic* |
| `[link](url)` | Clickable link |
| `# Heading` | Styled heading (Proxima Nova) |
| Tables | Bordered with header styling |
| Lists | Bulleted/numbered with spacing |
| Code blocks | Monospace font |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "pandoc: command not found" | `brew install pandoc` |
| "GOOGLE_CLIENT_SECRET_FILE not set" | Export path to OAuth credentials |
| Rate limit errors | Wait 60 seconds and retry |
| Links in tables wrong | Update to latest version (re-fetches indices) |
| Wrong font in tables | 11pt is applied automatically to prevent inheritance |

## License

MIT

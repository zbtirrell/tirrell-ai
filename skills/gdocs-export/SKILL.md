---
name: gdocs-export
description: Export Google Documents to local markdown files, keeping them in sync with the source document. Supports single doc export, batch folder export, and splitting by sections.
allowed-tools: [Bash]
---

# Google Docs to Markdown

Export Google Documents to local markdown files, keeping them in sync with the source document.

## Quick Start

```bash
# Export a Google Doc to markdown
./export.sh \
  --url "https://docs.google.com/document/d/1T8aa0gc4bZQ7h3p5rna0bD1owue_JI4sU7ahvBZb6Ew/edit" \
  --output "analysis.md"

# Export with auto-detected filename from document title
./export.sh \
  --url "https://docs.google.com/document/d/1T8aa0gc4bZQ7h3p5rna0bD1owue_JI4sU7ahvBZb6Ew/edit"

# Export using just the document ID
./export.sh \
  --doc-id "1T8aa0gc4bZQ7h3p5rna0bD1owue_JI4sU7ahvBZb6Ew" \
  --output "analysis.md"

# Export ALL Google Docs from a Drive folder
./export-folder.sh \
  --folder "https://drive.google.com/drive/folders/1f7-IxJdicZV5JoO_BiaTWUERUr5YK4ki" \
  --output "./strategy/2026q1-rocks"
```

## Script Reference

### Single Document Export

**Location:** `./export.sh`

| Option | Description |
|--------|-------------|
| `-u, --url URL` | Full Google Docs URL (required if --doc-id not provided) |
| `-d, --doc-id ID` | Google Docs document ID (required if --url not provided) |
| `-o, --output FILE` | Output markdown file path (default: auto-generated from doc title) |
| `--force` | Overwrite existing file without prompting |
| `--split-sections` | Split document into separate files by major headings (H1/H2) |
| `-h, --help` | Show help |

### Folder Export (Batch)

**Location:** `./export-folder.sh`

| Option | Description |
|--------|-------------|
| `--folder URL_OR_ID` | Google Drive folder URL or folder ID (required) |
| `--output DIR` | Output directory for markdown files (required) |
| `--force` | Overwrite existing files without prompting |
| `--list-only` | Only list documents in the folder, do not export |

**Note:** First run will prompt for additional Google Drive permissions (drive.readonly scope) to list folder contents. This creates a separate token file (`~/.google-drive-token.json`).

## Prerequisites

### Google API Credentials

This skill requires Google API credentials to access Google Docs.

**See [SETUP.md](SETUP.md) for detailed step-by-step instructions.**

Quick summary:
1. Create a Google Cloud project and enable Google Docs API
2. Create OAuth 2.0 credentials (Desktop app type)
3. Download the client secret JSON file
4. Set the environment variable:
   ```bash
   export GOOGLE_CLIENT_SECRET_FILE="/path/to/client-secret.json"
   ```
5. First run will open browser for authentication (creates token file)

**Note:** This uses your personal Google account, so you can access any documents you have permission to view.

### Python Dependencies

The skill requires Python 3.7+ and the following packages:

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

Or install via the skill's requirements file:

```bash
pip install -r ./requirements.txt
```

## Examples

### Export Specific Document

```bash
./export.sh \
  --url "https://docs.google.com/document/d/1T8aa0gc4bZQ7h3p5rna0bD1owue_JI4sU7ahvBZb6Ew/edit" \
  --output "smash-balloon-analysis.md"
```

### Auto-detect Output Filename

```bash
# Output will be based on document title (e.g., "Smash Balloon Analysis.md")
./export.sh \
  --doc-id "1T8aa0gc4bZQ7h3p5rna0bD1owue_JI4sU7ahvBZb6Ew"
```

### Force Overwrite

```bash
./export.sh \
  --url "https://docs.google.com/document/d/1T8aa0gc4bZQ7h3p5rna0bD1owue_JI4sU7ahvBZb6Ew/edit" \
  --output "analysis.md" \
  --force
```

### Split by Sections

Export each major section (H1/H2 headings) to separate files:

```bash
./export.sh \
  --doc-id "1T8aa0gc4bZQ7h3p5rna0bD1owue_JI4sU7ahvBZb6Ew" \
  --output "smash-balloon-analysis" \
  --split-sections
```

This will create files like:
- `product-overview.md`
- `swot.md`
- `strategic-recommendations.md`
- etc.

### Export Entire Folder

```bash
./export-folder.sh \
  --folder "https://drive.google.com/drive/folders/1f7-IxJdicZV5JoO_BiaTWUERUr5YK4ki" \
  --output "./docs"
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_SECRET_FILE` | Path to OAuth client secret JSON file (required) |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Permission denied" | Re-authenticate by deleting token file and running again |
| "Module not found" | Install Python dependencies: `pip install -r requirements.txt` |
| "No valid credentials found" | Set `GOOGLE_CLIENT_SECRET_FILE` environment variable |
| "Document not found" | Verify the document ID is correct and the document is accessible |

## How It Works

The skill uses the Google Docs API to:
1. Authenticate using service account or OAuth credentials
2. Fetch the document content via the API
3. Convert the document structure to markdown format
4. Preserve formatting, headings, lists, tables, and links
5. Save to the local file system

This approach provides better markdown conversion than HTML export + pandoc, as it has direct access to the document structure.

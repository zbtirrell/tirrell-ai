# Markdown to Google Docs

**name:** markdown-to-google-docs

**description:** "Convert markdown files to Google Docs and upload to Google Drive."

## Quick Start

```bash
# Upload markdown as a new Google Doc
.claude/skills/markdown-to-google-docs/upload.sh input.md

# With custom title
.claude/skills/markdown-to-google-docs/upload.sh input.md --title "My Document"

# Upload to specific Drive folder
.claude/skills/markdown-to-google-docs/upload.sh input.md --folder "1abc123FolderId"
```

## Options

| Option | Description |
|--------|-------------|
| `input` | Input markdown file (required) |
| `-t, --title TITLE` | Document title (default: filename without extension) |
| `-f, --folder ID` | Google Drive folder ID to upload to |
| `--reference-doc FILE` | Word template (.docx) for custom styling |
| `--keep-docx` | Keep the intermediate .docx file |

## Prerequisites

### 1. Pandoc

```bash
brew install pandoc
```

### 2. Google API Credentials

Uses the same OAuth credentials as `google-docs-to-markdown`. Set:

```bash
export GOOGLE_CLIENT_SECRET_FILE="/path/to/client-secret.json"
```

First run will open browser for authentication.

### 3. Python Dependencies

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

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
| "Permission denied" | Re-authenticate by deleting `~/.google-docs-token.json` and running again |
| Tables look wrong | Try simplifying table structure or use `--reference-doc` with custom table styles |

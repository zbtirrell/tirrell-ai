# tirrell-ai

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills library with Google Docs integration, document workflows, and productivity tools.

## Skills Included

| Skill | Description |
|-------|-------------|
| `gdocs-upload` | Convert markdown to Google Docs with rich formatting |
| `gdocs-export` | Export Google Docs to markdown (single doc or folder) |

## Installation

### Option 1: Plugin Marketplace (Recommended)

```bash
# Add from marketplace
/plugin marketplace add zbtirrell/tirrell-ai

# Install the plugin (alias: z)
/plugin install z
```

### Option 2: Local Installation

```bash
# Clone to your plugins directory
mkdir -p ~/.claude/plugins
cd ~/.claude/plugins
git clone https://github.com/zbtirrell/tirrell-ai.git

# Register and install
/plugin add ~/.claude/plugins/tirrell-ai
/plugin install z
```

### Option 3: As Skills (Legacy)

```bash
# Global installation
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/zbtirrell/tirrell-ai.git
```

## Enabling Specific Skills

After installing the plugin, you can enable individual skills:

```bash
# Enable only gdocs-upload
/skill enable z:gdocs-upload

# Enable only gdocs-export
/skill enable z:gdocs-export

# Enable all skills from the plugin
/skill enable z:*
```

To see available skills:

```bash
/skill list
```

## Prerequisites

### Google API Credentials (Required for all skills)

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the **Google Drive API** and **Google Docs API**
3. Create OAuth 2.0 credentials (Desktop application)
4. Download the client secret JSON file
5. Export the path:

```bash
export GOOGLE_CLIENT_SECRET_FILE="/path/to/client-secret.json"
```

### Python Dependencies

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

### Pandoc (for gdocs-upload only)

```bash
brew install pandoc
```

---

## gdocs-upload Skill

Convert markdown files to Google Docs with rich formatting, preserving styles and links.

### Features

- **In-place updates** - Re-running preserves the existing Google Doc URL
- **Text formatting** - Bold, italic, underline, links (including in tables)
- **Custom styling applied automatically**:
  - Proxima Nova font for headings
  - Table borders (0.5pt, dark gray)
  - Table header row: bold + light gray background
  - Vertical center alignment in table cells
  - Space after paragraphs
- **Rate limit handling** - Waits and retries without creating duplicate docs

### Usage

Ask Claude to convert your markdown:

> "Upload my-document.md to Google Docs"

> "Convert the project README to a Google Doc"

> "Update the Google Doc for strategy.md"

Or use the slash command:

> `/gdocs-upload my-document.md`

### What happens

1. Claude converts your markdown to a Google Doc
2. The doc ID is saved as a comment in your markdown file:
   ```markdown
   <!-- google-doc-id: 1abc123... -->

   # Your Document
   ...
   ```
3. Future updates preserve the same URL

### CLI Usage

```bash
# Upload markdown as a new Google Doc
~/.claude/skills/tirrell-ai/gdocs-upload/upload.sh document.md

# With custom title
~/.claude/skills/tirrell-ai/gdocs-upload/upload.sh document.md --title "My Document"

# Upload to specific Drive folder
~/.claude/skills/tirrell-ai/gdocs-upload/upload.sh document.md --folder "1abc123FolderId"

# Force create new doc (ignore existing ID)
~/.claude/skills/tirrell-ai/gdocs-upload/upload.sh document.md --new
```

### Options

| Option | Description |
|--------|-------------|
| `-t, --title TITLE` | Document title (default: filename) |
| `-f, --folder ID` | Google Drive folder ID |
| `--reference-doc FILE` | Word template for base styling |
| `--keep-docx` | Keep intermediate .docx file |
| `--new` | Force create new doc |
| `--no-save-id` | Don't save doc ID to markdown |

---

## gdocs-export Skill

Export Google Documents to local markdown files, keeping them in sync with the source document.

### Features

- **Single doc export** - Export any Google Doc by URL or ID
- **Folder export** - Batch export all docs from a Drive folder
- **Split by sections** - Split document into separate files by H1/H2 headings
- **Preserves formatting** - Headings, lists, tables, links

### Usage

Ask Claude to export a Google Doc:

> "Export this Google Doc to markdown: https://docs.google.com/document/d/xxx/edit"

> "Download the strategy doc as markdown"

> "Export all docs in this Drive folder to ./docs"

Or use the slash command:

> `/gdocs-export --url "https://docs.google.com/document/d/xxx/edit"`

### CLI Usage

```bash
# Export a single doc
~/.claude/skills/tirrell-ai/gdocs-export/export.sh \
  --url "https://docs.google.com/document/d/DOC_ID/edit" \
  --output "document.md"

# Export with auto-detected filename
~/.claude/skills/tirrell-ai/gdocs-export/export.sh \
  --doc-id "DOC_ID"

# Split by sections
~/.claude/skills/tirrell-ai/gdocs-export/export.sh \
  --doc-id "DOC_ID" \
  --split-sections

# Export all docs from a folder
~/.claude/skills/tirrell-ai/gdocs-export/export-folder.sh \
  --folder "https://drive.google.com/drive/folders/FOLDER_ID" \
  --output "./docs"
```

### Single Doc Options

| Option | Description |
|--------|-------------|
| `-u, --url URL` | Full Google Docs URL |
| `-d, --doc-id ID` | Google Docs document ID |
| `-o, --output FILE` | Output markdown file path |
| `--force` | Overwrite existing file |
| `--split-sections` | Split by H1/H2 headings |

### Folder Export Options

| Option | Description |
|--------|-------------|
| `--folder URL_OR_ID` | Google Drive folder URL or ID |
| `--output DIR` | Output directory |
| `--force` | Overwrite existing files |
| `--list-only` | List docs without exporting |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "pandoc: command not found" | `brew install pandoc` |
| "GOOGLE_CLIENT_SECRET_FILE not set" | Export path to OAuth credentials |
| Rate limit errors | Wait 60 seconds and retry |
| Authentication errors | Delete token file and retry |

**Token file locations:**
- Upload: `~/.google-drive-upload-token.json`
- Export (docs): `~/.google-docs-token.json`
- Export (folders): `~/.google-drive-token.json`

---

## License

MIT

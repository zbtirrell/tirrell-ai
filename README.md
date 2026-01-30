# tirrell-ai

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skills library with Google Docs integration, document workflows, and productivity tools.

## Skills Included

| Skill | Description |
|-------|-------------|
| `gdocs` | Convert markdown to Google Docs with rich formatting |

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

## Prerequisites

### For gdocs skill

**1. Pandoc (for markdown conversion)**

```bash
brew install pandoc
```

**2. Python Dependencies**

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

**3. Google API Credentials**

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the **Google Drive API** and **Google Docs API**
3. Create OAuth 2.0 credentials (Desktop application)
4. Download the client secret JSON file
5. Export the path:

```bash
export GOOGLE_CLIENT_SECRET_FILE="/path/to/client-secret.json"
```

---

## gdocs Skill

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

> `/gdocs my-document.md`

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
./upload.sh document.md

# With custom title
./upload.sh document.md --title "My Document"

# Upload to specific Drive folder
./upload.sh document.md --folder "1abc123FolderId"

# Force create new doc (ignore existing ID)
./upload.sh document.md --new
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

### Formatting Support

| Markdown | Result |
|----------|--------|
| `**bold**` | **bold** |
| `*italic*` | *italic* |
| `[link](url)` | Clickable link |
| `# Heading` | Styled heading (Proxima Nova) |
| Tables | Bordered with header styling |
| Lists | Bulleted/numbered with spacing |
| Code blocks | Monospace font |

### Customizing Styles

Edit the `apply_document_styles()` function in `upload.py`:

```python
# Heading font
heading_font = 'Proxima Nova'  # Change to your preferred font

# Table border color (#b7b7b7 = dark gray 1)
'red': 0.718, 'green': 0.718, 'blue': 0.718

# Header background (#f3f3f3)
'red': 0.953, 'green': 0.953, 'blue': 0.953

# Space after paragraphs
'magnitude': 6, 'unit': 'PT'
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "pandoc: command not found" | `brew install pandoc` |
| "GOOGLE_CLIENT_SECRET_FILE not set" | Export path to OAuth credentials |
| Rate limit errors | Wait 60 seconds and retry |
| Authentication errors | Delete `~/.google-drive-upload-token.json` and retry |

---

## License

MIT

---
description: Export Google Documents to local markdown files
---

You are helping the user export Google Docs to local markdown files.

## Process

1. **Get the document source**
   - Ask the user for one of:
     - A Google Docs URL
     - A Google Drive folder URL (for batch export)
   - Use the AskUserQuestion tool if not provided

2. **Determine output location**
   - Ask where to save the markdown file(s)
   - Default: current directory with auto-generated filename from doc title

3. **Check for split option** (single doc only)
   - For long documents, ask if they want to split by sections (H1/H2 headings)
   - This creates separate files for each major section

4. **Invoke the gdocs-export skill**
   - Use the Skill tool to invoke `z:gdocs-export`
   - Command: `Skill(skill: "z:gdocs-export")`

## Important Notes

- First run will prompt for Google authentication in the browser
- Requires `GOOGLE_CLIENT_SECRET_FILE` environment variable set
- Folder export requires additional Drive permissions (prompted on first use)
- Output preserves formatting, headings, lists, tables, and links

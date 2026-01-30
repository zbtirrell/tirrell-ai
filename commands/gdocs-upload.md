---
description: Convert markdown files to Google Docs with rich formatting
---

You are helping the user upload a markdown file to Google Docs.

## Process

1. **Get the markdown file**
   - Ask the user which markdown file to upload
   - Use the AskUserQuestion tool if not provided

2. **Determine options**
   - Ask for optional custom title (default: filename without extension)
   - Ask if they want to upload to a specific Google Drive folder

3. **Check for existing doc ID**
   - If the markdown file contains `<!-- google-doc-id: ... -->`, inform the user it will update the existing doc
   - If they want a new doc instead, note they can use `--new` flag

4. **Invoke the gdocs-upload skill**
   - Use the Skill tool to invoke `z:gdocs-upload`
   - Command: `Skill(skill: "z:gdocs-upload")`

## Important Notes

- Requires pandoc installed (`brew install pandoc`)
- Requires `GOOGLE_CLIENT_SECRET_FILE` environment variable set
- First run will prompt for Google authentication in the browser
- Re-uploading preserves the Google Doc URL (in-place update)
- The doc ID is saved as a comment in the markdown file for future syncs

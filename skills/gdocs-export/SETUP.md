# Google API Credentials Setup Guide

This guide walks you through setting up Google API credentials using OAuth 2.0.

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top
3. Click **"New Project"**
4. Enter a project name (e.g., "Google Docs Tools")
5. Click **"Create"**
6. Wait for the project to be created and select it

## Step 2: Enable the Required APIs

1. In the Google Cloud Console, go to **"APIs & Services"** > **"Library"**
2. Search for **"Google Docs API"** and click **"Enable"**
3. Search for **"Google Drive API"** and click **"Enable"**

## Step 3: Configure OAuth Consent Screen

1. Go to **"APIs & Services"** > **"OAuth consent screen"**
2. Choose **"Internal"** (if you have Google Workspace) or **"External"**
3. Fill in the required fields:
   - **App name**: Google Docs Tools (or any name)
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Click **"Save and Continue"**
5. On the Scopes page, click **"Add or Remove Scopes"**
6. Add these scopes:
   - `https://www.googleapis.com/auth/documents.readonly`
   - `https://www.googleapis.com/auth/drive.readonly`
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/documents`
7. Click **"Save and Continue"**
8. If using External, add your email as a test user
9. Click **"Save and Continue"**

## Step 4: Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** > **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** at the top
3. Select **"OAuth client ID"**
4. Select **"Desktop app"** as the application type
5. Give it a name (e.g., "Google Docs Tools")
6. Click **"Create"**
7. Click **"Download JSON"** to save the client secret file
8. Save this file securely (e.g., `~/.config/google/client-secret.json`)

## Step 5: Configure Environment Variable

Set the environment variable to point to your OAuth client secret file:

```bash
export GOOGLE_CLIENT_SECRET_FILE="$HOME/.config/google/client-secret.json"
```

To make this permanent, add it to your shell profile:

```bash
# For zsh (default on macOS)
echo 'export GOOGLE_CLIENT_SECRET_FILE="$HOME/.config/google/client-secret.json"' >> ~/.zshrc
source ~/.zshrc
```

## Step 6: First-Time Authentication

The first time you run a skill, it will:
1. Open your browser
2. Ask you to sign in with your Google account
3. Request permission to access your Google Docs/Drive
4. Save a token file for future use

After this, you won't need to authenticate again unless the token expires.

## Step 7: Test the Setup

Try exporting a document:

```bash
./export.sh \
  --url "https://docs.google.com/document/d/YOUR_DOC_ID/edit" \
  --output "test-export.md"
```

Or uploading a markdown file:

```bash
../gdocs-upload/upload.sh test.md
```

## Security Best Practices

1. **Keep the client secret file secure** - Don't commit it to git repositories
2. **Use a dedicated project** - Create a separate Google Cloud project for this purpose
3. **Store credentials securely** - Consider using a secure location like `~/.config/google/`

## Troubleshooting

### "No valid credentials found" error
- Verify `GOOGLE_CLIENT_SECRET_FILE` environment variable is set
- Check that the file path is correct

### "API not enabled" error
- Go to Google Cloud Console > APIs & Services > Library
- Ensure both Google Docs API and Google Drive API are enabled

### "Permission denied" error
- Delete the token file and re-authenticate:
  - `~/.google-docs-token.json` (for single doc export)
  - `~/.google-drive-token.json` (for folder export)
  - `~/.google-drive-upload-token.json` (for upload)

### "Document not found" error
- Verify the document ID is correct
- Ensure you have access to the document with your Google account

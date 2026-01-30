#!/usr/bin/env python3
"""
Google Drive Folder to Markdown Exporter
Lists all Google Docs in a folder and exports them to markdown.
"""

import argparse
import os
import re
import sys
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"Error: Missing required package. Install with: pip install -r requirements.txt", file=sys.stderr)
    print(f"Missing: {e.name}", file=sys.stderr)
    sys.exit(1)

# Import the document conversion function from gdoc2md
from gdoc2md import convert_document_to_markdown, sanitize_filename

# Scopes required - need Drive readonly to list folder contents
SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
]

# OAuth token file location - use a separate token file since we need additional scopes
TOKEN_FILE = os.path.expanduser('~/.google-drive-token.json')


def get_credentials():
    """Get valid user credentials from storage or OAuth flow."""
    creds = None

    # Try OAuth token file
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_secret_file = os.environ.get('GOOGLE_CLIENT_SECRET_FILE')
            if not client_secret_file or not os.path.exists(client_secret_file):
                print("Error: No valid credentials found.", file=sys.stderr)
                print("Set GOOGLE_CLIENT_SECRET_FILE environment variable.", file=sys.stderr)
                sys.exit(1)

            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return creds


def extract_folder_id(url_or_id: str) -> str:
    """Extract folder ID from a Google Drive URL or return the ID if already extracted."""
    # Pattern for folder URLs
    folder_pattern = r'folders/([a-zA-Z0-9_-]+)'
    match = re.search(folder_pattern, url_or_id)
    if match:
        return match.group(1)
    # Assume it's already a folder ID
    return url_or_id


def list_google_docs_in_folder(drive_service, folder_id: str) -> list:
    """List all Google Docs in a folder (supports shared drives)."""
    docs = []
    page_token = None

    # Query for Google Docs in the specified folder
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"

    while True:
        try:
            results = drive_service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, modifiedTime)',
                pageToken=page_token,
                orderBy='name',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()

            docs.extend(results.get('files', []))
            page_token = results.get('nextPageToken')

            if not page_token:
                break

        except HttpError as e:
            if e.resp.status == 404:
                print(f"Error: Folder not found. Check the folder ID.", file=sys.stderr)
            elif e.resp.status == 403:
                print(f"Error: Permission denied. Make sure you have access to the folder.", file=sys.stderr)
            else:
                print(f"Error listing folder: {e}", file=sys.stderr)
            sys.exit(1)

    return docs


def export_doc_to_markdown(docs_service, doc_id: str, doc_name: str, output_dir: Path, force: bool = False) -> bool:
    """Export a single Google Doc to markdown."""
    output_file = output_dir / sanitize_filename(doc_name)

    # Check if file exists
    if output_file.exists() and not force:
        print(f"  Skipping '{doc_name}' - file exists. Use --force to overwrite.", file=sys.stderr)
        return False

    try:
        # Get document with tabs content
        doc = docs_service.documents().get(
            documentId=doc_id,
            includeTabsContent=True
        ).execute()

        # Convert to markdown
        sections = convert_document_to_markdown(doc)
        _, markdown = sections[0]

        # Write to file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown)

        print(f"  Exported: {doc_name} -> {output_file.name}", file=sys.stderr)
        return True

    except HttpError as e:
        if e.resp.status == 404:
            print(f"  Error: Document '{doc_name}' not found.", file=sys.stderr)
        elif e.resp.status == 403:
            print(f"  Error: Permission denied for '{doc_name}'.", file=sys.stderr)
        else:
            print(f"  Error exporting '{doc_name}': {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  Error exporting '{doc_name}': {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Export all Google Docs from a Drive folder to markdown'
    )
    parser.add_argument(
        '--folder',
        required=True,
        help='Google Drive folder URL or ID'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for markdown files'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing files without prompting'
    )
    parser.add_argument(
        '--list-only',
        action='store_true',
        help='Only list the documents, do not export'
    )

    args = parser.parse_args()

    # Extract folder ID
    folder_id = extract_folder_id(args.folder)

    # Get credentials
    try:
        creds = get_credentials()
    except Exception as e:
        print(f"Error getting credentials: {e}", file=sys.stderr)
        sys.exit(1)

    # Build services
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        docs_service = build('docs', 'v1', credentials=creds)
    except Exception as e:
        print(f"Error building service: {e}", file=sys.stderr)
        sys.exit(1)

    # List documents in folder
    print(f"Scanning folder...", file=sys.stderr)
    docs = list_google_docs_in_folder(drive_service, folder_id)

    if not docs:
        print("No Google Docs found in the folder.", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(docs)} Google Doc(s):", file=sys.stderr)
    for doc in docs:
        print(f"  - {doc['name']}", file=sys.stderr)

    if args.list_only:
        sys.exit(0)

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export each document
    print(f"\nExporting to: {output_dir.absolute()}", file=sys.stderr)

    success_count = 0
    for doc in docs:
        if export_doc_to_markdown(docs_service, doc['id'], doc['name'], output_dir, args.force):
            success_count += 1

    print(f"\nExported {success_count}/{len(docs)} document(s).", file=sys.stderr)


if __name__ == '__main__':
    main()

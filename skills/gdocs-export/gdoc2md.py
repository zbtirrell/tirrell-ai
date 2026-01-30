#!/usr/bin/env python3
"""
Google Docs to Markdown Converter
Exports Google Documents to markdown format using the Google Docs API.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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

# Scopes required for Google Docs API
SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
]

# OAuth token file location
TOKEN_FILE = os.path.expanduser('~/.google-docs-token.json')


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


def extract_text_runs(element: Dict) -> str:
    """Extract text from a text run element."""
    if 'textRun' in element:
        return element['textRun'].get('content', '')
    return ''


def get_text_style(element: Dict) -> Dict:
    """Get text style from an element."""
    if 'textRun' in element and 'textStyle' in element['textRun']:
        return element['textRun']['textStyle']
    return {}


def is_bold(style: Dict) -> bool:
    """Check if text is bold."""
    return style.get('bold', False)


def is_italic(style: Dict) -> bool:
    """Check if text is italic."""
    return style.get('italic', False)


def is_underline(style: Dict) -> bool:
    """Check if text is underlined."""
    return style.get('underline', False)


def get_link(style: Dict) -> Optional[str]:
    """Get link URL from text style."""
    if 'link' in style:
        return style['link'].get('url')
    return None


def convert_paragraph_to_markdown(paragraph: Dict, level: int = 0) -> str:
    """Convert a paragraph element to markdown."""
    result = []
    
    if 'paragraph' not in paragraph:
        return ''
    
    para = paragraph['paragraph']
    para_style = para.get('paragraphStyle', {})
    named_style = para_style.get('namedStyleType', 'NORMAL_TEXT')
    
    # Extract text from elements
    text_parts = []
    for element in para.get('elements', []):
        text = extract_text_runs(element)
        if not text:
            continue
        
        style = get_text_style(element)
        link = get_link(style)
        
        # Apply formatting (order matters: bold/italic before links)
        formatted_text = text
        if is_bold(style) and is_italic(style):
            formatted_text = f"***{formatted_text}***"
        elif is_bold(style):
            formatted_text = f"**{formatted_text}**"
        elif is_italic(style):
            formatted_text = f"*{formatted_text}*"
        
        if is_underline(style):
            formatted_text = f"<u>{formatted_text}</u>"
        
        # Links should wrap the formatted text
        if link:
            formatted_text = f"[{formatted_text}]({link})"
        
        text_parts.append(formatted_text)
    
    text = ''.join(text_parts).rstrip()
    
    # Handle different paragraph styles
    if named_style.startswith('HEADING_'):
        level_map = {
            'HEADING_1': 1,
            'HEADING_2': 2,
            'HEADING_3': 3,
            'HEADING_4': 4,
            'HEADING_5': 5,
            'HEADING_6': 6,
        }
        heading_level = level_map.get(named_style, 1)
        return f"{'#' * heading_level} {text}\n"
    elif para.get('bullet'):
        bullet = para['bullet']
        list_id = bullet.get('listId')
        nesting_level = bullet.get('nestingLevel', 0)
        indent = '  ' * nesting_level
        marker = '- ' if nesting_level == 0 else '  - '
        return f"{indent}{marker}{text}\n"
    elif text.strip():
        return f"{text}\n"
    
    return '\n'


def convert_table_to_markdown(table: Dict) -> str:
    """Convert a table element to markdown."""
    result = []
    
    if 'table' not in table:
        return ''
    
    table_data = table['table']
    rows = table_data.get('tableRows', [])
    
    if not rows:
        return ''
    
    # Extract table data
    table_rows = []
    for row in rows:
        row_data = []
        for cell in row.get('tableCells', []):
            cell_text = []
            for content in cell.get('content', []):
                for element in content.get('paragraph', {}).get('elements', []):
                    text = extract_text_runs(element)
                    cell_text.append(text)
            row_data.append(' '.join(cell_text).strip())
        table_rows.append(row_data)
    
    if not table_rows:
        return ''
    
    # Generate markdown table
    if not table_rows:
        return ''
    
    num_cols = max(len(row) for row in table_rows) if table_rows else 0
    if num_cols == 0:
        return ''
    
    # Escape pipe characters in cell content
    def escape_cell(cell):
        return str(cell).replace('|', '\\|').replace('\n', ' ')
    
    # Header row
    header = table_rows[0] if table_rows else []
    while len(header) < num_cols:
        header.append('')
    result.append('| ' + ' | '.join(escape_cell(cell) for cell in header) + ' |')
    result.append('| ' + ' | '.join(['---'] * num_cols) + ' |')
    
    # Data rows
    for row in table_rows[1:]:
        # Pad row if needed
        while len(row) < num_cols:
            row.append('')
        result.append('| ' + ' | '.join(escape_cell(cell) for cell in row) + ' |')
    
    return '\n'.join(result) + '\n\n'


def get_all_tabs(doc: Dict) -> List[Tuple[str, Dict]]:
    """
    Recursively get all tabs from a document, including nested child tabs.
    Returns a list of tuples: (tab_title, tab_content_dict)
    """
    all_tabs = []
    
    # Get tabs from document
    tabs = doc.get('tabs', [])
    
    for tab in tabs:
        # Get tab title
        tab_props = tab.get('tabProperties', {})
        tab_title = tab_props.get('title', 'Untitled Tab')
        
        # Add this tab
        if 'documentTab' in tab:
            all_tabs.append((tab_title, tab['documentTab']))
        
        # Recursively get child tabs
        if 'childTabs' in tab:
            for child_tab in tab['childTabs']:
                child_props = child_tab.get('tabProperties', {})
                child_title = child_props.get('title', 'Untitled Tab')
                if 'documentTab' in child_tab:
                    all_tabs.append((child_title, child_tab['documentTab']))
                # Handle nested child tabs
                if 'childTabs' in child_tab:
                    nested_tabs = get_all_tabs({'tabs': child_tab['childTabs']})
                    all_tabs.extend(nested_tabs)
    
    return all_tabs


def convert_document_to_markdown(doc: Dict, split_by_sections: bool = False, split_by_tabs: bool = False) -> List[Tuple[str, str]]:
    """
    Convert a Google Document to markdown.
    
    Returns:
        If split_by_sections and split_by_tabs are False: List with single tuple (title, markdown)
        If split_by_sections is True: List of tuples (section_title, markdown) for each section
        If split_by_tabs is True: List of tuples (tab_title, markdown) for each tab
    """
    result = []
    
    # Get all tabs content (if document has tabs)
    all_tabs = get_all_tabs(doc)
    
    # Collect content from main body and all tabs
    all_content = []
    
    # Add main body content (if any)
    main_body = doc.get('body', {})
    main_content = main_body.get('content', [])
    if main_content:
        all_content.append(('Main Document', main_content))
    
    # Add content from each tab
    for tab_title, tab_doc in all_tabs:
        tab_body = tab_doc.get('body', {})
        tab_content = tab_body.get('content', [])
        if tab_content:
            all_content.append((tab_title, tab_content))
    
    # If no tabs and no main content, use empty content
    if not all_content:
        all_content = [('Main Document', main_body.get('content', []))]
    
    if split_by_tabs:
        # Split by tabs mode - one file per tab
        tab_sections = []
        for tab_title, content in all_content:
            markdown_parts = []
            for element in content:
                if 'paragraph' in element:
                    markdown = convert_paragraph_to_markdown(element)
                    markdown_parts.append(markdown)
                elif 'table' in element:
                    markdown = convert_table_to_markdown(element)
                    markdown_parts.append(markdown)
                elif 'sectionBreak' in element:
                    markdown_parts.append('\n---\n\n')
            
            tab_markdown = ''.join(markdown_parts)
            if tab_markdown.strip():  # Only add non-empty tabs
                tab_sections.append((tab_title, tab_markdown))
        
        return tab_sections if tab_sections else [('', '')]
    
    if not split_by_sections:
        # Single file mode - combine everything from all tabs
        markdown_parts = []
        for tab_title, content in all_content:
            if len(all_content) > 1:
                markdown_parts.append(f'\n# {tab_title}\n\n')
            
            for element in content:
                if 'paragraph' in element:
                    markdown = convert_paragraph_to_markdown(element)
                    markdown_parts.append(markdown)
                elif 'table' in element:
                    markdown = convert_table_to_markdown(element)
                    markdown_parts.append(markdown)
                elif 'sectionBreak' in element:
                    markdown_parts.append('\n---\n\n')
        
        return [('', ''.join(markdown_parts))]
    
    else:
        # Split by sections mode - detect major headings (H1) as section breaks
        sections = []
        current_section = []
        current_section_title = None
        has_content_before_first_heading = False
        
        # Process all content from all tabs
        for tab_title, content in all_content:
            # Add tab title as a section if we have multiple tabs
            if len(all_content) > 1 and content:
                if current_section:
                    title = current_section_title or 'Introduction'
                    sections.append((title, ''.join(current_section)))
                current_section_title = tab_title
                current_section = []
        
        # Process all elements from all tabs
        for tab_title, content in all_content:
            for element in content:
                if 'paragraph' in element:
                    para = element['paragraph']
                    para_style = para.get('paragraphStyle', {})
                    named_style = para_style.get('namedStyleType', 'NORMAL_TEXT')
                    
                    # Check if this is a major heading (H1 only) that should start a new section
                    if named_style == 'HEADING_1':
                        # Save previous section if it has content
                        if current_section:
                            # Use a default title if we haven't set one yet
                            title = current_section_title or 'Introduction'
                            sections.append((title, ''.join(current_section)))
                        
                        # Start new section
                        text_parts = []
                        for elem in para.get('elements', []):
                            text = extract_text_runs(elem)
                            if text:
                                text_parts.append(text)
                        # Clean up the title (remove markdown formatting)
                        raw_title = ''.join(text_parts).strip()
                        # Remove bold/italic markers
                        current_section_title = re.sub(r'\*\*?([^*]+)\*\*?', r'\1', raw_title).strip() or 'Untitled Section'
                        current_section = []
                        # Add the heading to the new section
                        markdown = convert_paragraph_to_markdown(element)
                        current_section.append(markdown)
                        has_content_before_first_heading = True
                    else:
                        markdown = convert_paragraph_to_markdown(element)
                        current_section.append(markdown)
                        if not has_content_before_first_heading and current_section_title is None:
                            # We have content before the first H1
                            current_section_title = 'Introduction'
                        
                elif 'table' in element:
                    markdown = convert_table_to_markdown(element)
                    current_section.append(markdown)
                elif 'sectionBreak' in element:
                    # Section breaks can also indicate a new section
                    # Save current section if it has content
                    if current_section:
                        title = current_section_title or 'Untitled Section'
                        sections.append((title, ''.join(current_section)))
                    current_section_title = 'Untitled Section'
                    current_section = []
        
        # Add final section
        if current_section:
            title = current_section_title or 'Untitled Section'
            sections.append((title, ''.join(current_section)))
        
        return sections if sections else [('Introduction', '')]


def sanitize_filename(title: str) -> str:
    """Convert document title to a valid filename."""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', title)
    # Replace spaces with hyphens
    filename = re.sub(r'\s+', '-', filename)
    # Remove multiple hyphens
    filename = re.sub(r'-+', '-', filename)
    # Convert to lowercase
    filename = filename.lower()
    # Add .md extension if not present
    if not filename.endswith('.md'):
        filename += '.md'
    return filename


def main():
    parser = argparse.ArgumentParser(
        description='Export Google Document to markdown'
    )
    parser.add_argument(
        '--doc-id',
        required=True,
        help='Google Docs document ID'
    )
    parser.add_argument(
        '--output',
        help='Output markdown file path (default: auto-generated from title)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing file without prompting'
    )
    parser.add_argument(
        '--split-sections',
        action='store_true',
        help='Split document into separate files by major headings (H1/H2)'
    )
    parser.add_argument(
        '--split-tabs',
        action='store_true',
        help='Split document into separate files by tabs (one file per tab)'
    )
    
    args = parser.parse_args()
    
    # Get credentials
    try:
        creds = get_credentials()
    except Exception as e:
        print(f"Error getting credentials: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Build service
    try:
        service = build('docs', 'v1', credentials=creds)
    except Exception as e:
        print(f"Error building service: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get document - request all content including tabs
    try:
        # Request the full document with all tabs content
        doc = service.documents().get(
            documentId=args.doc_id,
            includeTabsContent=True
        ).execute()
    except HttpError as e:
        if e.resp.status == 404:
            print(f"Error: Document not found. Check the document ID and ensure it's shared with your account.", file=sys.stderr)
        elif e.resp.status == 403:
            print(f"Error: Permission denied. Share the document with your service account or authenticate with OAuth.", file=sys.stderr)
        else:
            print(f"Error fetching document: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Get document title
    title = doc.get('title', 'Untitled Document')
    print(f"Document: {title}", file=sys.stderr)
    
    # Convert to markdown (returns list of sections)
    sections = convert_document_to_markdown(doc, split_by_sections=args.split_sections, split_by_tabs=args.split_tabs)
    
    if args.split_tabs:
        # Write each tab to a separate file in a folder
        if args.output:
            # If output is specified, use it as the folder name
            output_path = Path(args.output)
            if output_path.suffix == '.md':
                # If it ends with .md, use the stem as folder name
                folder_name = output_path.stem
                base_path = output_path.parent / folder_name
            else:
                # Otherwise use it as the folder name directly
                base_path = output_path
        else:
            # Default to document title as folder name
            folder_name = sanitize_filename(title).replace('.md', '')
            base_path = Path('.') / folder_name
        
        # Create the folder
        base_path.mkdir(parents=True, exist_ok=True)
        
        print(f"Found {len(sections)} tabs", file=sys.stderr)
        print(f"Exporting to folder: {base_path.absolute()}", file=sys.stderr)
        
        for tab_title, markdown in sections:
            # Create filename from tab title
            if tab_title:
                tab_filename = sanitize_filename(tab_title)
            else:
                tab_filename = "untitled.md"
            
            output_file = base_path / tab_filename
            
            # Check if file exists
            if output_file.exists() and not args.force:
                print(f"Warning: {output_file} already exists. Skipping. Use --force to overwrite.", file=sys.stderr)
                continue
            
            # Write tab to file
            try:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                print(f"  Exported tab '{tab_title}' to: {output_file.absolute()}", file=sys.stderr)
            except Exception as e:
                print(f"Error writing file {output_file}: {e}", file=sys.stderr)
    
    elif args.split_sections:
        # Write each section to a separate file
        base_path = Path(args.output).parent if args.output else Path('.')
        base_name = Path(args.output).stem if args.output else sanitize_filename(title).replace('.md', '')
        
        print(f"Found {len(sections)} sections", file=sys.stderr)
        
        for i, (section_title, markdown) in enumerate(sections, 1):
            # Create filename from section title
            if section_title:
                section_filename = sanitize_filename(section_title)
            else:
                section_filename = f"{base_name}-{i:02d}.md"
            
            output_file = base_path / section_filename
            
            # Check if file exists
            if output_file.exists() and not args.force:
                print(f"Warning: {output_file} already exists. Skipping. Use --force to overwrite.", file=sys.stderr)
                continue
            
            # Write section to file
            try:
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                print(f"  Exported section '{section_title}' to: {output_file.absolute()}", file=sys.stderr)
            except Exception as e:
                print(f"Error writing file {output_file}: {e}", file=sys.stderr)
    else:
        # Single file mode
        _, markdown = sections[0]
        
        # Determine output file
        if args.output:
            output_file = Path(args.output)
        else:
            output_file = Path(sanitize_filename(title))
        
        # Check if file exists
        if output_file.exists() and not args.force:
            print(f"Error: File {output_file} already exists. Use --force to overwrite.", file=sys.stderr)
            sys.exit(1)
        
        # Write to file
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown)
            print(f"Exported to: {output_file.absolute()}", file=sys.stderr)
        except Exception as e:
            print(f"Error writing file: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()


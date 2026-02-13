#!/usr/bin/env python3
"""
Convert Markdown to Google Docs

Converts a markdown file to Google Docs format and uploads it to Google Drive.
Uses pandoc for markdown→docx conversion, then Google Drive API for upload.

Supports updating existing docs by storing the doc ID in the markdown file:
<!-- google-doc-id: 1abc123... -->
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# Google API imports
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Pattern to find Google Doc ID in markdown
DOC_ID_PATTERN = re.compile(r'<!--\s*google-doc-id:\s*([a-zA-Z0-9_-]+)\s*-->')

# Default reference template (for consistent styling)
SCRIPT_DIR = Path(__file__).parent
DEFAULT_REFERENCE_DOC = SCRIPT_DIR / 'reference-template.docx'

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/documents'
]

def get_credentials():
    """Get Google API credentials via OAuth."""
    # Use separate token file for this skill (needs drive.file scope)
    token_file = os.environ.get('GOOGLE_DRIVE_TOKEN_FILE',
                                os.path.expanduser('~/.google-drive-upload-token.json'))
    client_secret_file = os.environ.get('GOOGLE_CLIENT_SECRET_FILE')

    if not client_secret_file:
        print("Error: GOOGLE_CLIENT_SECRET_FILE environment variable not set")
        print("See the google-docs-to-markdown skill for setup instructions")
        sys.exit(1)

    creds = None

    # Load existing token
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    # Refresh or get new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token
        with open(token_file, 'w') as f:
            f.write(creds.to_json())

    return creds


def extract_doc_id(content: str) -> tuple[str, str]:
    """Extract Google Doc ID from markdown content and return (doc_id, clean_content)."""
    match = DOC_ID_PATTERN.search(content)
    if match:
        doc_id = match.group(1)
        # Remove the comment line from content
        clean_content = DOC_ID_PATTERN.sub('', content).lstrip('\n')
        return doc_id, clean_content
    return None, content


def save_doc_id_to_markdown(markdown_path: str, doc_id: str):
    """Add Google Doc ID comment to the top of the markdown file."""
    with open(markdown_path, 'r') as f:
        content = f.read()

    # Check if already has a doc ID
    if DOC_ID_PATTERN.search(content):
        # Replace existing
        content = DOC_ID_PATTERN.sub(f'<!-- google-doc-id: {doc_id} -->', content)
    else:
        # Add to top
        content = f'<!-- google-doc-id: {doc_id} -->\n\n{content}'

    with open(markdown_path, 'w') as f:
        f.write(content)


def preprocess_markdown_for_lists(content: str) -> str:
    """Ensure blank lines before list items that follow paragraphs.

    Pandoc requires a blank line before the start of a list block.
    Without this, bullets immediately after a paragraph line get merged
    into that paragraph as inline text instead of becoming list items.
    """
    lines = content.split('\n')
    result = []
    for i, line in enumerate(lines):
        # Check if this line starts a list item (-, *, +, or 1.)
        if re.match(r'^[\-\*\+]\s', line) or re.match(r'^\d+\.\s', line):
            # Insert blank line if previous line is non-empty, non-blank,
            # and not itself a list item
            if result and result[-1].strip() and not re.match(r'^[\-\*\+]\s', result[-1]) and not re.match(r'^\d+\.\s', result[-1]):
                result.append('')
        result.append(line)
    return '\n'.join(result)


def convert_markdown_to_docx(markdown_path: str, docx_path: str, reference_doc: str = None, content_override: str = None):
    """Convert markdown to docx using pandoc."""

    # If we have cleaned content (with doc ID stripped), use temp file
    if content_override:
        content_override = preprocess_markdown_for_lists(content_override)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
            tmp.write(content_override)
            markdown_path = tmp.name
    else:
        # Preprocess the file content even when no content_override
        with open(markdown_path, 'r') as f:
            raw = f.read()
        preprocessed = preprocess_markdown_for_lists(raw)
        if preprocessed != raw:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
                tmp.write(preprocessed)
                markdown_path = tmp.name

    cmd = ['pandoc', markdown_path, '-o', docx_path]

    # Use reference doc for styling if provided
    if reference_doc and os.path.exists(reference_doc):
        cmd.extend(['--reference-doc', reference_doc])

    # Add options for better formatting
    # -auto_identifiers removes bookmarks/anchors from headings
    cmd.extend([
        '--from', 'markdown+pipe_tables+backtick_code_blocks-auto_identifiers',
        '--wrap', 'none',
    ])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Pandoc error: {result.stderr}")
        sys.exit(1)

    return docx_path


def apply_document_styles(doc_id: str, heading_font: str = 'Proxima Nova'):
    """Apply custom styles to document via Google Docs API."""
    import time

    creds = get_credentials()
    docs_service = build('docs', 'v1', credentials=creds)

    # Get the document structure
    doc = docs_service.documents().get(documentId=doc_id).execute()

    requests = []
    table_count = 0
    list_item_count = 0

    # 0.5pt border style with dark gray 1 color (#b7b7b7)
    border_style = {
        'width': {'magnitude': 0.5, 'unit': 'PT'},
        'dashStyle': 'SOLID',
        'color': {
            'color': {
                'rgbColor': {
                    'red': 0.718,
                    'green': 0.718,
                    'blue': 0.718
                }
            }
        }
    }

    # Header row background color (#f3f3f3)
    header_bg_color = {
        'color': {
            'rgbColor': {
                'red': 0.953,
                'green': 0.953,
                'blue': 0.953
            }
        }
    }

    for element in doc.get('body', {}).get('content', []):
        # Handle headings and list items
        if 'paragraph' in element:
            para = element['paragraph']
            style = para.get('paragraphStyle', {}).get('namedStyleType', '')
            start_index = element.get('startIndex', 0)
            end_index = element.get('endIndex', start_index)

            # Style headings with Proxima Nova
            if style.startswith('HEADING_'):
                # Skip empty ranges
                if end_index - 1 > start_index:
                    requests.append({
                        'updateTextStyle': {
                            'range': {
                                'startIndex': start_index,
                                'endIndex': end_index - 1
                            },
                            'textStyle': {
                                'weightedFontFamily': {
                                    'fontFamily': heading_font,
                                    'weight': 700
                                }
                            },
                            'fields': 'weightedFontFamily'
                        }
                    })

            # Add space after all paragraphs (including list items)
            # Skip empty paragraphs
            if end_index > start_index:
                list_item_count += 1
                requests.append({
                    'updateParagraphStyle': {
                        'range': {
                            'startIndex': start_index,
                            'endIndex': end_index
                        },
                        'paragraphStyle': {
                            'spaceBelow': {
                                'magnitude': 6,
                                'unit': 'PT'
                            }
                        },
                        'fields': 'spaceBelow'
                    }
                })

        # Handle tables
        if 'table' in element:
            table = element['table']
            table_count += 1
            start_index = element.get('startIndex', 0)

            rows = table.get('rows', 0)
            cols = table.get('columns', 0)

            # Apply borders and vertical center alignment to all cells
            requests.append({
                'updateTableCellStyle': {
                    'tableRange': {
                        'tableCellLocation': {
                            'tableStartLocation': {'index': start_index},
                            'rowIndex': 0,
                            'columnIndex': 0
                        },
                        'rowSpan': rows,
                        'columnSpan': cols
                    },
                    'tableCellStyle': {
                        'borderTop': border_style,
                        'borderBottom': border_style,
                        'borderLeft': border_style,
                        'borderRight': border_style,
                        'contentAlignment': 'MIDDLE',
                    },
                    'fields': 'borderTop,borderBottom,borderLeft,borderRight,contentAlignment'
                }
            })

            # Apply header row styling (first row): background color + bold text
            requests.append({
                'updateTableCellStyle': {
                    'tableRange': {
                        'tableCellLocation': {
                            'tableStartLocation': {'index': start_index},
                            'rowIndex': 0,
                            'columnIndex': 0
                        },
                        'rowSpan': 1,
                        'columnSpan': cols
                    },
                    'tableCellStyle': {
                        'backgroundColor': header_bg_color,
                    },
                    'fields': 'backgroundColor'
                }
            })

            # Make header row text bold - need to find text ranges in first row
            table_rows = table.get('tableRows', [])
            if table_rows:
                first_row = table_rows[0]
                for cell in first_row.get('tableCells', []):
                    for content in cell.get('content', []):
                        if 'paragraph' in content:
                            cell_start = content.get('startIndex', 0)
                            cell_end = content.get('endIndex', cell_start)
                            # Skip empty ranges
                            if cell_end - 1 > cell_start:
                                requests.append({
                                    'updateTextStyle': {
                                        'range': {
                                            'startIndex': cell_start,
                                            'endIndex': cell_end - 1
                                        },
                                        'textStyle': {
                                            'bold': True
                                        },
                                        'fields': 'bold'
                                    }
                                })

    if requests:
        # Batch requests in groups of 30 to avoid rate limits (60/min limit)
        batch_size = 30
        for i in range(0, len(requests), batch_size):
            batch = requests[i:i+batch_size]
            try:
                docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': batch}
                ).execute()
            except Exception as e:
                if 'Quota exceeded' in str(e) or '429' in str(e):
                    print(f"  Rate limit hit, waiting 60s...")
                    time.sleep(60)
                    # Retry
                    docs_service.documents().batchUpdate(
                        documentId=doc_id,
                        body={'requests': batch}
                    ).execute()
                else:
                    raise

            # Small delay between batches to avoid hitting rate limit
            if i + batch_size < len(requests):
                time.sleep(1.5)

        heading_count = sum(1 for r in requests if 'updateTextStyle' in r and 'weightedFontFamily' in r.get('updateTextStyle', {}).get('textStyle', {}))
        print(f"  Applied {heading_font} font to {heading_count} headings")
        if table_count:
            print(f"  Applied borders, header styling, and vertical alignment to {table_count} tables")
        if list_item_count:
            print(f"  Added spacing after {list_item_count} paragraphs")


def clear_document_content(docs_service, doc_id: str):
    """Clear all content from a Google Doc, leaving it empty."""
    doc = docs_service.documents().get(documentId=doc_id).execute()

    # Find the end index of the document body
    body = doc.get('body', {})
    content = body.get('content', [])

    if not content:
        return

    # The last element's endIndex - 1 is where content ends (excluding final newline)
    end_index = content[-1].get('endIndex', 1) - 1

    if end_index > 1:
        # Delete from index 1 to end (index 0 is reserved, can't delete)
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={
                'requests': [{
                    'deleteContentRange': {
                        'range': {
                            'startIndex': 1,
                            'endIndex': end_index
                        }
                    }
                }]
            }
        ).execute()

    # Remove any orphaned list definitions from the remaining empty paragraph.
    # Without this, re-uploaded content can inherit bullet formatting from the
    # previous version of the document.
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={
            'requests': [{
                'deleteParagraphBullets': {
                    'range': {
                        'startIndex': 1,
                        'endIndex': 2
                    }
                }
            }]
        }
    ).execute()


def copy_document_content(docs_service, source_doc_id: str, dest_doc_id: str):
    """Copy all content from source doc to destination doc using Docs API."""
    # Get source document structure
    source_doc = docs_service.documents().get(documentId=source_doc_id).execute()
    source_body = source_doc.get('body', {}).get('content', [])

    if not source_body:
        return

    requests = []

    # Process elements in reverse order since we're inserting at index 1
    # This maintains the correct order in the destination
    for element in reversed(source_body):
        if 'paragraph' in element:
            para = element['paragraph']
            elements = para.get('elements', [])

            # Build the text content with formatting
            for elem in reversed(elements):
                if 'textRun' in elem:
                    text_run = elem['textRun']
                    content = text_run.get('content', '')
                    text_style = text_run.get('textStyle', {})

                    if content:
                        requests.append({
                            'insertText': {
                                'location': {'index': 1},
                                'text': content
                            }
                        })

                        # Apply text styling if present
                        if text_style and len(content) > 0:
                            # We'll apply styles after all content is inserted
                            pass

            # Handle paragraph style (bullet lists, etc.)
            para_style = para.get('paragraphStyle', {})
            bullet = para.get('bullet', None)

        elif 'table' in element:
            # Tables are complex - we'll let them come through the temp doc approach
            pass

    if requests:
        docs_service.documents().batchUpdate(
            documentId=dest_doc_id,
            body={'requests': requests}
        ).execute()


def copy_doc_content_to_existing(docs_service, source_doc_id: str, dest_doc_id: str):
    """Copy content from source doc to destination, preserving formatting.

    Preserves: paragraph styles, text styles (bold, italic, underline), and tables.
    Uses batched API calls to avoid rate limits.
    """
    import time

    # Get source document structure
    source_doc = docs_service.documents().get(documentId=source_doc_id).execute()
    source_body = source_doc.get('body', {}).get('content', [])

    if not source_body:
        return

    # Capture list definitions so we can distinguish numbered vs bulleted lists
    source_lists = source_doc.get('lists', {})

    # Collect paragraphs with their text runs (preserving inline formatting info)
    # Each paragraph: (named_style, [(text, text_style), ...])
    paragraphs = []
    table_info = []  # (position_in_paragraphs, table_element)

    for element in source_body:
        if 'paragraph' in element:
            para = element['paragraph']
            para_style = para.get('paragraphStyle', {})
            named_style = para_style.get('namedStyleType', 'NORMAL_TEXT')
            bullet = para.get('bullet')

            text_runs = []

            # For nested bullets, prepend tab characters to indicate nesting level
            if bullet:
                nesting_level = bullet.get('nestingLevel', 0)
                if nesting_level > 0:
                    text_runs.append(('\t' * nesting_level, {}))

            for para_elem in para.get('elements', []):
                if 'textRun' in para_elem:
                    text = para_elem['textRun'].get('content', '')
                    text_style = para_elem['textRun'].get('textStyle', {})
                    if text:
                        text_runs.append((text, text_style))

            if text_runs:
                paragraphs.append((named_style, text_runs, bullet))

        elif 'table' in element:
            table_info.append((len(paragraphs), element['table']))
            # Placeholder paragraph for table position
            paragraphs.append(('NORMAL_TEXT', [('\n', {})], None))

    # Step 1: Insert all text content in one batch
    all_text = ''
    for named_style, text_runs, bullet in paragraphs:
        for text, style in text_runs:
            all_text += text

    if all_text:
        docs_service.documents().batchUpdate(
            documentId=dest_doc_id,
            body={'requests': [{
                'insertText': {
                    'endOfSegmentLocation': {'segmentId': ''},
                    'text': all_text
                }
            }]}
        ).execute()

    # Step 2: Apply paragraph styles AND text styles
    format_requests = []
    current_index = 1  # Start after index 0

    for named_style, text_runs, bullet in paragraphs:
        para_start = current_index
        para_len = sum(len(text) for text, _ in text_runs)

        # Apply paragraph style (headings)
        if named_style and named_style != 'NORMAL_TEXT':
            format_requests.append({
                'updateParagraphStyle': {
                    'range': {'startIndex': para_start, 'endIndex': para_start + para_len},
                    'paragraphStyle': {'namedStyleType': named_style},
                    'fields': 'namedStyleType'
                }
            })

        # Apply text styles (bold, italic, etc.) for each text run
        for text, text_style in text_runs:
            text_len = len(text)
            if text_len > 0 and text_style:
                # Build the style update
                style_fields = []
                style_update = {}

                if text_style.get('bold'):
                    style_update['bold'] = True
                    style_fields.append('bold')

                if text_style.get('italic'):
                    style_update['italic'] = True
                    style_fields.append('italic')

                if text_style.get('underline'):
                    style_update['underline'] = True
                    style_fields.append('underline')

                if text_style.get('strikethrough'):
                    style_update['strikethrough'] = True
                    style_fields.append('strikethrough')

                # Handle font family
                if 'weightedFontFamily' in text_style:
                    style_update['weightedFontFamily'] = text_style['weightedFontFamily']
                    style_fields.append('weightedFontFamily')

                # Handle foreground color
                if 'foregroundColor' in text_style:
                    style_update['foregroundColor'] = text_style['foregroundColor']
                    style_fields.append('foregroundColor')

                # Handle background color
                if 'backgroundColor' in text_style:
                    style_update['backgroundColor'] = text_style['backgroundColor']
                    style_fields.append('backgroundColor')

                # Handle font size
                if 'fontSize' in text_style:
                    style_update['fontSize'] = text_style['fontSize']
                    style_fields.append('fontSize')

                # Handle links - ensure proper structure
                if 'link' in text_style:
                    link_data = text_style['link']
                    # Links can have url, bookmarkId, or headingId
                    if isinstance(link_data, dict) and ('url' in link_data or 'bookmarkId' in link_data or 'headingId' in link_data):
                        style_update['link'] = link_data
                        style_fields.append('link')

                if style_fields and current_index + text_len - 1 > current_index:
                    # Don't include trailing newline in text style range
                    end_idx = current_index + text_len
                    if text.endswith('\n'):
                        end_idx -= 1

                    if end_idx > current_index:
                        format_requests.append({
                            'updateTextStyle': {
                                'range': {'startIndex': current_index, 'endIndex': end_idx},
                                'textStyle': style_update,
                                'fields': ','.join(style_fields)
                            }
                        })

            current_index += text_len

    if format_requests:
        # Batch format requests (up to 50 at a time to be safe)
        for i in range(0, len(format_requests), 50):
            batch = format_requests[i:i+50]
            try:
                docs_service.documents().batchUpdate(
                    documentId=dest_doc_id,
                    body={'requests': batch}
                ).execute()
                time.sleep(0.5)  # Small delay between batches
            except Exception as e:
                print(f"  Warning: Could not apply some formatting: {e}")

    # Step 2b: Apply bullet formatting in a separate pass.
    # This must happen after all text insertion and paragraph styling to avoid
    # index conflicts. We collect contiguous bullet ranges, determine whether
    # they are numbered or bulleted, and send createParagraphBullets requests.
    bullet_requests = []
    bullet_index = 1  # mirrors current_index tracking above

    for named_style, text_runs, bullet in paragraphs:
        para_start = bullet_index
        para_len = sum(len(text) for text, _ in text_runs)

        if bullet:
            # Determine if numbered or bulleted by checking source list properties
            list_id = bullet.get('listId', '')
            preset = 'BULLET_DISC_CIRCLE_SQUARE'  # default to unordered

            if list_id and list_id in source_lists:
                list_props = source_lists[list_id]
                nesting_levels = list_props.get('listProperties', {}).get('nestingLevels', [])
                if nesting_levels:
                    first_level = nesting_levels[0]
                    glyph_type = first_level.get('glyphType', '')
                    # Numbered list glyph types: DECIMAL, ALPHA, ROMAN, ZERO_DECIMAL, UPPER_ALPHA, UPPER_ROMAN
                    if glyph_type in ('DECIMAL', 'ALPHA', 'ROMAN', 'ZERO_DECIMAL', 'UPPER_ALPHA', 'UPPER_ROMAN'):
                        preset = 'NUMBERED_DECIMAL_ALPHA_ROMAN'

            bullet_requests.append({
                'createParagraphBullets': {
                    'range': {
                        'startIndex': para_start,
                        'endIndex': para_start + para_len
                    },
                    'bulletPreset': preset
                }
            })

        bullet_index += para_len

    if bullet_requests:
        for i in range(0, len(bullet_requests), 50):
            batch = bullet_requests[i:i+50]
            try:
                docs_service.documents().batchUpdate(
                    documentId=dest_doc_id,
                    body={'requests': batch}
                ).execute()
                time.sleep(0.5)
            except Exception as e:
                print(f"  Warning: Could not apply some bullet formatting: {e}")

    # Step 3: Handle tables - need to insert them and fill content
    # Tables are more complex because we need to:
    # 1. Delete the placeholder newline
    # 2. Insert table structure
    # 3. Fill table cells

    if table_info:
        # Process tables in reverse order to avoid index shifting issues
        for text_pos, table in reversed(table_info):
            # Calculate where this table's placeholder is in the document
            placeholder_start = 1  # Start at beginning
            for i in range(text_pos):
                # paragraphs[i] = (named_style, text_runs, bullet)
                # text_runs = [(text, text_style), ...]
                para_len = sum(len(text) for text, _ in paragraphs[i][1])
                placeholder_start += para_len

            rows = table.get('rows', 0)
            cols = table.get('columns', 0)

            # Delete placeholder and insert table
            requests = [
                {
                    'deleteContentRange': {
                        'range': {
                            'startIndex': placeholder_start,
                            'endIndex': placeholder_start + 1  # Delete the \n placeholder
                        }
                    }
                },
                {
                    'insertTable': {
                        'location': {'index': placeholder_start},
                        'rows': rows,
                        'columns': cols
                    }
                }
            ]

            docs_service.documents().batchUpdate(
                documentId=dest_doc_id,
                body={'requests': requests}
            ).execute()

            # Delay between tables to avoid rate limits
            time.sleep(1.5)

            # Get updated doc to find cell indices
            updated_doc = docs_service.documents().get(documentId=dest_doc_id).execute()
            dest_content = updated_doc.get('body', {}).get('content', [])

            # Find the table we just inserted (should be at placeholder_start)
            dest_table = None
            for elem in dest_content:
                if 'table' in elem and elem.get('startIndex', 0) >= placeholder_start - 1:
                    dest_table = elem['table']
                    break

            if dest_table:
                # Fill table cells, preserving text styles (bold, links, etc.)
                source_rows = table.get('tableRows', [])
                dest_rows = dest_table.get('tableRows', [])

                # Step 1: Collect source cell data by (row, col) position
                # Store: {(row, col): [(text, text_style), ...]}
                source_cell_data = {}

                for row_idx, source_row in enumerate(source_rows):
                    source_cells = source_row.get('tableCells', [])
                    for col_idx, source_cell in enumerate(source_cells):
                        text_runs = []
                        for content in source_cell.get('content', []):
                            if 'paragraph' in content:
                                for elem in content['paragraph'].get('elements', []):
                                    if 'textRun' in elem:
                                        text = elem['textRun'].get('content', '')
                                        style = elem['textRun'].get('textStyle', {})
                                        if text:
                                            text_runs.append((text, style))
                        if text_runs:
                            # Strip trailing newline from last text run
                            last_text, last_style = text_runs[-1]
                            if last_text.endswith('\n'):
                                text_runs[-1] = (last_text.rstrip('\n'), last_style)
                            source_cell_data[(row_idx, col_idx)] = text_runs

                # Step 2: Insert text into all cells (collect inserts, execute in reverse)
                cell_inserts = []  # [(insert_idx, row, col, full_text), ...]

                for row_idx, dest_row in enumerate(dest_rows):
                    dest_cells = dest_row.get('tableCells', [])
                    for col_idx, dest_cell in enumerate(dest_cells):
                        if (row_idx, col_idx) in source_cell_data:
                            text_runs = source_cell_data[(row_idx, col_idx)]
                            full_text = ''.join(t for t, s in text_runs)
                            if full_text:
                                dest_cell_content = dest_cell.get('content', [])
                                if dest_cell_content and 'paragraph' in dest_cell_content[0]:
                                    insert_idx = dest_cell_content[0].get('startIndex', 0)
                                    cell_inserts.append((insert_idx, row_idx, col_idx, full_text))

                if cell_inserts:
                    # Insert in reverse order to avoid index shifting during insertion
                    cell_inserts.sort(key=lambda x: x[0], reverse=True)
                    insert_requests = [{
                        'insertText': {
                            'location': {'index': idx},
                            'text': text
                        }
                    } for idx, row, col, text in cell_inserts]

                    docs_service.documents().batchUpdate(
                        documentId=dest_doc_id,
                        body={'requests': insert_requests}
                    ).execute()

                    # Step 3: Re-fetch document to get NEW indices after text insertion
                    time.sleep(0.3)
                    updated_doc = docs_service.documents().get(documentId=dest_doc_id).execute()
                    updated_content = updated_doc.get('body', {}).get('content', [])

                    # Find the table again with updated indices
                    updated_table = None
                    for elem in updated_content:
                        if 'table' in elem and elem.get('startIndex', 0) >= placeholder_start - 1:
                            updated_table = elem['table']
                            break

                    if updated_table:
                        # Step 4: Apply text styles using NEW indices from updated table
                        style_requests = []
                        updated_rows = updated_table.get('tableRows', [])

                        for row_idx, updated_row in enumerate(updated_rows):
                            updated_cells = updated_row.get('tableCells', [])
                            for col_idx, updated_cell in enumerate(updated_cells):
                                if (row_idx, col_idx) not in source_cell_data:
                                    continue

                                text_runs = source_cell_data[(row_idx, col_idx)]

                                # Get the starting index of this cell's content
                                cell_content = updated_cell.get('content', [])
                                if not cell_content or 'paragraph' not in cell_content[0]:
                                    continue

                                current_idx = cell_content[0].get('startIndex', 0)

                                for text, text_style in text_runs:
                                    text_len = len(text)
                                    if text_len > 0 and text_style:
                                        style_update = {}
                                        style_fields = []

                                        if text_style.get('bold'):
                                            style_update['bold'] = True
                                            style_fields.append('bold')
                                        if text_style.get('italic'):
                                            style_update['italic'] = True
                                            style_fields.append('italic')
                                        if text_style.get('underline'):
                                            style_update['underline'] = True
                                            style_fields.append('underline')

                                        # Handle links
                                        if 'link' in text_style:
                                            link_data = text_style['link']
                                            if isinstance(link_data, dict) and ('url' in link_data or 'bookmarkId' in link_data or 'headingId' in link_data):
                                                style_update['link'] = link_data
                                                style_fields.append('link')

                                        if style_fields:
                                            end_idx = current_idx + text_len
                                            if end_idx > current_idx:
                                                style_requests.append({
                                                    'updateTextStyle': {
                                                        'range': {'startIndex': current_idx, 'endIndex': end_idx},
                                                        'textStyle': style_update,
                                                        'fields': ','.join(style_fields)
                                                    }
                                                })
                                    current_idx += text_len

                        if style_requests:
                            # Batch in groups with delays to avoid rate limits
                            for i in range(0, len(style_requests), 20):
                                batch = style_requests[i:i+20]
                                try:
                                    docs_service.documents().batchUpdate(
                                        documentId=dest_doc_id,
                                        body={'requests': batch}
                                    ).execute()
                                    time.sleep(1.5)  # Rate limit delay
                                except Exception as e:
                                    if 'Quota exceeded' in str(e) or '429' in str(e):
                                        print(f"  Rate limit hit on table styles, waiting 60s...")
                                        time.sleep(60)
                                        docs_service.documents().batchUpdate(
                                            documentId=dest_doc_id,
                                            body={'requests': batch}
                                        ).execute()
                                    else:
                                        print(f"  Warning: Could not apply some table cell styles: {e}")

                    # Apply 11pt font to all table cells to override any inherited styles
                    # Need to re-fetch doc to get updated indices
                    time.sleep(0.2)
                    updated_doc2 = docs_service.documents().get(documentId=dest_doc_id).execute()
                    dest_content2 = updated_doc2.get('body', {}).get('content', [])

                    # Find the table again
                    for elem in dest_content2:
                        if 'table' in elem and elem.get('startIndex', 0) >= placeholder_start - 1:
                            tbl = elem['table']
                            font_requests = []
                            for tbl_row in tbl.get('tableRows', []):
                                for tbl_cell in tbl_row.get('tableCells', []):
                                    for cell_content in tbl_cell.get('content', []):
                                        if 'paragraph' in cell_content:
                                            cell_start = cell_content.get('startIndex', 0)
                                            cell_end = cell_content.get('endIndex', cell_start)
                                            if cell_end - 1 > cell_start:
                                                font_requests.append({
                                                    'updateTextStyle': {
                                                        'range': {
                                                            'startIndex': cell_start,
                                                            'endIndex': cell_end - 1
                                                        },
                                                        'textStyle': {
                                                            'fontSize': {
                                                                'magnitude': 11,
                                                                'unit': 'PT'
                                                            }
                                                        },
                                                        'fields': 'fontSize'
                                                    }
                                                })
                            if font_requests:
                                docs_service.documents().batchUpdate(
                                    documentId=dest_doc_id,
                                    body={'requests': font_requests}
                                ).execute()
                            break


def upload_to_drive(docx_path: str, title: str, folder_id: str = None, existing_doc_id: str = None):
    """Upload docx to Google Drive and convert to Google Docs.

    If existing_doc_id is provided, updates the existing doc in place by:
    1. Creating a temp doc from the new docx
    2. Clearing the existing doc
    3. Copying content from temp to existing (preserves URL)
    4. Deleting the temp doc
    """
    creds = get_credentials()
    drive_service = build('drive', 'v3', credentials=creds)
    docs_service = build('docs', 'v1', credentials=creds)

    # First, always upload the docx as a new doc (temp if updating)
    file_metadata = {
        'name': title if not existing_doc_id else f"_temp_{title}",
        'mimeType': 'application/vnd.google-apps.document'
    }

    if folder_id and not existing_doc_id:
        file_metadata['parents'] = [folder_id]

    media = MediaFileUpload(
        docx_path,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        resumable=True
    )

    new_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink'
    ).execute()

    new_doc_id = new_file.get('id')

    if existing_doc_id:
        try:
            # Verify the existing doc exists and get its folder
            existing = drive_service.files().get(
                fileId=existing_doc_id,
                fields='parents'
            ).execute()
            if not folder_id and existing.get('parents'):
                folder_id = existing['parents'][0]

            # Clear the existing document
            print(f"  Clearing existing document...")
            clear_document_content(docs_service, existing_doc_id)

            # Copy content from new doc to existing
            print(f"  Copying new content to existing document...")
            copy_doc_content_to_existing(docs_service, new_doc_id, existing_doc_id)

            # Delete the temp doc
            drive_service.files().delete(fileId=new_doc_id).execute()
            print(f"  Cleaned up temp document")

            # Get the existing doc's URL
            existing_file = drive_service.files().get(
                fileId=existing_doc_id,
                fields='webViewLink'
            ).execute()

            return existing_doc_id, existing_file.get('webViewLink')

        except Exception as e:
            # Clean up temp doc
            try:
                drive_service.files().delete(fileId=new_doc_id).execute()
            except:
                pass

            # Don't create a new doc - preserve the original URL
            if 'Quota exceeded' in str(e) or '429' in str(e):
                print(f"\n  ERROR: Rate limit exceeded. Please wait a minute and try again.")
                print(f"  Original document preserved: {existing_doc_id}")
                sys.exit(1)
            else:
                print(f"\n  ERROR: In-place update failed: {e}")
                print(f"  Original document preserved: {existing_doc_id}")
                sys.exit(1)

    return new_doc_id, new_file.get('webViewLink')


def main():
    parser = argparse.ArgumentParser(
        description='Convert Markdown to Google Docs'
    )
    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('-t', '--title', help='Document title (default: filename)')
    parser.add_argument('-f', '--folder', help='Google Drive folder ID to upload to')
    parser.add_argument('--reference-doc', help='Word template for styling')
    parser.add_argument('--keep-docx', action='store_true', help='Keep intermediate docx file')
    parser.add_argument('--new', action='store_true', help='Force create new doc (ignore existing ID)')
    parser.add_argument('--no-save-id', action='store_true', help='Do not save doc ID to markdown file')

    args = parser.parse_args()

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    # Read markdown and check for existing doc ID
    with open(input_path, 'r') as f:
        content = f.read()

    existing_doc_id, clean_content = extract_doc_id(content)

    if existing_doc_id and not args.new:
        print(f"Found existing doc ID: {existing_doc_id}")

    # Determine title
    title = args.title or input_path.stem

    # Create temp docx
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
        docx_path = tmp.name

    try:
        # Use provided reference doc, or default if it exists
        reference_doc = args.reference_doc
        if not reference_doc and DEFAULT_REFERENCE_DOC.exists():
            reference_doc = str(DEFAULT_REFERENCE_DOC)
            print(f"Using default reference template for styling")

        print(f"Converting {input_path.name} to docx...")
        convert_markdown_to_docx(str(input_path), docx_path, reference_doc, clean_content)

        action = "Updating" if (existing_doc_id and not args.new) else "Uploading"
        print(f"{action} Google Doc '{title}'...")

        doc_id, doc_url = upload_to_drive(
            docx_path,
            title,
            args.folder,
            existing_doc_id if not args.new else None
        )

        # Apply document styles (headings, tables, etc.)
        print("Applying document styles...")
        apply_document_styles(doc_id)

        print(f"\nSuccess!")
        print(f"Document ID: {doc_id}")
        print(f"URL: {doc_url}")

        # Save doc ID to markdown file for future updates
        if not args.no_save_id:
            save_doc_id_to_markdown(str(input_path), doc_id)
            print(f"Doc ID saved to {input_path.name}")

        if args.keep_docx:
            kept_path = input_path.with_suffix('.docx')
            os.rename(docx_path, kept_path)
            print(f"Docx saved: {kept_path}")

    finally:
        # Clean up temp file
        if os.path.exists(docx_path) and not args.keep_docx:
            os.remove(docx_path)


if __name__ == '__main__':
    main()

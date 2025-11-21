"""
CLI Integration for PDF Reading

Commands for reading and searching PDF files.
"""

from typing import Any
import json


def command_pdf_read(args: Any) -> int:
    """Read entire PDF file"""
    from whitemagic.utils.pdf_reader import get_pdf_reader
    
    reader = get_pdf_reader()
    if not reader.available:
        print("❌ PDF reading not available. Install: pip install PyMuPDF")
        return 1
    
    result = reader.read_pdf(args.path, args.max_pages)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return 1
    
    print(f"\n📄 PDF: {result['path']}")
    print(f"Pages: {result['pages_read']}/{result['page_count']}")
    print(f"\n{result['full_text'][:2000]}...")  # First 2000 chars
    
    return 0


def command_pdf_search(args: Any) -> int:
    """Search within PDF"""
    from whitemagic.utils.pdf_reader import get_pdf_reader
    
    reader = get_pdf_reader()
    if not reader.available:
        print("❌ PDF reading not available. Install: pip install PyMuPDF")
        return 1
    
    result = reader.search(args.path, args.query, args.context_lines)
    
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return 1
    
    print(f"\n🔍 Search: {result['query']}")
    print(f"Matches: {result['match_count']}")
    
    for match in result['matches'][:10]:  # First 10
        print(f"\n📄 Page {match['page_number']}, Line {match['line_number']}")
        print(match['context'])
    
    return 0


def register_pdf_commands(subparsers: Any):
    """Register PDF CLI commands"""
    
    # pdf-read
    pdf_read = subparsers.add_parser(
        'pdf-read',
        help='Read PDF file and extract text'
    )
    pdf_read.add_argument('path', help='Path to PDF file')
    pdf_read.add_argument('--max-pages', type=int, default=1000,
                         help='Maximum pages to read')
    
    # pdf-search
    pdf_search = subparsers.add_parser(
        'pdf-search',
        help='Search within PDF file'
    )
    pdf_search.add_argument('path', help='Path to PDF file')
    pdf_search.add_argument('query', help='Search query')
    pdf_search.add_argument('--context-lines', type=int, default=3,
                           help='Lines of context around matches')


# Command handlers
PDF_COMMAND_HANDLERS = {
    "pdf-read": command_pdf_read,
    "pdf-search": command_pdf_search,
}

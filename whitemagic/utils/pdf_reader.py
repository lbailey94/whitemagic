"""
PDF Reading Module for WhiteMagic

Provides PDF extraction capabilities using PyMuPDF (fitz).
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json


class PDFReader:
    """Read and extract text from PDF files"""
    
    def __init__(self):
        try:
            import fitz  # PyMuPDF
            self.fitz = fitz
            self.available = True
        except ImportError:
            self.fitz = None
            self.available = False
            print("⚠️  PyMuPDF not available. Install with: pip install PyMuPDF")
    
    def read_pdf(self, path: str, max_pages: int = 1000) -> Dict[str, Any]:
        """Read entire PDF and extract text
        
        Args:
            path: Path to PDF file
            max_pages: Maximum pages to read
            
        Returns:
            Dict with text, page_count, metadata
        """
        if not self.available:
            return {"error": "PyMuPDF not installed"}
        
        pdf_path = Path(path).expanduser()
        if not pdf_path.exists():
            return {"error": f"File not found: {path}"}
        
        try:
            doc = self.fitz.open(str(pdf_path))
            total_pages = min(len(doc), max_pages)
            
            pages = []
            full_text = []
            
            for page_num in range(total_pages):
                page = doc[page_num]
                text = page.get_text()
                pages.append({
                    "page_number": page_num + 1,
                    "text": text,
                    "char_count": len(text)
                })
                full_text.append(text)
            
            return {
                "path": str(pdf_path),
                "page_count": len(doc),
                "pages_read": total_pages,
                "full_text": "\n\n".join(full_text),
                "pages": pages,
                "metadata": doc.metadata
            }
        except Exception as e:
            return {"error": str(e)}
    
    def extract_text(self, path: str, start_page: int = 1, end_page: Optional[int] = None) -> Dict[str, Any]:
        """Extract text from specific page range
        
        Args:
            path: Path to PDF
            start_page: Start page (1-indexed)
            end_page: End page (inclusive), None = last page
            
        Returns:
            Dict with text and page info
        """
        if not self.available:
            return {"error": "PyMuPDF not installed"}
        
        pdf_path = Path(path).expanduser()
        if not pdf_path.exists():
            return {"error": f"File not found: {path}"}
        
        try:
            doc = self.fitz.open(str(pdf_path))
            end = end_page if end_page else len(doc)
            
            pages = []
            for page_num in range(start_page - 1, min(end, len(doc))):
                page = doc[page_num]
                pages.append({
                    "page_number": page_num + 1,
                    "text": page.get_text()
                })
            
            return {
                "path": str(pdf_path),
                "pages": pages,
                "page_range": f"{start_page}-{end}"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_pages(self, path: str, page_numbers: List[int]) -> Dict[str, Any]:
        """Get specific pages by number
        
        Args:
            path: Path to PDF
            page_numbers: List of page numbers (1-indexed)
            
        Returns:
            Dict with requested pages
        """
        if not self.available:
            return {"error": "PyMuPDF not installed"}
        
        pdf_path = Path(path).expanduser()
        if not pdf_path.exists():
            return {"error": f"File not found: {path}"}
        
        try:
            doc = self.fitz.open(str(pdf_path))
            pages = []
            
            for page_num in page_numbers:
                if 1 <= page_num <= len(doc):
                    page = doc[page_num - 1]
                    pages.append({
                        "page_number": page_num,
                        "text": page.get_text()
                    })
            
            return {
                "path": str(pdf_path),
                "pages": pages
            }
        except Exception as e:
            return {"error": str(e)}
    
    def search(self, path: str, query: str, context_lines: int = 3) -> Dict[str, Any]:
        """Search for text within PDF
        
        Args:
            path: Path to PDF
            query: Search query
            context_lines: Lines of context around matches
            
        Returns:
            Dict with matches and page numbers
        """
        if not self.available:
            return {"error": "PyMuPDF not installed"}
        
        pdf_path = Path(path).expanduser()
        if not pdf_path.exists():
            return {"error": f"File not found: {path}"}
        
        try:
            doc = self.fitz.open(str(pdf_path))
            matches = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                lines = text.split("\n")
                
                for i, line in enumerate(lines):
                    if query.lower() in line.lower():
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        context = "\n".join(lines[start:end])
                        
                        matches.append({
                            "page_number": page_num + 1,
                            "line_number": i + 1,
                            "match": line,
                            "context": context
                        })
            
            return {
                "path": str(pdf_path),
                "query": query,
                "match_count": len(matches),
                "matches": matches
            }
        except Exception as e:
            return {"error": str(e)}


# Convenience instance
_pdf_reader = None

def get_pdf_reader() -> PDFReader:
    """Get global PDF reader instance"""
    global _pdf_reader
    if _pdf_reader is None:
        _pdf_reader = PDFReader()
    return _pdf_reader

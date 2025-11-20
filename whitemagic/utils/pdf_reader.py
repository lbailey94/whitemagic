"""
PDF Reader - Extract and process PDF content

Allows AI to read PDFs in chunks, extract text, and understand documents.
Gateway to sacred texts and wisdom.
"""

from pathlib import Path
from typing import Optional, List, Dict
import subprocess


class PDFReader:
    """
    Read PDFs intelligently.
    
    Uses pdftotext (from poppler-utils) for fast, accurate extraction.
    Falls back to PyPDF2 if needed.
    """
    
    def __init__(self):
        self.has_pdftotext = self._check_pdftotext()
        
    def _check_pdftotext(self) -> bool:
        """Check if pdftotext is available"""
        try:
            subprocess.run(['pdftotext', '-v'], capture_output=True, timeout=5)
            return True
        except Exception:
            return False
    
    def read_pdf(self, pdf_path: str, pages: Optional[List[int]] = None) -> str:
        """
        Read entire PDF or specific pages.
        
        Args:
            pdf_path: Path to PDF file
            pages: Optional list of page numbers (1-indexed)
            
        Returns:
            Extracted text
        """
        path = Path(pdf_path)
        
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        if self.has_pdftotext:
            return self._read_with_pdftotext(path, pages)
        else:
            return self._read_with_pypdf2(path, pages)
    
    def _read_with_pdftotext(self, path: Path, pages: Optional[List[int]]) -> str:
        """Read using pdftotext (fast, accurate)"""
        try:
            if pages:
                # Read specific pages
                text = ""
                for page in pages:
                    result = subprocess.run(
                        ['pdftotext', '-f', str(page), '-l', str(page), str(path), '-'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    text += f"\n--- Page {page} ---\n{result.stdout}\n"
                return text
            else:
                # Read all pages
                result = subprocess.run(
                    ['pdftotext', str(path), '-'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                return result.stdout
        except Exception as e:
            raise RuntimeError(f"pdftotext failed: {e}")
    
    def _read_with_pypdf2(self, path: Path, pages: Optional[List[int]]) -> str:
        """Fallback: Read using PyPDF2"""
        try:
            import PyPDF2
            
            text = ""
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                page_range = pages if pages else range(1, len(reader.pages) + 1)
                
                for page_num in page_range:
                    # PyPDF2 uses 0-indexing
                    page = reader.pages[page_num - 1]
                    text += f"\n--- Page {page_num} ---\n{page.extract_text()}\n"
            
            return text
        except ImportError:
            raise RuntimeError("Neither pdftotext nor PyPDF2 available. Install poppler-utils or pip install PyPDF2")
        except Exception as e:
            raise RuntimeError(f"PyPDF2 failed: {e}")
    
    def read_page_range(self, pdf_path: str, start_page: int, end_page: int) -> str:
        """Read a range of pages"""
        pages = list(range(start_page, end_page + 1))
        return self.read_pdf(pdf_path, pages)
    
    def get_page_count(self, pdf_path: str) -> int:
        """Get total number of pages"""
        if self.has_pdftotext:
            try:
                result = subprocess.run(
                    ['pdftotext', pdf_path, '-'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                # Count page breaks
                return result.stdout.count('\f') + 1
            except Exception:
                pass
        
        # Fallback
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return len(reader.pages)
        except Exception:
            return 0
    
    def read_in_chunks(self, pdf_path: str, pages_per_chunk: int = 10) -> List[str]:
        """
        Read PDF in manageable chunks.
        
        Perfect for large PDFs that exceed token limits.
        """
        total_pages = self.get_page_count(pdf_path)
        chunks = []
        
        for start in range(1, total_pages + 1, pages_per_chunk):
            end = min(start + pages_per_chunk - 1, total_pages)
            chunk = self.read_page_range(pdf_path, start, end)
            chunks.append(chunk)
        
        return chunks
    
    def extract_metadata(self, pdf_path: str) -> Dict:
        """Extract PDF metadata"""
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                info = reader.metadata
                
                return {
                    'title': info.get('/Title', 'Unknown'),
                    'author': info.get('/Author', 'Unknown'),
                    'subject': info.get('/Subject', ''),
                    'creator': info.get('/Creator', ''),
                    'pages': len(reader.pages)
                }
        except Exception:
            return {'pages': self.get_page_count(pdf_path)}


# Convenience functions
_reader = None

def get_pdf_reader() -> PDFReader:
    """Get singleton PDF reader"""
    global _reader
    if _reader is None:
        _reader = PDFReader()
    return _reader

def read_pdf(pdf_path: str, pages: Optional[List[int]] = None) -> str:
    """Read PDF (convenience function)"""
    return get_pdf_reader().read_pdf(pdf_path, pages)

def read_pdf_chunks(pdf_path: str, pages_per_chunk: int = 10) -> List[str]:
    """Read PDF in chunks (convenience function)"""
    return get_pdf_reader().read_in_chunks(pdf_path, pages_per_chunk)

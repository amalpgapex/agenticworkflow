"""
Word Document Processor - Enhanced Style Preservation
Handles reading and writing Word documents while preserving ALL styles, formatting, and structure
Also handles PDF text extraction for document comparison workflows
"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from typing import Dict, List, Tuple
import io
import re

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("Warning: pdfplumber not installed. PDF support disabled.")


class DocumentProcessor:
    """Processes Word documents with ENHANCED style preservation and PDF extraction"""
    
    def __init__(self):
        self.original_doc_bytes = None
        self.style_map = {}
        self.default_style = 'Normal'
    
    def extract_pdf_content(self, pdf_bytes: bytes) -> str:
        """
        Extract text content from PDF file
        Returns: content_text
        """
        if not PDF_SUPPORT:
            return "Error: PDF support not available. Install pdfplumber: pip install pdfplumber"
        
        try:
            content_parts = []
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text from page
                    text = page.extract_text()
                    if text:
                        # Add page marker for very long documents
                        if len(pdf.pages) > 10:
                            content_parts.append(f"[Page {page_num}]")
                        content_parts.append(text)
            
            if not content_parts:
                return "Error: No text could be extracted from PDF"
            
            content = "\n\n".join(content_parts)
            return content
            
        except Exception as e:
            return f"Error extracting PDF content: {str(e)}"
    
    def extract_content_and_style(self, doc_bytes: bytes) -> Tuple[str, bytes]:
        """
        Extract text content while preserving style information
        Returns: (content_text, original_doc_bytes)
        """
        self.original_doc_bytes = doc_bytes
        doc = Document(io.BytesIO(doc_bytes))
        
        # Build style map from original document
        self._build_style_map(doc)
        
        # Extract text content with structure markers
        content_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                # Add paragraph with style information preserved in metadata
                content_parts.append(para.text)
        
        content = "\n\n".join(content_parts)
        
        return content, doc_bytes
    
    def _build_style_map(self, doc: Document):
        """Build a map of available styles in the document"""
        self.style_map = {}
        try:
            for style in doc.styles:
                self.style_map[style.name] = style
                
            # Identify the most common paragraph style (will use as default)
            style_counts = {}
            for para in doc.paragraphs:
                if para.style and para.style.name:
                    style_counts[para.style.name] = style_counts.get(para.style.name, 0) + 1
            
            if style_counts:
                # Most common style becomes default
                self.default_style = max(style_counts, key=style_counts.get)
        except:
            self.default_style = 'Normal'
    
    def create_document_with_style(self, content: str, original_doc_bytes: bytes) -> bytes:
        """
        Create document using original as template with ENHANCED style preservation
        Preserves: ALL paragraph styles, fonts, formatting, structure
        """
        # Load original document as template
        doc = Document(io.BytesIO(original_doc_bytes))
        
        # Get first paragraph style as reference for body text
        body_style = self._detect_body_style(doc)
        heading_styles = self._detect_heading_styles(doc)
        list_style = self._detect_list_style(doc)
        
        # Clear all body content but keep ALL document properties
        for element in list(doc.element.body):
            if element.tag.endswith('p') or element.tag.endswith('tbl'):
                doc.element.body.remove(element)
        
        # Parse and add new content with intelligent style matching
        self._add_content_with_smart_styling(doc, content, body_style, heading_styles, list_style)
        
        # Save to bytes
        doc_bytes = io.BytesIO()
        doc.save(doc_bytes)
        doc_bytes.seek(0)
        return doc_bytes.getvalue()
    
    def _detect_body_style(self, doc: Document) -> str:
        """Detect the primary body text style from original document"""
        # Look for most common non-heading style
        style_counts = {}
        for para in doc.paragraphs:
            if para.style and para.style.name:
                style_name = para.style.name
                # Exclude headings and list styles
                if not style_name.startswith('Heading') and not style_name.startswith('List'):
                    style_counts[style_name] = style_counts.get(style_name, 0) + 1
        
        if style_counts:
            return max(style_counts, key=style_counts.get)
        return 'Normal'
    
    def _detect_heading_styles(self, doc: Document) -> Dict:
        """Detect available heading styles"""
        headings = {}
        for i in range(1, 10):
            style_name = f'Heading {i}'
            if style_name in [s.name for s in doc.styles]:
                headings[i] = style_name
        
        # If no heading styles, use Normal with bold
        if not headings:
            headings[1] = 'Normal'
        
        return headings
    
    def _detect_list_style(self, doc: Document) -> str:
        """Detect list style from original document"""
        list_styles = ['List Bullet', 'List Number', 'List', 'List Paragraph']
        for style in list_styles:
            if style in [s.name for s in doc.styles]:
                return style
        return None
    
    def _add_content_with_smart_styling(self, doc: Document, content: str, body_style: str, heading_styles: Dict, list_style: str):
        """Add content with intelligent style detection and application - now with markdown formatting support"""
        # Split content into paragraphs
        paragraphs = content.split('\n')
        
        prev_was_heading = False
        in_list = False
        
        for para_text in paragraphs:
            para_text_stripped = para_text.strip()
            
            # Handle empty paragraphs (preserve spacing)
            if not para_text_stripped:
                doc.add_paragraph()
                in_list = False
                continue
            
            # Detect content type and apply appropriate style
            
            # 1. Check for markdown headings first (# ## ###)
            md_heading_level = self._detect_markdown_heading(para_text_stripped)
            if md_heading_level:
                # Remove markdown syntax
                clean_text = re.sub(r'^#+\s+', '', para_text_stripped)
                style_name = heading_styles.get(md_heading_level, heading_styles.get(1, 'Heading 1'))
                para = doc.add_paragraph(clean_text, style=style_name)
                prev_was_heading = True
                in_list = False
                continue
            
            # 2. Check for structural headings (multiple detection methods)
            heading_level = self._detect_heading_level(para_text_stripped, prev_was_heading)
            if heading_level:
                style_name = heading_styles.get(heading_level, heading_styles.get(1, 'Heading 1'))
                para = doc.add_paragraph(para_text_stripped, style=style_name)
                prev_was_heading = True
                in_list = False
                continue
            
            # 3. Check for markdown list items (- or * at start)
            if self._is_markdown_list(para_text_stripped):
                in_list = True
                # Remove markdown prefix
                text = re.sub(r'^[\-\*]\s+', '', para_text_stripped)
                
                if list_style:
                    try:
                        para = doc.add_paragraph(style=list_style)
                        self._add_formatted_text(para, text)
                    except:
                        para = doc.add_paragraph(style=body_style)
                        self._add_formatted_text(para, text)
                else:
                    para = doc.add_paragraph(style=body_style)
                    self._add_formatted_text(para, text)
                prev_was_heading = False
                continue
            
            # 4. Check for numbered list items (1. 2. etc)
            if self._is_list_item(para_text_stripped):
                in_list = True
                # Remove bullet/number prefix for style handling
                text = self._clean_list_prefix(para_text_stripped)
                
                if list_style:
                    try:
                        para = doc.add_paragraph(style=list_style)
                        self._add_formatted_text(para, text)
                    except:
                        para = doc.add_paragraph(style=body_style)
                        self._add_formatted_text(para, text)
                else:
                    para = doc.add_paragraph(style=body_style)
                    self._add_formatted_text(para, text)
                prev_was_heading = False
                continue
            
            # 5. Check for Q&A formatting (FAQ)
            if para_text_stripped.startswith('Q:') or para_text_stripped.startswith('Question:'):
                para = doc.add_paragraph(style=body_style)
                self._add_formatted_text(para, para_text_stripped)
                # Make first run bold
                if para.runs:
                    para.runs[0].bold = True
                prev_was_heading = False
                in_list = False
                continue
            
            if para_text_stripped.startswith('A:') or para_text_stripped.startswith('Answer:'):
                para = doc.add_paragraph(style=body_style)
                self._add_formatted_text(para, para_text_stripped)
                prev_was_heading = False
                in_list = False
                continue
            
            # 6. Regular body paragraph - use detected body style with markdown formatting
            para = doc.add_paragraph(style=body_style)
            self._add_formatted_text(para, para_text_stripped)
            prev_was_heading = False
            
            # If previous was list and this isn't, end list
            if in_list:
                in_list = False
    
    def _detect_markdown_heading(self, text: str) -> int:
        """Detect markdown heading syntax (# ## ###)"""
        match = re.match(r'^(#{1,6})\s+', text)
        if match:
            return len(match.group(1))  # Return heading level (1-6)
        return None
    
    def _is_markdown_list(self, text: str) -> bool:
        """Check if text is a markdown list item (- or * at start)"""
        return bool(re.match(r'^[\-\*]\s+', text))
    
    def _add_formatted_text(self, paragraph, text: str):
        """
        Add text to paragraph with markdown formatting (bold, italic)
        Handles **bold**, *italic*, ***bold+italic***
        """
        # Pattern to match markdown formatting
        # Handles: **bold**, *italic*, ***bold+italic***
        pattern = r'(\*\*\*[^\*]+\*\*\*|\*\*[^\*]+\*\*|\*[^\*]+\*|[^\*]+)'
        
        parts = re.findall(pattern, text)
        
        for part in parts:
            if not part:
                continue
                
            if part.startswith('***') and part.endswith('***'):
                # Bold + Italic
                clean = part.strip('*')
                run = paragraph.add_run(clean)
                run.bold = True
                run.italic = True
            elif part.startswith('**') and part.endswith('**'):
                # Bold
                clean = part.strip('*')
                run = paragraph.add_run(clean)
                run.bold = True
            elif part.startswith('*') and part.endswith('*'):
                # Italic
                clean = part.strip('*')
                run = paragraph.add_run(clean)
                run.italic = True
            else:
                # Regular text
                paragraph.add_run(part)
    
    def _detect_heading_level(self, text: str, prev_was_heading: bool) -> int:
        """
        Intelligent heading detection with multiple strategies
        Returns heading level (1-6) or None
        """
        # Strategy 1: All caps = likely heading level 1
        if text.isupper() and len(text) < 100:
            return 1
        
        # Strategy 2: Title case + short + no ending punctuation
        if text.istitle() and len(text) < 80 and not text.endswith(('.', '!', '?', ',')):
            return 1
        
        # Strategy 3: Numbered sections (1. 1.1, etc.)
        section_match = re.match(r'^(\d+\.)+\s+[A-Z]', text)
        if section_match:
            # Count depth of numbering
            depth = text[:20].count('.')
            return min(depth, 3)  # Cap at Heading 3
        
        # Strategy 4: Common heading patterns
        heading_patterns = [
            r'^(Chapter|Section|Part|Appendix)\s+\d+',
            r'^(Introduction|Conclusion|Summary|Overview|Background)',
            r'^(Step\s+\d+|Phase\s+\d+)',
        ]
        for pattern in heading_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return 2 if prev_was_heading else 1
        
        # Strategy 5: Short + bold-looking (all caps first word)
        words = text.split()
        if words and words[0].isupper() and len(text) < 60 and not text.endswith(('.', '!', '?')):
            return 2
        
        return None
    
    def _is_list_item(self, text: str) -> bool:
        """Check if text is a list item"""
        # Check for bullets
        if text.startswith(('•', '◦', '▪', '■', '○', '-', '*')):
            return True
        
        # Check for numbered lists
        if re.match(r'^\d+[\.\)]\s+', text):
            return True
        
        # Check for lettered lists
        if re.match(r'^[a-zA-Z][\.\)]\s+', text):
            return True
        
        return False
    
    def _clean_list_prefix(self, text: str) -> str:
        """Remove bullet or number prefix from list item"""
        # Remove bullet characters
        text = re.sub(r'^[•◦▪■○\-\*]\s+', '', text)
        
        # Remove numbered list prefix
        text = re.sub(r'^\d+[\.\)]\s+', '', text)
        
        # Remove lettered list prefix
        text = re.sub(r'^[a-zA-Z][\.\)]\s+', '', text)
        
        return text.strip()
    
    def _preserve_headers_footers(self, doc: Document) -> Dict:
        """
        Headers and footers are automatically preserved when using
        original document as template (they're in the sections)
        """
        preserved = {'headers': [], 'footers': []}
        
        try:
            for section in doc.sections:
                if section.header:
                    preserved['headers'].append(section.header)
                if section.footer:
                    preserved['footers'].append(section.footer)
        except:
            pass
        
        return preserved
    
    def get_document_properties(self, doc_bytes: bytes) -> Dict:
        """
        Extract detailed document properties for inspection
        """
        doc = Document(io.BytesIO(doc_bytes))
        
        properties = {
            'styles': [],
            'margins': {},
            'sections': [],
            'has_headers': False,
            'has_footers': False,
            'theme_fonts': {},
            'paragraph_styles_used': {},
            'list_styles': []
        }
        
        try:
            # Get available styles
            properties['styles'] = [style.name for style in doc.styles]
            
            # Get paragraph styles actually used in document
            for para in doc.paragraphs:
                if para.style and para.style.name:
                    style_name = para.style.name
                    properties['paragraph_styles_used'][style_name] = properties['paragraph_styles_used'].get(style_name, 0) + 1
            
            # Identify list styles
            for style_name in properties['styles']:
                if 'List' in style_name or 'Bullet' in style_name:
                    properties['list_styles'].append(style_name)
            
            # Get section properties
            for i, section in enumerate(doc.sections):
                section_info = {
                    'index': i,
                    'page_width': section.page_width.inches if section.page_width else None,
                    'page_height': section.page_height.inches if section.page_height else None,
                    'top_margin': section.top_margin.inches if section.top_margin else None,
                    'bottom_margin': section.bottom_margin.inches if section.bottom_margin else None,
                    'left_margin': section.left_margin.inches if section.left_margin else None,
                    'right_margin': section.right_margin.inches if section.right_margin else None,
                    'has_header': bool(section.header),
                    'has_footer': bool(section.footer),
                }
                properties['sections'].append(section_info)
                
                if section.header:
                    properties['has_headers'] = True
                if section.footer:
                    properties['has_footers'] = True
                
        except Exception as e:
            properties['error'] = str(e)
        
        return properties
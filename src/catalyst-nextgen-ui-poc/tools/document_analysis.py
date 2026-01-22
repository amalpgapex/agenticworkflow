
from typing import Dict, Any, Optional, Callable, List
from tools.base import AgenticTool
import re

class DocumentAnalysisTool(AgenticTool):
    """Analyze document for specific patterns or information"""

    def __init__(self):
        super().__init__("document_analysis", "Extract specific information from document")

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Analyze document based on analysis type"""
        document_content = context.get('document_content', '')
        analysis_type = context.get('analysis_type', 'summary')

        if streaming_callback:
            streaming_callback(f"Analyzing document ({analysis_type})...")

        results = []

        if analysis_type == 'extract_numbers':
            numbers = re.findall(r'\b\d+(?:\.\d+)?%?\b', document_content)
            results.append(f"**Numbers found:** {', '.join(numbers[:20])}")

        elif analysis_type == 'extract_dates':
            dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b', document_content)
            results.append(f"**Dates found:** {', '.join(dates)}")

        elif analysis_type == 'extract_emails':
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', document_content)
            results.append(f"**Emails found:** {', '.join(emails)}")

        elif analysis_type == 'extract_urls':
            urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', document_content)
            results.append(f"**URLs found:** {', '.join(urls[:10])}")

        elif analysis_type == 'word_count':
            words = document_content.split()
            results.append(f"**Word count:** {len(words)}")
            results.append(f"**Character count:** {len(document_content)}")
            results.append(f"**Paragraph count:** {len(document_content.split(chr(10)+chr(10)))}")

        elif analysis_type == 'extract_headings':
            lines = document_content.split('\n')
            headings = [line.strip() for line in lines
                        if line.strip() and len(line.strip()) < 80
                        and line.strip().istitle()]
            results.append(f"**Headings found:**\n" + '\n'.join(f"- {h}" for h in headings[:15]))

        else:
            words = document_content.split()
            results.append(f"**Document Stats:**")
            results.append(f"- Word count: {len(words)}")
            results.append(f"- Character count: {len(document_content)}")
            results.append(f"- First 50 words: {' '.join(words[:50])}...")

        output = '\n'.join(results)

        if streaming_callback:
            streaming_callback(output)

        return output

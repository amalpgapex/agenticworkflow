
from typing import Dict, Any, Optional, Callable
from tools.base import AgenticTool
import re

class DataValidationTool(AgenticTool):
    """Validate data formats and check for errors"""

    def __init__(self):
        super().__init__("data_validation", "Validate data and check for errors")

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Validate data in previous output"""
        previous_output = context.get('previous_output', '')
        validation_type = context.get('validation_type', 'all')

        if streaming_callback:
            streaming_callback("Validating data...")

        issues = []

        if validation_type in ['all', 'links']:
            urls = re.findall(r'https?://\S+', previous_output)
            if urls:
                issues.append(f"**Links found:** {len(urls)} URLs detected (manual verification recommended)")

        if validation_type in ['all', 'dates']:
            dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', previous_output)
            if dates:
                issues.append(f"**Dates found:** {len(dates)} dates (verify format consistency)")

        if validation_type in ['all', 'emails']:
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', previous_output)
            if emails:
                issues.append(f"**Emails found:** {len(emails)} email addresses")

        if validation_type in ['all', 'spelling']:
            common_errors = ['teh ', 'recieve', 'occured', 'thier', 'definately']
            found_errors = [error for error in common_errors if error in previous_output.lower()]
            if found_errors:
                issues.append(f"**Potential spelling errors:** {', '.join(found_errors)}")

        if validation_type in ['all', 'formatting']:
            has_bullets = bool(re.search(r'^[•\-\*]\s', previous_output, re.MULTILINE))
            has_numbers = bool(re.search(r'^\d+\.\s', previous_output, re.MULTILINE))
            if has_bullets and has_numbers:
                issues.append("**Formatting note:** Mixed list formats detected (bullets and numbers)")

        output = "**Validation Report:**\n\n" + '\n'.join(issues) if issues else "**Validation Report:**\n\nNo issues detected."

        if streaming_callback:
            streaming_callback(output)

        return output

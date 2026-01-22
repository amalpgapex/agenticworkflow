
from typing import Dict, Any, Optional, Callable
from tools.base import AgenticTool
from langchain_openai import ChatOpenAI

class UpdateDerivativeTool(AgenticTool):
    """Create updated derivative based on changes to primary document"""

    def __init__(self, api_key: str):
        super().__init__("update_derivative", "Generate updated derivative document based on primary changes")
        self.llm = ChatOpenAI(
            model="gpt-5",
            temperature=0.7,
            api_key=api_key,
            streaming=True
        )

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Generate updated derivative document"""
        try:
            labeled_docs = context.get('labeled_documents', {})
            previous_output = context.get('previous_output', '')
            original_primary = labeled_docs.get('original_primary', {}).get('content', '')
            current_derivative = labeled_docs.get('current_derivative', {}).get('content', '')
            updated_primary = labeled_docs.get('updated_primary', {}).get('content', '')

            if not all([original_primary, current_derivative, updated_primary]):
                return "Error: All three documents required (original primary, current derivative, updated primary)"

            if streaming_callback:
                streaming_callback("📝 Analyzing transformation patterns and applying updates...")

            # Build comprehensive prompt
            update_prompt = f"""You are updating a derivative document to reflect changes in the primary source document.

**Context:**

1. **Original Primary Document** (the source that the derivative was originally based on):
{original_primary[:2000]}

2. **Current Derivative Document** (the derivative we need to update):
{current_derivative[:2000]}

3. **Updated Primary Document** (the new version of the primary with changes):
{updated_primary[:2000]}

4. **Analysis of How Derivative Was Created** (your guide for maintaining consistency):
{previous_output[:1500]}

**Your Task:**

Create an updated version of the Current Derivative Document that:

1. **Maintains the transformation pattern** - Apply the same type of transformation that was used to create the original derivative
2. **Incorporates all changes** - Reflect all relevant changes from the Updated Primary Document
3. **Preserves structure** - Keep the same structural approach (headings, lists, format)
4. **Maintains tone & style** - Use the same tone, style, and target audience as the original derivative
5. **Removes outdated content** - Remove or update content that's no longer accurate based on the changes
6. **Adds new content** - Include new information from the Updated Primary where appropriate
7. **Stays consistent** - Apply the same rules and patterns that governed the original transformation

**Guidelines:**
- If the original derivative was a summary, create a summary of the updated primary
- If it was an FAQ, update the questions and answers to reflect changes
- If it was a checklist, update the checklist items
- Preserve the same level of detail and depth
- Use the same formatting conventions

Provide ONLY the updated derivative document (no meta-commentary):

"""

            # Stream the generated derivative
            full_response = ""
            for chunk in self.llm.stream(update_prompt):
                token = chunk.content
                full_response += token
                if streaming_callback:
                    streaming_callback(full_response)
            
            return full_response
            
        except Exception as e:
            error_msg = f"**Update derivative error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg
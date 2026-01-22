
from typing import Dict, Any, Optional, Callable
from tools.base import AgenticTool
from langchain_openai import ChatOpenAI
from openai import OpenAI

class DerivativeAnalysisTool(AgenticTool):
    """Analyze how a derivative document was created from an original, using GPT-5 with reasoning"""

    def __init__(self, api_key: str):
        super().__init__("derivative_analysis", "Deep analysis of derivative document creation using GPT-5 with reasoning")
        self.client = OpenAI(api_key=api_key)
        self.regular_llm = ChatOpenAI(model="gpt-5-mini", temperature=0.7, api_key=api_key, streaming=True)

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Perform deep analysis of how derivative was created from original"""
        try:
            labeled_docs = context.get('labeled_documents', {})
            original_content = labeled_docs.get('original_primary', {}).get('content', '')
            derivative_content = labeled_docs.get('current_derivative', {}).get('content', '')

            if not original_content or not derivative_content:
                return "Error: Original and derivative documents required for analysis"

            if streaming_callback:
                streaming_callback("🧠 Starting deep reasoning analysis with GPT-5...\n\n(verbosity: medium, reasoning_effort: medium)\n\nAnalyzing transformation patterns...")

            analysis_prompt = f"""You are analyzing how a derivative document was created from an original document.

Original Document:
{original_content[:3000]}

Derivative Document:
{derivative_content[:3000]}

Perform a comprehensive analysis and identify:

1. **Transformation Type**: What type of derivative is this? (summary, FAQ, checklist, translation, simplification, etc.)

2. **Content Preservation**: What content from the original was kept exactly or substantially?

3. **Content Modification**: What content was modified, and how? (rephrased, reorganized, condensed, expanded)

4. **Content Removal**: What was removed from the original, and why might it have been removed?

5. **Content Addition**: What new content was added that wasn't in the original?

6. **Structural Changes**: How was the document structure changed? (headings, lists, sections, format)

7. **Tone & Style**: How did the tone, style, or target audience change?

8. **Key Patterns**: What patterns or rules seem to govern this transformation?

Provide your analysis in a structured format."""

            analysis = ""
            try:
                response = self.client.chat.completions.create(
                    model="gpt-5",
                    messages=[{"role": "developer", "content": [{"type": "text", "text": analysis_prompt}]}],
                    response_format={"type": "text"},
                    verbosity="medium",
                    reasoning_effort="medium",
                    stream=True
                )

                for chunk in response:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if not delta:
                        continue
                    content = getattr(delta, "content", None)

                    if isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text = part.get("text", "")
                                analysis += text
                                if streaming_callback:
                                    streaming_callback(f"🧠 Analysis:\n\n{analysis}")
                    elif isinstance(content, str):
                        analysis += content
                        if streaming_callback:
                            streaming_callback(f"🧠 Analysis:\n\n{analysis}")

            except Exception as api_error:
                print(f"GPT-5 streaming error: {api_error}")
                if streaming_callback:
                    streaming_callback(f"⚠️ GPT-5 not available, using GPT-4o...\n\n")
                for chunk in self.regular_llm.stream(analysis_prompt):
                    token = chunk.content
                    analysis += token
                    if streaming_callback:
                        streaming_callback(f"🧠 Analysis:\n\n{analysis}")

            if streaming_callback:
                streaming_callback(f"✅ Deep analysis complete!\n\n---\n\n{analysis}")

            return analysis

        except Exception as e:
            error_msg = f"**Derivative analysis error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg

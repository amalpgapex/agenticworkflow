
from typing import Dict, Any, Optional, Callable
from tools.base import AgenticTool
from tools.web_search import WebSearchTool
from langchain_openai import ChatOpenAI
from openai import OpenAI

class ContentEnrichmentTool(AgenticTool):
    """Enrich content with additional context from web"""

    def __init__(self, api_key: str):
        super().__init__("content_enrichment", "Add context and details from web sources")
        self.client = OpenAI(api_key=api_key)
        self.primary_model = "gpt-5-mini"
        self.llm_fallback = ChatOpenAI(model="gpt-4o-mini", api_key=api_key)
        self.web_search = WebSearchTool()

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Enrich content with web research"""
        previous_output = context.get('previous_output', '')
        enrichment_topic = context.get('enrichment_topic', '')

        try:
            accumulated_output = f"**Content Enrichment Started**\n\nResearching topic: {enrichment_topic}...\n"
            if streaming_callback:
                streaming_callback(accumulated_output)

            search_result = self.web_search.execute({'search_query': enrichment_topic, 'max_results': 5})

            accumulated_output += "\nResearch complete. Integrating findings...\n\n---\n\n"
            if streaming_callback:
                streaming_callback(accumulated_output)

            enrich_prompt = f"""You are enriching the following content with additional context from web research.

Original Content:
{previous_output}

Research Results:
{search_result}

Please create an enriched version that:
1. Keeps all original content
2. Adds relevant facts and context from research
3. Cites sources when adding new information
4. Maintains the original tone and format

Enriched Content:"""

            enriched_content = ""
            try:
                response = self.client.chat.completions.create(
                    model=self.primary_model,
                    messages=[{"role": "user", "content": enrich_prompt}],
                    response_format={"type": "text"},
                    verbosity="medium",
                    reasoning_effort="low",
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
                                enriched_content += text
                                full_output = accumulated_output + enriched_content
                                if streaming_callback:
                                    streaming_callback(full_output)
                    elif isinstance(content, str):
                        enriched_content += content
                        full_output = accumulated_output + enriched_content
                        if streaming_callback:
                            streaming_callback(full_output)

                return accumulated_output + enriched_content

            except Exception as e:
                print(f"GPT-5-mini enrichment error: {e}")
                enriched_content = ""
                for chunk in self.llm_fallback.stream(enrich_prompt):
                    enriched_content += chunk.content
                    full_output = accumulated_output + enriched_content
                    if streaming_callback:
                        streaming_callback(full_output)
                return accumulated_output + enriched_content

        except Exception as e:
            error_msg = f"**Content enrichment error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg

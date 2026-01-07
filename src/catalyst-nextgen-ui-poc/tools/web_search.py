
from typing import Dict, Any, Optional, Callable
from tools.base import AgenticTool
import requests

class WebSearchTool(AgenticTool):
    """Web search using DuckDuckGo or similar API"""

    def __init__(self):
        super().__init__("web_search", "Search the web for information")

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Execute web search"""
        query = context.get('search_query', '')
        max_results = context.get('max_results', 5)

        try:
            if streaming_callback:
                streaming_callback(f"Searching web for: {query}...")

            url = f"https://api.duckduckgo.com/?q={query}&format=json"
            response = requests.get(url, timeout=10)
            data = response.json()

            results = []
            if data.get('Abstract'):
                results.append(f"**Summary:** {data['Abstract']}")
                if data.get('AbstractSource'):
                    results.append(f"*Source: {data['AbstractSource']}*")

            if data.get('RelatedTopics'):
                results.append("\n**Related Information:**")
                for i, topic in enumerate(data['RelatedTopics'][:max_results]):
                    if isinstance(topic, dict) and topic.get('Text'):
                        results.append(f"{i+1}. {topic['Text']}")

            output = "\n".join(results) if results else "No results found."

            if streaming_callback:
                streaming_callback(output)

            return output

        except Exception as e:
            error_msg = f"Web search failed: {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg

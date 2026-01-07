
from typing import Dict, Any, Optional, Callable, List
from tools.base import AgenticTool
from tools.web_search import WebSearchTool
from langchain_openai import ChatOpenAI
from openai import OpenAI

class FactCheckTool(AgenticTool):
    """Verify claims against web sources (using LLM + Web Search)"""

    def __init__(self, api_key: str):
        super().__init__("fact_check", "Verify factual claims")
        self.client = OpenAI(api_key=api_key)
        self.primary_model = "gpt-5-mini"
        self.llm_fallback = ChatOpenAI(model="gpt-5-mini", api_key=api_key)
        self.web_search = WebSearchTool()

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Fact check claims from previous output"""
        previous_output = context.get('previous_output', '')

        if not previous_output:
            error_msg = "No content to fact-check (previous output is empty)"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg

        try:
            accumulated_output = "**Fact-Checking Process Started**\n\nExtracting claims to verify..."
            if streaming_callback:
                streaming_callback(accumulated_output)

            extract_prompt = f"""From the following text, extract 3-5 key factual claims that should be verified.
List each claim on a new line starting with "CLAIM:".

Text:
{previous_output}

Claims:"""

            claims_text = ""
            try:
                response = self.client.chat.completions.create(
                    model=self.primary_model,
                    messages=[{"role": "user", "content": extract_prompt}],
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
                                claims_text += part.get("text", "")
                    elif isinstance(content, str):
                        claims_text += content
            except Exception as e:
                print(f"GPT-5-mini claim extraction error: {e}")
                for chunk in self.llm_fallback.stream(extract_prompt):
                    claims_text += chunk.content

            claims = [line.replace('CLAIM:', '').strip()
                      for line in claims_text.split('\n')
                      if line.strip().startswith('CLAIM:')]

            if not claims:
                no_claims_msg = "**No verifiable claims found in the content.**"
                if streaming_callback:
                    streaming_callback(no_claims_msg)
                return no_claims_msg

            accumulated_output += f"\n\nFound {len(claims)} claims to verify.\n\n**Fact Check Results:**\n"
            if streaming_callback:
                streaming_callback(accumulated_output)

            results = []

            for i, claim in enumerate(claims[:3], 1):
                accumulated_output += f"\n**Claim {i}/{min(len(claims), 3)}:** {claim}\n"
                if streaming_callback:
                    streaming_callback(accumulated_output)

                accumulated_output += "Searching for evidence...\n"
                if streaming_callback:
                    streaming_callback(accumulated_output)

                search_result = self.web_search.execute({'search_query': claim, 'max_results': 3})

                accumulated_output += "Analyzing verdict...\n"
                if streaming_callback:
                    streaming_callback(accumulated_output)

                verify_prompt = f"""Based on this search result, is the following claim likely TRUE, FALSE, or UNCERTAIN?

Claim: {claim}

Search Result:
{search_result}

Answer with just: TRUE, FALSE, or UNCERTAIN, followed by a brief explanation."""

                verdict = ""
                try:
                    verify_response = self.client.chat.completions.create(
                        model=self.primary_model,
                        messages=[{"role": "user", "content": verify_prompt}],
                        response_format={"type": "text"},
                        verbosity="medium",
                        reasoning_effort="low",
                        stream=True
                    )

                    for chunk in verify_response:
                        if not chunk.choices:
                            continue
                        delta = chunk.choices[0].delta
                        if not delta:
                            continue
                        content = getattr(delta, "content", None)
                        if isinstance(content, list):
                            for part in content:
                                if isinstance(part, dict) and part.get("type") == "text":
                                    verdict += part.get("text", "")
                                    temp_output = accumulated_output + f"**Verdict:** {verdict}"
                                    if streaming_callback:
                                        streaming_callback(temp_output)
                        elif isinstance(content, str):
                            verdict += content
                            temp_output = accumulated_output + f"**Verdict:** {verdict}"
                            if streaming_callback:
                                streaming_callback(temp_output)
                except Exception as e:
                    print(f"GPT-5-mini verdict error: {e}")
                    for chunk in self.llm_fallback.stream(verify_prompt):
                        verdict += chunk.content
                        temp_output = accumulated_output + f"**Verdict:** {verdict}"
                        if streaming_callback:
                            streaming_callback(temp_output)

                accumulated_output += f"**Verdict:** {verdict}\n"
                if streaming_callback:
                    streaming_callback(accumulated_output)

                results.append(f"\n**Claim {i}:** {claim}")
                results.append(f"**Verdict:** {verdict}")

            output = accumulated_output + "\n**Fact-Checking Complete!**"
            if streaming_callback:
                streaming_callback(output)
            return output

        except Exception as e:
            error_msg = f"**Fact-check error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg

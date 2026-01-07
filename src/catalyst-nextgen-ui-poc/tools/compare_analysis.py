
from typing import Dict, Any, Optional, Callable
from tools.base import AgenticTool
from langchain_openai import ChatOpenAI
from openai import OpenAI
import json

class CompareAnalysisTool(AgenticTool):
    """Analyze differences between aligned Excel pairs using LLM"""

    def __init__(self, api_key: str):
        super().__init__("compare_analysis", "Generate AI descriptions of differences between aligned pairs")
        self.client = OpenAI(api_key=api_key)
        self.llm_fallback = ChatOpenAI(model="gpt-5-mini", temperature=0.7, api_key=api_key, streaming=True)

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Analyze alignment results and add AI-generated analysis column"""
        previous_output = context.get('previous_output', '')

        if not previous_output or not previous_output.startswith('ALIGNMENT_RESULT:'):
            return "Error: No alignment data found in previous step"

        try:
            json_data = previous_output.replace('ALIGNMENT_RESULT:', '').strip()
            alignment_result = json.loads(json_data)

            all_pairs = alignment_result.get('unified_pairs', alignment_result.get('matched_pairs', []))
            matched_pairs = [p for p in all_pairs if p.get('is_matched', True)]

            file1_col = alignment_result.get('file1_column', 'File 1')
            file2_col = alignment_result.get('file2_column', 'File 2')

            if not matched_pairs:
                return "No matched pairs found to compare."

            if streaming_callback:
                streaming_callback(f"🔍 Analyzing {len(matched_pairs)} matched pairs...\n\n")

            analyzed_count = 0
            for idx, pair in enumerate(all_pairs):
                if pair.get('is_matched') is False:
                    continue

                analyzed_count += 1
                text1 = pair.get('file1_value', '')
                text2 = pair.get('file2_value', '')
                similarity = pair.get('similarity', 0)

                if streaming_callback:
                    streaming_callback(f"🔍 Analyzing pair {analyzed_count}/{len(matched_pairs)}...\n\n")

                pair_prompt = f"""Compare these two text values and briefly describe the key differences in 1-2 concise sentences.
Focus on meaningful changes, not trivial wording differences.

Value from {file1_col}: {text1}

Value from {file2_col}: {text2}

Similarity score: {similarity:.1%}

Brief description of differences:"""

                try:
                    response = self.client.chat.completions.create(
                        model="gpt-5-mini",
                        messages=[{"role": "user", "content": pair_prompt}],
                        response_format={"type": "text"},
                        verbosity="low",
                        reasoning_effort="low"
                    )
                    analysis = response.choices[0].message.content.strip() if response.choices else ""
                except Exception as e:
                    print(f"GPT-5-mini comparison error for pair {analyzed_count}: {e}")
                    resp = self.llm_fallback.invoke(pair_prompt)
                    analysis = resp.content.strip()

                pair['analysis'] = analysis

            alignment_result['has_analysis'] = True

            if 'unified_pairs' in alignment_result:
                alignment_result['unified_pairs'] = all_pairs
            else:
                alignment_result['matched_pairs'] = [p for p in all_pairs if p.get('is_matched', True)]

            output = f"ALIGNMENT_RESULT:{json.dumps(alignment_result)}"

            if streaming_callback:
                streaming_callback(f"✅ Comparison analysis complete for all {analyzed_count} pairs!")

            return output

        except Exception as e:
            error_msg = f"**Compare analysis error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg

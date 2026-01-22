
from typing import Dict, Any, Optional, Callable
from tools.base import AgenticTool
from langchain_openai import ChatOpenAI
from openai import OpenAI

class LLMPromptTool(AgenticTool):
    """Standard LLM prompt execution"""

    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        super().__init__("llm_prompt", "Execute an LLM prompt")
        # Primary: GPT-5 via direct OpenAI client (supports verbosity / reasoning parameters)
        self.client = OpenAI(api_key=api_key)
        self.primary_model = "gpt-5-mini"
        # Fallback model if GPT-5 call fails
        self.fallback_llm = ChatOpenAI(
            model=model,
            temperature=0.7,
            api_key=api_key,
            streaming=True
        )

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Execute LLM prompt with streaming support"""
        prompt = context.get('prompt', '')
        document_content = context.get('document_content', '')
        previous_output = context.get('previous_output', '')
        template_variables = context.get('template_variables', [])
        user_options = context.get('user_options', {})
        labeled_documents = context.get('labeled_documents', {})
        step_history = context.get('step_history', [])

        formatted_prompt = prompt.replace('{document_content}', document_content)
        formatted_prompt = formatted_prompt.replace('{previous_output}', previous_output)

        for var in template_variables:
            placeholder = f'{{{var}}}'
            if placeholder in formatted_prompt and var in user_options:
                formatted_prompt = formatted_prompt.replace(placeholder, str(user_options[var]))

        for key, value in user_options.items():
            placeholder = f'{{{key}}}'
            if placeholder in formatted_prompt:
                formatted_prompt = formatted_prompt.replace(placeholder, str(value))

        if labeled_documents:
            for label_key, doc_info in labeled_documents.items():
                if isinstance(doc_info, dict) and 'content' in doc_info:
                    placeholder = f'{{labeled_documents.{label_key}.content}}'
                    if placeholder in formatted_prompt:
                        formatted_prompt = formatted_prompt.replace(placeholder, doc_info['content'])

        if step_history:
            for idx, step_data in enumerate(step_history):
                placeholder = f'{{current_state.step_outputs[{idx}].output}}'
                if placeholder in formatted_prompt:
                    formatted_prompt = formatted_prompt.replace(placeholder, step_data.get('output', ''))

        full_response = ""
        try:
            if streaming_callback:
                response = self.client.chat.completions.create(
                    model=self.primary_model,
                    messages=[{"role": "user", "content": formatted_prompt}],
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
                                full_response += text
                                streaming_callback(full_response)
                    elif isinstance(content, str):
                        full_response += content
                        streaming_callback(full_response)
            else:
                response = self.client.chat.completions.create(
                    model=self.primary_model,
                    messages=[{"role": "user", "content": formatted_prompt}],
                    response_format={"type": "text"},
                    verbosity="medium",
                    reasoning_effort="low"
                )
                if response.choices:
                    full_response = response.choices[0].message.content
                else:
                    full_response = ""
        except Exception as gpt5_error:
            print(f"GPT-5 prompt error: {gpt5_error}")
            if streaming_callback:
                streaming_callback("⚠️ GPT-5 unavailable, falling back to GPT-4o-mini...\n\n")
                for chunk in self.fallback_llm.stream(formatted_prompt):
                    token = chunk.content
                    full_response += token
                    streaming_callback(full_response)
            else:
                fallback_response = self.fallback_llm.invoke(formatted_prompt)
                full_response = fallback_response.content

        return full_response

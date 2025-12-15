"""
Agentic Tools for Document Transformation
Provides various tool types beyond LLM prompts for enhanced agentic workflows
"""

from typing import Dict, Any, Optional, Callable, List
import os
import json
import re
from datetime import datetime
import requests
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from openai import OpenAI
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.optimize import linear_sum_assignment
import difflib


class AgenticTool:
    """Base class for agentic tools"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Execute the tool with given context"""
        raise NotImplementedError


class LLMPromptTool(AgenticTool):
    """Standard LLM prompt execution"""
    
    def __init__(self, api_key: str, model: str = "gpt-5-mini"):
        super().__init__("llm_prompt", "Execute an LLM prompt")
        from openai import AzureOpenAI
        # Primary: GPT-5 via direct OpenAI client (supports verbosity / reasoning parameters)
        self.client = AzureOpenAI(api_key=api_key)
        self.primary_model = "gpt-5-mini"
        # Fallback model if GPT-5 call fails
        self.fallback_llm = AzureChatOpenAI(
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
        
        # Format prompt with base variables
        formatted_prompt = prompt.replace('{document_content}', document_content)
        formatted_prompt = formatted_prompt.replace('{previous_output}', previous_output)
        
        # Substitute any user option placeholders in the prompt
        for var in template_variables:
            placeholder = f'{{{var}}}'
            if placeholder in formatted_prompt and var in user_options:
                formatted_prompt = formatted_prompt.replace(placeholder, str(user_options[var]))
        
        # For robustness, also replace any remaining placeholders with user options if they exist
        for key, value in user_options.items():
            placeholder = f'{{{key}}}'
            if placeholder in formatted_prompt:
                formatted_prompt = formatted_prompt.replace(placeholder, str(value))
        
        # Inject labeled documents if placeholders are present
        if labeled_documents:
            for label_key, doc_info in labeled_documents.items():
                if isinstance(doc_info, dict) and 'content' in doc_info:
                    placeholder = f'{{labeled_documents.{label_key}.content}}'
                    if placeholder in formatted_prompt:
                        formatted_prompt = formatted_prompt.replace(placeholder, doc_info['content'])

        # Inject step history references if requested (e.g., {step_outputs[1].output})
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
                    messages=[
                        {
                            "role": "user",
                            "content": formatted_prompt
                        }
                    ],
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
                    messages=[
                        {
                            "role": "user",
                            "content": formatted_prompt
                        }
                    ],
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


class WebSearchTool(AgenticTool):
    """Web search using DuckDuckGo or similar API"""
    
    def __init__(self):
        super().__init__("web_search", "Search the web for information")
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Execute web search"""
        query = context.get('search_query', '')
        max_results = context.get('max_results', 5)
        
        # Use DuckDuckGo instant answer API (free, no key needed)
        try:
            if streaming_callback:
                streaming_callback(f"Searching web for: {query}...")
            
            # DuckDuckGo instant answer
            url = f"https://api.duckduckgo.com/?q={query}&format=json"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            results = []
            
            # Get abstract
            if data.get('Abstract'):
                results.append(f"**Summary:** {data['Abstract']}")
                if data.get('AbstractSource'):
                    results.append(f"*Source: {data['AbstractSource']}*")
            
            # Get related topics
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
            # Extract all numbers and statistics
            numbers = re.findall(r'\b\d+(?:\.\d+)?%?\b', document_content)
            results.append(f"**Numbers found:** {', '.join(numbers[:20])}")
        
        elif analysis_type == 'extract_dates':
            # Extract dates
            dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b', document_content)
            results.append(f"**Dates found:** {', '.join(dates)}")
        
        elif analysis_type == 'extract_emails':
            # Extract email addresses
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', document_content)
            results.append(f"**Emails found:** {', '.join(emails)}")
        
        elif analysis_type == 'extract_urls':
            # Extract URLs
            urls = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', document_content)
            results.append(f"**URLs found:** {', '.join(urls[:10])}")
        
        elif analysis_type == 'word_count':
            # Word count analysis
            words = document_content.split()
            results.append(f"**Word count:** {len(words)}")
            results.append(f"**Character count:** {len(document_content)}")
            results.append(f"**Paragraph count:** {len(document_content.split(chr(10)+chr(10)))}")
        
        elif analysis_type == 'extract_headings':
            # Extract potential headings (short lines, title case)
            lines = document_content.split('\n')
            headings = [line.strip() for line in lines 
                       if line.strip() and len(line.strip()) < 80 
                       and line.strip().istitle()]
            results.append(f"**Headings found:**\n" + '\n'.join(f"- {h}" for h in headings[:15]))
        
        else:
            # Default: basic summary
            words = document_content.split()
            results.append(f"**Document Stats:**")
            results.append(f"- Word count: {len(words)}")
            results.append(f"- Character count: {len(document_content)}")
            results.append(f"- First 50 words: {' '.join(words[:50])}...")
        
        output = '\n'.join(results)
        
        if streaming_callback:
            streaming_callback(output)
        
        return output


class FactCheckTool(AgenticTool):
    """Verify claims against web sources (using LLM + Web Search)"""
    
    def __init__(self, api_key: str):
        super().__init__("fact_check", "Verify factual claims")
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.primary_model = "gpt-5-mini"
        self.llm_fallback = AzureChatOpenAI(model="gpt-5-mini", api_key=api_key)
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
            # Build output progressively
            accumulated_output = "**Fact-Checking Process Started**\n\nExtracting claims to verify..."
            if streaming_callback:
                streaming_callback(accumulated_output)
            
            # Step 1: Extract claims using GPT-5-mini with streaming
            extract_prompt = f"""From the following text, extract 3-5 key factual claims that should be verified.
List each claim on a new line starting with "CLAIM:".

Text:
{previous_output}

Claims:"""
            
            # Use streaming for claim extraction
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
                # Fallback uses GPT-4o-mini
            
            claims = [line.replace('CLAIM:', '').strip() 
                     for line in claims_text.split('\n') 
                     if line.strip().startswith('CLAIM:')]
            
            if not claims:
                no_claims_msg = "**No verifiable claims found in the content.**"
                if streaming_callback:
                    streaming_callback(no_claims_msg)
                return no_claims_msg
            
            # Update output with found claims
            accumulated_output += f"\n\nFound {len(claims)} claims to verify.\n\n**Fact Check Results:**\n"
            if streaming_callback:
                streaming_callback(accumulated_output)
            
            results = []
            
            # Step 2: Search and verify each claim
            for i, claim in enumerate(claims[:3], 1):
                accumulated_output += f"\n**Claim {i}/{min(len(claims), 3)}:** {claim}\n"
                if streaming_callback:
                    streaming_callback(accumulated_output)
                
                # Search for evidence
                accumulated_output += "Searching for evidence...\n"
                if streaming_callback:
                    streaming_callback(accumulated_output)
                
                search_result = self.web_search.execute({
                    'search_query': claim,
                    'max_results': 3
                })
                
                accumulated_output += "Analyzing verdict...\n"
                if streaming_callback:
                    streaming_callback(accumulated_output)
                
                # Analyze with GPT-5-mini using streaming
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
                
                # Finalize this claim's output
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


class ContentEnrichmentTool(AgenticTool):
    """Enrich content with additional context from web"""
    
    def __init__(self, api_key: str):
        super().__init__("content_enrichment", "Add context and details from web sources")
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.primary_model = "gpt-5-mini"
        self.llm_fallback = AzureChatOpenAI(model="gpt-4o-mini", api_key=api_key)
        self.web_search = WebSearchTool()
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Enrich content with web research"""
        previous_output = context.get('previous_output', '')
        enrichment_topic = context.get('enrichment_topic', '')
        
        try:
            # Build output progressively
            accumulated_output = f"**Content Enrichment Started**\n\nResearching topic: {enrichment_topic}...\n"
            if streaming_callback:
                streaming_callback(accumulated_output)
            
            # Search for additional information
            search_result = self.web_search.execute({
                'search_query': enrichment_topic,
                'max_results': 5
            })
            
            accumulated_output += "\nResearch complete. Integrating findings...\n\n---\n\n"
            if streaming_callback:
                streaming_callback(accumulated_output)
            
            # Use LLM to integrate findings with streaming
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
            
            # Stream the enriched content as it's generated
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
        
        # Check for broken links
        if validation_type in ['all', 'links']:
            urls = re.findall(r'https?://\S+', previous_output)
            if urls:
                issues.append(f"**Links found:** {len(urls)} URLs detected (manual verification recommended)")
        
        # Check for inconsistent dates
        if validation_type in ['all', 'dates']:
            dates = re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', previous_output)
            if dates:
                issues.append(f"**Dates found:** {len(dates)} dates (verify format consistency)")
        
        # Check for email format
        if validation_type in ['all', 'emails']:
            emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', previous_output)
            if emails:
                issues.append(f"**Emails found:** {len(emails)} email addresses")
        
        # Check for common errors
        if validation_type in ['all', 'spelling']:
            common_errors = ['teh ', 'recieve', 'occured', 'thier', 'definately']
            found_errors = [error for error in common_errors if error in previous_output.lower()]
            if found_errors:
                issues.append(f"**Potential spelling errors:** {', '.join(found_errors)}")
        
        # Check for inconsistent formatting
        if validation_type in ['all', 'formatting']:
            # Check for mixed list formats
            has_bullets = bool(re.search(r'^[•\-\*]\s', previous_output, re.MULTILINE))
            has_numbers = bool(re.search(r'^\d+\.\s', previous_output, re.MULTILINE))
            if has_bullets and has_numbers:
                issues.append("**Formatting note:** Mixed list formats detected (bullets and numbers)")
        
        output = "**Validation Report:**\n\n" + '\n'.join(issues) if issues else "**Validation Report:**\n\nNo issues detected."
        
        if streaming_callback:
            streaming_callback(output)
        
        return output


class PodcastGeneratorTool(AgenticTool):
    """Generate audio podcast from text using OpenAI TTS"""
    
    def __init__(self, api_key: str):
        super().__init__("podcast_generator", "Generate audio podcast from text")
        self.client = OpenAI(api_key=api_key)
        self.output_dir = Path("generated_audio")
        self.output_dir.mkdir(exist_ok=True)
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Generate podcast audio from text"""
        # Get the podcast script (from previous step or document)
        script = context.get('previous_output', context.get('document_content', ''))
        
        if not script or len(script.strip()) < 10:
            return "Error: No content available to convert to speech"
        
        if streaming_callback:
            streaming_callback("🎙️ Preparing podcast script for audio generation...")
        
        try:
            # Get voice preference from parameters (default: alloy)
            voice = context.get('parameters', {}).get('voice', 'alloy')
            # Available voices: alloy, echo, fable, onyx, nova, shimmer
            
            if streaming_callback:
                streaming_callback(f"🎙️ Generating podcast audio with voice: {voice}...")
            
            # Generate timestamp-based filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"podcast_{timestamp}.mp3"
            audio_path = self.output_dir / audio_filename
            
            # Call OpenAI TTS API
            response = self.client.audio.speech.create(
                model="tts-1",  # or "tts-1-hd" for higher quality
                voice=voice,
                input=script[:4096]  # TTS API has character limit
            )
            
            # Save audio file
            response.stream_to_file(str(audio_path))
            
            if streaming_callback:
                streaming_callback(f"✅ Podcast audio generated successfully!\n\nAudio file: {audio_filename}\nVoice: {voice}\nDuration: ~{len(script) // 150} seconds (estimated)")
            
            # Return the relative path to the audio file
            return f"AUDIO_FILE:{audio_filename}"
            
        except Exception as e:
            error_msg = f"Error generating podcast audio: {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg


class AlignmentTool(AgenticTool):
    """Align items from two Excel files using OpenAI embeddings and Hungarian algorithm"""
    
    def __init__(self, api_key: str):
        super().__init__("alignment", "Align items from two Excel files using semantic matching")
        self.embeddings = AzureOpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=api_key
        )
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Execute alignment between two Excel files"""
        try:
            # Get file paths from context
            file1_path = context.get('file1_path')
            file2_path = context.get('file2_path')
            
            # Get column selections from user options
            user_options = context.get('user_options', {})
            
            # Parse column selections - they come as strings from frontend
            column1_str = user_options.get('column1', '0')
            column2_str = user_options.get('column2', '0')
            
            # Convert to integers, handling empty strings
            try:
                column1 = int(column1_str) if column1_str else 0
            except (ValueError, TypeError):
                column1 = 0
            
            try:
                column2 = int(column2_str) if column2_str else 0
            except (ValueError, TypeError):
                column2 = 0
            
            include_diff = user_options.get('include_diff', 'no') == 'yes'
            
            if not file1_path or not file2_path:
                return "Error: Both Excel file paths are required"
            
            if streaming_callback:
                streaming_callback("📊 Loading Excel files...")
            
            # Read Excel files
            df1 = pd.read_excel(file1_path)
            df2 = pd.read_excel(file2_path)
            
            # Get the columns to align
            if isinstance(column1, int):
                col1_data = df1.iloc[:, column1].astype(str).tolist()
                col1_name = str(df1.columns[column1])
            else:
                col1_data = df1[column1].astype(str).tolist()
                col1_name = str(column1)
            
            if isinstance(column2, int):
                col2_data = df2.iloc[:, column2].astype(str).tolist()
                col2_name = str(df2.columns[column2])
            else:
                col2_data = df2[column2].astype(str).tolist()
                col2_name = str(column2)
            
            if streaming_callback:
                streaming_callback(f"📊 Loaded {len(col1_data)} items from file 1 and {len(col2_data)} items from file 2\n\n🔮 Generating embeddings...")
            
            # Generate embeddings
            embeddings1 = self.embeddings.embed_documents(col1_data)
            embeddings2 = self.embeddings.embed_documents(col2_data)
            
            if streaming_callback:
                streaming_callback(f"🔮 Embeddings generated\n\n🔗 Computing similarity matrix and finding optimal matches...")
            
            # Convert to numpy arrays
            emb1 = np.array(embeddings1)
            emb2 = np.array(embeddings2)
            
            # Compute cosine similarity matrix
            # Normalize embeddings
            emb1_norm = emb1 / np.linalg.norm(emb1, axis=1, keepdims=True)
            emb2_norm = emb2 / np.linalg.norm(emb2, axis=1, keepdims=True)
            
            # Similarity matrix (cosine similarity)
            similarity_matrix = np.dot(emb1_norm, emb2_norm.T)
            
            # Hungarian algorithm works with cost matrix (minimize)
            # Convert similarity to cost (1 - similarity for maximization)
            cost_matrix = 1 - similarity_matrix
            
            # Apply Hungarian algorithm
            row_indices, col_indices = linear_sum_assignment(cost_matrix)
            
            if streaming_callback:
                streaming_callback("🔗 Optimal matching complete\n\n📋 Formatting results...")
            
            # Build match lookup for quick access
            match_dict_1to2 = {}  # file1_index -> file2_index
            match_dict_2to1 = {}  # file2_index -> file1_index
            for i, j in zip(row_indices, col_indices):
                match_dict_1to2[i] = j
                match_dict_2to1[j] = i
            
            # Find orphans (unmatched items)
            matched_indices1 = set(row_indices)
            matched_indices2 = set(col_indices)
            
            # Build unified list in ORIGINAL INPUT ORDER (based on File 1)
            # Each row represents a File 1 item with its match (if any)
            unified_pairs = []
            
            for i in range(len(col1_data)):
                if i in match_dict_1to2:
                    # This item has a match
                    j = match_dict_1to2[i]
                    similarity_score = similarity_matrix[i, j]
                    
                    pair_data = {
                        'file1_index': int(i),
                        'file2_index': int(j),
                        'file1_value': col1_data[i],
                        'file2_value': col2_data[j],
                        'similarity': float(similarity_score),
                        'is_matched': True,
                        'type': 'match'
                    }
                    
                    # Calculate diff if requested
                    if include_diff:
                        diff_html = self._calculate_diff(col1_data[i], col2_data[j])
                        pair_data['diff'] = diff_html
                    
                    unified_pairs.append(pair_data)
                else:
                    # This item is unmatched (orphan from file 1)
                    unified_pairs.append({
                        'file1_index': int(i),
                        'file2_index': None,
                        'file1_value': col1_data[i],
                        'file2_value': None,
                        'similarity': 0.0,
                        'is_matched': False,
                        'type': 'orphan_file1'
                    })
            
            # Add File 2 orphans to the end with original indices preserved
            for j in range(len(col2_data)):
                if j not in matched_indices2:
                    unified_pairs.append({
                        'file1_index': None,
                        'file2_index': int(j),
                        'file1_value': None,
                        'file2_value': col2_data[j],
                        'similarity': 0.0,
                        'is_matched': False,
                        'type': 'orphan_file2'
                    })
            
            # Collect orphans from file 2 (for backward compatibility and separate display if needed)
            orphans1 = [{'index': int(i), 'value': col1_data[i]} 
                       for i in range(len(col1_data)) if i not in matched_indices1]
            orphans2 = [{'index': int(i), 'value': col2_data[i]} 
                       for i in range(len(col2_data)) if i not in matched_indices2]
            
            # Format output as JSON for the canvas to parse
            # Extract just the matched pairs for statistics
            matched_only = [p for p in unified_pairs if p['is_matched']]
            
            result = {
                'unified_pairs': unified_pairs,  # NEW: Unified list in original order
                'matched_pairs': matched_only,  # For backward compatibility
                'orphans_file1': orphans1,
                'orphans_file2': orphans2,
                'file1_column': col1_name,
                'file2_column': col2_name,
                'total_matches': len(matched_only),
                'total_orphans': len(orphans1) + len(orphans2),
                'avg_similarity': float(np.mean([p['similarity'] for p in matched_only])) if matched_only else 0.0,
                'include_diff': include_diff
            }
            
            # Return as specially formatted string that frontend can parse
            output = f"ALIGNMENT_RESULT:{json.dumps(result)}"
            
            if streaming_callback:
                streaming_callback(f"✅ Alignment complete!\n\n**Summary:**\n- {len(matched_only)} pairs matched\n- {len(orphans1)} unmatched from file 1\n- {len(orphans2)} unmatched from file 2\n- Average similarity: {result['avg_similarity']:.2%}")
            
            return output
            
        except Exception as e:
            error_msg = f"**Alignment error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg
    
    def _calculate_diff(self, text1: str, text2: str) -> str:
        """Calculate diff between two text blocks and return HTML"""
        differ = difflib.Differ()
        diff = list(differ.compare(text1.split(), text2.split()))
        
        html_parts = []
        for item in diff:
            if item.startswith('- '):
                # Deleted (redline)
                word = item[2:]
                html_parts.append(f'<span class="diff-removed">{word}</span>')
            elif item.startswith('+ '):
                # Added (greenline)
                word = item[2:]
                html_parts.append(f'<span class="diff-added">{word}</span>')
            elif item.startswith('  '):
                # Unchanged
                word = item[2:]
                html_parts.append(word)
        
        return ' '.join(html_parts)


class CompareAnalysisTool(AgenticTool):
    """Analyze differences between aligned Excel pairs using LLM"""
    
    def __init__(self, api_key: str):
        super().__init__("compare_analysis", "Generate AI descriptions of differences between aligned pairs")
        # Use GPT-5-mini for efficient analysis of differences
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.llm_fallback = AzureChatOpenAI(
            model="gpt-5-mini",
            temperature=0.7,
            api_key=api_key,
            streaming=True
        )
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Analyze alignment results and add AI-generated analysis column"""
        previous_output = context.get('previous_output', '')
        
        if not previous_output or not previous_output.startswith('ALIGNMENT_RESULT:'):
            return "Error: No alignment data found in previous step"
        
        try:
            # Parse alignment result
            json_data = previous_output.replace('ALIGNMENT_RESULT:', '').strip()
            alignment_result = json.loads(json_data)
            
            # Support both unified_pairs (new) and matched_pairs (backward compatibility)
            all_pairs = alignment_result.get('unified_pairs', alignment_result.get('matched_pairs', []))
            # Only analyze matched pairs
            matched_pairs = [p for p in all_pairs if p.get('is_matched', True)]
            
            file1_col = alignment_result.get('file1_column', 'File 1')
            file2_col = alignment_result.get('file2_column', 'File 2')
            
            if not matched_pairs:
                return "No matched pairs found to compare."
            
            if streaming_callback:
                streaming_callback(f"🔍 Analyzing {len(matched_pairs)} matched pairs...\n\n")
            
            # Loop through each matched pair and add AI analysis
            analyzed_count = 0
            for idx, pair in enumerate(all_pairs):
                # Skip unmatched items
                if pair.get('is_matched') == False:
                    continue
                
                analyzed_count += 1
                text1 = pair.get('file1_value', '')
                text2 = pair.get('file2_value', '')
                similarity = pair.get('similarity', 0)
                
                if streaming_callback:
                    streaming_callback(f"🔍 Analyzing pair {analyzed_count}/{len(matched_pairs)}...\n\n")
                
                # Build prompt for this pair
                pair_prompt = f"""Compare these two text values and briefly describe the key differences in 1-2 concise sentences.
Focus on meaningful changes, not trivial wording differences.

Value from {file1_col}: {text1}

Value from {file2_col}: {text2}

Similarity score: {similarity:.1%}

Brief description of differences:"""
                
                # Get GPT-5-mini analysis (non-streaming for cleaner API)
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-5-mini",
                        messages=[
                            {
                                "role": "user",
                                "content": pair_prompt
                            }
                        ],
                        response_format={"type": "text"},
                        verbosity="low",
                        reasoning_effort="low"
                    )
                    analysis = response.choices[0].message.content.strip() if response.choices else ""
                except Exception as e:
                    print(f"GPT-5-mini comparison error for pair {analyzed_count}: {e}")
                    # Fallback to GPT-5-mini via LangChain
                    response = self.llm_fallback.invoke(pair_prompt)
                    analysis = response.content.strip()
                
                # Add analysis to the pair
                pair['analysis'] = analysis
            
            # Mark that this result has analysis
            alignment_result['has_analysis'] = True
            
            # Update the unified_pairs or matched_pairs with analysis
            if 'unified_pairs' in alignment_result:
                alignment_result['unified_pairs'] = all_pairs
            else:
                alignment_result['matched_pairs'] = [p for p in all_pairs if p.get('is_matched', True)]
            
            # Return enhanced alignment result
            output = f"ALIGNMENT_RESULT:{json.dumps(alignment_result)}"
            
            if streaming_callback:
                streaming_callback(f"✅ Comparison analysis complete for all {analyzed_count} pairs!")
            
            return output
            
        except Exception as e:
            error_msg = f"**Compare analysis error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg


class RAGSetupTool(AgenticTool):
    """Set up RAG system for document chat"""
    
    def __init__(self, api_key: str):
        super().__init__("rag_setup", "Set up Retrieval Augmented Generation for document chat")
        self.api_key = api_key
        self.embeddings = AzureOpenAIEmbeddings(api_key=api_key)
        self.llm = AzureChatOpenAI(
            model="gpt-5-mini",
            temperature=0.3,
            api_key=api_key
        )
        self.vectorstore = None
        self.session_id = None
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Set up RAG system with uploaded documents"""
        try:
            # Get all document contents
            all_documents = context.get('all_documents', [])
            
            if not all_documents:
                return "RAG_INITIALIZED:No documents provided"
            
            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
            )
            
            # Create Document objects with metadata
            docs = []
            for doc_info in all_documents:
                content = doc_info.get('content', '')
                filename = doc_info.get('filename', 'unknown')
                
                # Split the content
                chunks = text_splitter.split_text(content)
                
                # Create Document objects with source metadata
                for i, chunk in enumerate(chunks):
                    docs.append(Document(
                        page_content=chunk,
                        metadata={
                            'source': filename,
                            'chunk': i
                        }
                    ))
            
            if not docs:
                return "RAG_INITIALIZED:No content to index"
            
            # Create vector store
            self.vectorstore = FAISS.from_documents(docs, self.embeddings)
            
            # Generate session ID for this RAG instance
            import uuid
            self.session_id = str(uuid.uuid4())
            
            # Store vectorstore globally (will be accessed by chat endpoint)
            global _rag_sessions
            if '_rag_sessions' not in globals():
                _rag_sessions = {}
            _rag_sessions[self.session_id] = {
                'vectorstore': self.vectorstore,
                'llm': self.llm,
                'document_count': len(all_documents),
                'chunk_count': len(docs)
            }
            
            result = {
                'session_id': self.session_id,
                'document_count': len(all_documents),
                'chunk_count': len(docs),
                'status': 'ready'
            }
            
            return f"RAG_INITIALIZED:{json.dumps(result)}"
            
        except Exception as e:
            error_msg = f"RAG setup error: {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return f"RAG_INITIALIZED:{{\"error\": \"{str(e)}\"}}"


# Global storage for RAG sessions
_rag_sessions = {}


def clear_rag_sessions() -> None:
    """Clear all stored RAG sessions to free memory/resources."""
    global _rag_sessions
    _rag_sessions = {}


def get_rag_session(session_id: str):
    """Get RAG session by ID"""
    return _rag_sessions.get(session_id)


def rag_chat(session_id: str, question: str) -> Dict[str, Any]:
    """Handle chat query with RAG"""
    session = get_rag_session(session_id)
    
    if not session:
        return {
            'answer': 'Error: Chat session not found. Please restart the workflow.',
            'sources': []
        }
    
    try:
        vectorstore = session['vectorstore']
        llm = session['llm']
        
        # Retrieve relevant documents
        retriever = vectorstore.as_retriever(
            search_kwargs={'k': 4}
        )
        
        docs = retriever.get_relevant_documents(question)
        
        # Format context from retrieved documents
        context_parts = []
        sources = []
        
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('source', 'Unknown')
            context_parts.append(f"[Source {i}: {source}]\n{doc.page_content}")
            if source not in sources:
                sources.append(source)
        
        context = "\n\n".join(context_parts)
        
        # Create prompt with citations
        prompt = f"""Answer the question based ONLY on the provided context from the user's documents. 
Include inline citations using [Source N] format where information comes from.

Context:
{context}

Question: {question}

Answer (with citations):"""
        
        # Get answer from LLM
        response = llm.invoke(prompt)
        answer = response.content
        
        return {
            'answer': answer,
            'sources': sources
        }
        
    except Exception as e:
        return {
            'answer': f'Error processing question: {str(e)}',
            'sources': []
        }


class RedlineDiffTool(AgenticTool):
    """Generate redline diff between two documents with word-level granularity"""
    
    def __init__(self):
        super().__init__("redline_diff", "Generate word-level redline diff between two documents")
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Generate redline diff between two text documents"""
        try:
            # Get the two documents to compare from labeled_documents
            labeled_docs = context.get('labeled_documents', {})
            doc1_label = context.get('doc1_label', 'document1')
            doc2_label = context.get('doc2_label', 'document2')
            
            doc1_content = labeled_docs.get(doc1_label, {}).get('content', '')
            doc2_content = labeled_docs.get(doc2_label, {}).get('content', '')
            
            if not doc1_content or not doc2_content:
                # Fallback to all_documents if labeled_documents not available
                all_docs = context.get('all_documents', [])
                if len(all_docs) >= 2:
                    doc1_content = all_docs[0].get('content', '')
                    doc2_content = all_docs[1].get('content', '')
            
            if not doc1_content or not doc2_content:
                return "Error: Two documents required for redline comparison"
            
            if streaming_callback:
                streaming_callback("📄 Analyzing documents for differences...")
            
            # Generate word-level diff
            differ = difflib.Differ()
            
            # Split into words for more granular comparison
            words1 = doc1_content.split()
            words2 = doc2_content.split()
            
            diff = list(differ.compare(words1, words2))
            
            if streaming_callback:
                streaming_callback("📄 Building redline document...")
            
            # Build HTML redline with better formatting
            html_parts = ['<div class="redline-diff">']
            current_line = []
            
            for item in diff:
                if item.startswith('- '):
                    # Removed (redline)
                    word = item[2:]
                    current_line.append(f'<span class="diff-removed">{word}</span>')
                elif item.startswith('+ '):
                    # Added (greenline)
                    word = item[2:]
                    current_line.append(f'<span class="diff-added">{word}</span>')
                elif item.startswith('  '):
                    # Unchanged
                    word = item[2:]
                    current_line.append(word)
                elif item.startswith('? '):
                    # Ignore marker lines
                    continue
            
            html_parts.append(' '.join(current_line))
            html_parts.append('</div>')
            
            # Calculate statistics
            removed_count = sum(1 for item in diff if item.startswith('- '))
            added_count = sum(1 for item in diff if item.startswith('+ '))
            unchanged_count = sum(1 for item in diff if item.startswith('  '))
            
            total_words = removed_count + added_count + unchanged_count
            change_percentage = ((removed_count + added_count) / total_words * 100) if total_words > 0 else 0
            
            # Build result with metadata
            result = {
                'diff_html': ''.join(html_parts),
                'removed_words': removed_count,
                'added_words': added_count,
                'unchanged_words': unchanged_count,
                'change_percentage': round(change_percentage, 2),
                'doc1_label': doc1_label,
                'doc2_label': doc2_label
            }
            
            output = f"REDLINE_DIFF:{json.dumps(result)}"
            
            if streaming_callback:
                streaming_callback(f"✅ Redline comparison complete!\n\n**Summary:**\n- {removed_count} words removed\n- {added_count} words added\n- {change_percentage:.1f}% changed")
            
            return output
            
        except Exception as e:
            error_msg = f"**Redline diff error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg


class DerivativeAnalysisTool(AgenticTool):
    """Analyze how a derivative document was created from an original, using GPT-5 with reasoning"""
    
    def __init__(self, api_key: str):
        super().__init__("derivative_analysis", "Deep analysis of derivative document creation using GPT-5 with reasoning")
        # Use direct OpenAI client to access GPT-5 with verbosity & reasoning parameters
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)

        # Backup LLM for regular operations / fallback streaming
        self.regular_llm = AzureChatOpenAI(
            model="gpt-5-mini",
            temperature=0.7,
            api_key=api_key,
            streaming=True
        )
    
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
            
            # Use GPT-5 with verbosity and reasoning_effort for complex analysis
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

            # Get reasoning analysis using GPT-5 with verbosity & reasoning parameters
            analysis = ""
            try:
                response = self.client.chat.completions.create(
                    model="gpt-5",
                    messages=[
                        {
                            "role": "developer",
                            "content": [
                                {
                                    "type": "text",
                                    "text": analysis_prompt
                                }
                            ]
                        }
                    ],
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


class UpdateDerivativeTool(AgenticTool):
    """Create updated derivative based on changes to primary document"""
    
    def __init__(self, api_key: str):
        super().__init__("update_derivative", "Generate updated derivative document based on primary changes")
        self.llm = AzureChatOpenAI(
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


class SmartChunkerTool(AgenticTool):
    """Intelligent document chunking with structure detection and embeddings"""
    
    def __init__(self, api_key: str):
        super().__init__("smart_chunker", "Intelligently segment documents by structure")
        self.embeddings = AzureOpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=api_key
        )
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Chunk documents intelligently based on structure and size"""
        try:
            # Get both documents
            labeled_docs = context.get('labeled_documents', {})
            all_docs = context.get('all_documents', [])
            
            # Support both labeled and indexed access
            if labeled_docs and len(labeled_docs) >= 2:
                doc1_content = list(labeled_docs.values())[0].get('content', '')
                doc2_content = list(labeled_docs.values())[1].get('content', '')
            elif all_docs and len(all_docs) >= 2:
                doc1_content = all_docs[0].get('content', '')
                doc2_content = all_docs[1].get('content', '')
            else:
                return "Error: Two documents required for comparison"
            
            if streaming_callback:
                streaming_callback("📄 Analyzing document structure...")
            
            # Detect document size and choose chunking strategy
            doc1_words = len(doc1_content.split())
            doc2_words = len(doc2_content.split())
            max_words = max(doc1_words, doc2_words)
            
            # Estimate pages (250 words per page)
            est_pages = max_words / 250
            
            if streaming_callback:
                streaming_callback(f"📄 Estimated document size: ~{int(est_pages)} pages\n\nChoosing chunking strategy...")
            
            # Choose strategy based on size
            if est_pages <= 50:
                strategy = "paragraph"
                chunk_size = 500  # words
            elif est_pages <= 200:
                strategy = "section"
                chunk_size = 1000
            else:
                strategy = "adaptive"
                chunk_size = 1500
            
            if streaming_callback:
                streaming_callback(f"📄 Using {strategy} chunking strategy\n\nSegmenting documents...")
            
            # Chunk both documents
            chunks1 = self._chunk_document(doc1_content, strategy, chunk_size)
            chunks2 = self._chunk_document(doc2_content, strategy, chunk_size)
            
            if streaming_callback:
                streaming_callback(f"📄 Document 1: {len(chunks1)} chunks\n📄 Document 2: {len(chunks2)} chunks\n\nGenerating embeddings...")
            
            # Generate embeddings for semantic matching
            embeddings1 = self.embeddings.embed_documents([c['text'] for c in chunks1])
            embeddings2 = self.embeddings.embed_documents([c['text'] for c in chunks2])
            
            # Add embeddings to chunks
            for i, emb in enumerate(embeddings1):
                chunks1[i]['embedding'] = emb
            for i, emb in enumerate(embeddings2):
                chunks2[i]['embedding'] = emb
            
            # Create result
            result = {
                'strategy': strategy,
                'chunk_size': chunk_size,
                'estimated_pages': int(est_pages),
                'doc1_chunks': chunks1,
                'doc2_chunks': chunks2,
                'doc1_word_count': doc1_words,
                'doc2_word_count': doc2_words
            }
            
            output = f"CHUNKING_RESULT:{json.dumps(result)}"
            
            if streaming_callback:
                streaming_callback(f"✅ Chunking complete!\n\n**Summary:**\n- Strategy: {strategy}\n- Doc 1: {len(chunks1)} chunks ({doc1_words} words)\n- Doc 2: {len(chunks2)} chunks ({doc2_words} words)")
            
            return output
            
        except Exception as e:
            error_msg = f"**Chunking error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg
    
    def _chunk_document(self, content: str, strategy: str, chunk_size: int) -> List[Dict]:
        """Chunk document based on strategy"""
        chunks = []
        
        if strategy == "paragraph":
            # Split by double newlines (paragraphs)
            paragraphs = re.split(r'\n\s*\n', content)
            
            current_chunk = []
            current_words = 0
            chunk_id = 0
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                para_words = len(para.split())
                
                if current_words + para_words > chunk_size and current_chunk:
                    # Save current chunk
                    chunks.append({
                        'id': chunk_id,
                        'text': '\n\n'.join(current_chunk),
                        'type': 'paragraph',
                        'word_count': current_words,
                        'structure_level': self._detect_structure_level(current_chunk[0])
                    })
                    chunk_id += 1
                    current_chunk = []
                    current_words = 0
                
                current_chunk.append(para)
                current_words += para_words
            
            # Add final chunk
            if current_chunk:
                chunks.append({
                    'id': chunk_id,
                    'text': '\n\n'.join(current_chunk),
                    'type': 'paragraph',
                    'word_count': current_words,
                    'structure_level': self._detect_structure_level(current_chunk[0])
                })
        
        elif strategy == "section":
            # Try to split by headings
            lines = content.split('\n')
            current_section = []
            current_words = 0
            chunk_id = 0
            current_heading = None
            
            for line in lines:
                line_stripped = line.strip()
                
                # Check if this is a heading
                is_heading = self._is_heading(line_stripped)
                
                if is_heading and current_section and current_words > chunk_size // 2:
                    # Save current section
                    chunks.append({
                        'id': chunk_id,
                        'text': '\n'.join(current_section),
                        'type': 'section',
                        'word_count': current_words,
                        'heading': current_heading,
                        'structure_level': self._detect_structure_level(current_heading or '')
                    })
                    chunk_id += 1
                    current_section = []
                    current_words = 0
                
                if is_heading:
                    current_heading = line_stripped
                
                current_section.append(line)
                current_words += len(line_stripped.split())
            
            # Add final section
            if current_section:
                chunks.append({
                    'id': chunk_id,
                    'text': '\n'.join(current_section),
                    'type': 'section',
                    'word_count': current_words,
                    'heading': current_heading,
                    'structure_level': self._detect_structure_level(current_heading or '')
                })
        
        else:  # adaptive
            # Use both paragraph and heading detection
            chunks = self._chunk_document(content, "section", chunk_size)
        
        return chunks
    
    def _is_heading(self, text: str) -> bool:
        """Detect if text is likely a heading"""
        if not text:
            return False
        
        # Markdown heading
        if re.match(r'^#{1,6}\s+', text):
            return True
        
        # All caps short text
        if text.isupper() and len(text) < 100:
            return True
        
        # Title case short text without ending punctuation
        if text.istitle() and len(text) < 80 and not text.endswith(('.', '!', '?', ',')):
            return True
        
        # Numbered section
        if re.match(r'^\d+\.(\d+\.)*\s+[A-Z]', text):
            return True
        
        return False
    
    def _detect_structure_level(self, text: str) -> int:
        """Detect the structural level (heading depth)"""
        # Markdown heading
        match = re.match(r'^(#{1,6})\s+', text)
        if match:
            return len(match.group(1))
        
        # Numbered section depth
        if re.match(r'^(\d+\.)+', text):
            return text[:20].count('.')
        
        # All caps = level 1
        if text.isupper():
            return 1
        
        # Title case = level 2
        if text.istitle():
            return 2
        
        return 0  # Body text


class EnhancedDiffTool(AgenticTool):
    """Advanced diff generation with multi-level granularity and PDF support"""
    
    def __init__(self):
        super().__init__("enhanced_diff", "Generate multi-level diffs with visual rendering")
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Generate enhanced diff between two documents"""
        try:
            # Get documents
            labeled_docs = context.get('labeled_documents', {})
            all_docs = context.get('all_documents', [])
            
            if labeled_docs and len(labeled_docs) >= 2:
                doc1_content = list(labeled_docs.values())[0].get('content', '')
                doc2_content = list(labeled_docs.values())[1].get('content', '')
                doc1_name = list(labeled_docs.keys())[0]
                doc2_name = list(labeled_docs.keys())[1]
            elif all_docs and len(all_docs) >= 2:
                doc1_content = all_docs[0].get('content', '')
                doc2_content = all_docs[1].get('content', '')
                doc1_name = all_docs[0].get('filename', 'Document 1')
                doc2_name = all_docs[1].get('filename', 'Document 2')
            else:
                return "Error: Two documents required for diff"
            
            if streaming_callback:
                streaming_callback("📊 Generating multi-level diff analysis...")
            
            # Generate word-level diff
            words1 = doc1_content.split()
            words2 = doc2_content.split()
            
            differ = difflib.Differ()
            diff = list(differ.compare(words1, words2))
            
            if streaming_callback:
                streaming_callback("📊 Creating visual markup...")
            
            # Build HTML with better formatting and change tracking
            html_parts = ['<div class="enhanced-diff">']
            
            # Add statistics section
            removed_count = sum(1 for item in diff if item.startswith('- '))
            added_count = sum(1 for item in diff if item.startswith('+ '))
            unchanged_count = sum(1 for item in diff if item.startswith('  '))
            
            total_words = removed_count + added_count + unchanged_count
            change_percentage = ((removed_count + added_count) / total_words * 100) if total_words > 0 else 0
            
            # Generate unified diff view with line numbers
            current_line = []
            line_number = 0
            changes_by_type = {'additions': [], 'deletions': [], 'modifications': []}
            
            for item in diff:
                if item.startswith('- '):
                    word = item[2:]
                    current_line.append(f'<span class="diff-removed" data-word="{word}">{word}</span>')
                    changes_by_type['deletions'].append({'word': word, 'position': line_number})
                elif item.startswith('+ '):
                    word = item[2:]
                    current_line.append(f'<span class="diff-added" data-word="{word}">{word}</span>')
                    changes_by_type['additions'].append({'word': word, 'position': line_number})
                elif item.startswith('  '):
                    word = item[2:]
                    current_line.append(f'<span class="diff-unchanged">{word}</span>')
                
                # Add line breaks at sentence boundaries or every 20 words
                if len(current_line) > 20 or (item.endswith('.') or item.endswith('?') or item.endswith('!')):
                    if current_line:
                        html_parts.append(f'<div class="diff-line" data-line="{line_number}">{" ".join(current_line)}</div>')
                        line_number += 1
                        current_line = []
            
            # Add remaining words
            if current_line:
                html_parts.append(f'<div class="diff-line" data-line="{line_number}">{" ".join(current_line)}</div>')
            
            html_parts.append('</div>')
            
            # Generate sentence-level diff for better context
            sentences1 = re.split(r'[.!?]+\s+', doc1_content)
            sentences2 = re.split(r'[.!?]+\s+', doc2_content)
            
            sentence_matcher = difflib.SequenceMatcher(None, sentences1, sentences2)
            sentence_changes = []
            
            for tag, i1, i2, j1, j2 in sentence_matcher.get_opcodes():
                if tag != 'equal':
                    sentence_changes.append({
                        'type': tag,
                        'doc1_sentences': sentences1[i1:i2],
                        'doc2_sentences': sentences2[j1:j2],
                        'doc1_range': [i1, i2],
                        'doc2_range': [j1, j2]
                    })
            
            # Create comprehensive result
            result = {
                'diff_html': ''.join(html_parts),
                'statistics': {
                    'removed_words': removed_count,
                    'added_words': added_count,
                    'unchanged_words': unchanged_count,
                    'total_words': total_words,
                    'change_percentage': round(change_percentage, 2),
                    'doc1_word_count': len(words1),
                    'doc2_word_count': len(words2)
                },
                'changes_by_type': changes_by_type,
                'sentence_changes': sentence_changes[:50],  # Limit to first 50 for performance
                'doc1_name': doc1_name,
                'doc2_name': doc2_name,
                'change_summary': f"{removed_count} deletions, {added_count} additions, {round(change_percentage, 1)}% changed"
            }
            
            output = f"ENHANCED_DIFF:{json.dumps(result)}"
            
            if streaming_callback:
                streaming_callback(f"✅ Diff generation complete!\n\n**Summary:**\n- {removed_count} words removed\n- {added_count} words added\n- {unchanged_count} words unchanged\n- {change_percentage:.1f}% changed")
            
            return output
            
        except Exception as e:
            error_msg = f"**Enhanced diff error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg


class StructuralAnalysisTool(AgenticTool):
    """Analyze and compare document structure"""
    
    def __init__(self):
        super().__init__("structural_analysis", "Compare document outlines and hierarchies")
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Analyze structural differences between documents"""
        try:
            # Get documents
            labeled_docs = context.get('labeled_documents', {})
            all_docs = context.get('all_documents', [])
            
            if labeled_docs and len(labeled_docs) >= 2:
                doc1_content = list(labeled_docs.values())[0].get('content', '')
                doc2_content = list(labeled_docs.values())[1].get('content', '')
                doc1_name = list(labeled_docs.keys())[0]
                doc2_name = list(labeled_docs.keys())[1]
            elif all_docs and len(all_docs) >= 2:
                doc1_content = all_docs[0].get('content', '')
                doc2_content = all_docs[1].get('content', '')
                doc1_name = all_docs[0].get('filename', 'Document 1')
                doc2_name = all_docs[1].get('filename', 'Document 2')
            else:
                return "Error: Two documents required"
            
            if streaming_callback:
                streaming_callback("🏗️ Analyzing document structures...")
            
            # Extract structure from both documents
            structure1 = self._extract_structure(doc1_content)
            structure2 = self._extract_structure(doc2_content)
            
            if streaming_callback:
                streaming_callback("🏗️ Comparing hierarchies...")
            
            # Compare structures
            structural_changes = self._compare_structures(structure1, structure2)
            
            # Detect reordering
            reordered_sections = self._detect_reordering(structure1, structure2)
            
            # Create result
            result = {
                'doc1_structure': structure1,
                'doc2_structure': structure2,
                'doc1_name': doc1_name,
                'doc2_name': doc2_name,
                'added_sections': structural_changes['added'],
                'removed_sections': structural_changes['removed'],
                'modified_sections': structural_changes['modified'],
                'reordered_sections': reordered_sections,
                'hierarchy_changes': structural_changes['hierarchy_changes'],
                'summary': {
                    'total_sections_doc1': len(structure1),
                    'total_sections_doc2': len(structure2),
                    'sections_added': len(structural_changes['added']),
                    'sections_removed': len(structural_changes['removed']),
                    'sections_modified': len(structural_changes['modified']),
                    'sections_reordered': len(reordered_sections)
                }
            }
            
            output = f"STRUCTURAL_ANALYSIS:{json.dumps(result)}"
            
            if streaming_callback:
                streaming_callback(f"✅ Structural analysis complete!\n\n**Summary:**\n- {len(structural_changes['added'])} sections added\n- {len(structural_changes['removed'])} sections removed\n- {len(structural_changes['modified'])} sections modified\n- {len(reordered_sections)} sections reordered")
            
            return output
            
        except Exception as e:
            error_msg = f"**Structural analysis error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg
    
    def _extract_structure(self, content: str) -> List[Dict]:
        """Extract hierarchical structure from document"""
        structure = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check for heading patterns
            level = self._detect_heading_level(line_stripped)
            if level > 0:
                structure.append({
                    'line_number': i,
                    'level': level,
                    'text': line_stripped,
                    'type': 'heading',
                    'normalized': self._normalize_heading(line_stripped)
                })
        
        return structure
    
    def _detect_heading_level(self, text: str) -> int:
        """Detect heading level (0 = not a heading)"""
        # Markdown headings
        match = re.match(r'^(#{1,6})\s+', text)
        if match:
            return len(match.group(1))
        
        # Numbered sections
        match = re.match(r'^((\d+\.)+)\s+', text)
        if match:
            return match.group(1).count('.')
        
        # All caps = level 1
        if text.isupper() and len(text) < 100:
            return 1
        
        # Title case without ending punctuation
        if text.istitle() and len(text) < 80 and not text.endswith(('.', '!', '?', ',')):
            return 2
        
        return 0
    
    def _normalize_heading(self, text: str) -> str:
        """Normalize heading text for comparison"""
        # Remove markdown syntax
        text = re.sub(r'^#{1,6}\s+', '', text)
        # Remove numbering
        text = re.sub(r'^(\d+\.)+\s+', '', text)
        # Lowercase and strip
        return text.lower().strip()
    
    def _compare_structures(self, struct1: List[Dict], struct2: List[Dict]) -> Dict:
        """Compare two document structures"""
        # Create normalized maps
        map1 = {s['normalized']: s for s in struct1}
        map2 = {s['normalized']: s for s in struct2}
        
        keys1 = set(map1.keys())
        keys2 = set(map2.keys())
        
        added = [map2[k] for k in keys2 - keys1]
        removed = [map1[k] for k in keys1 - keys2]
        
        # Find modified (same heading but different level)
        modified = []
        hierarchy_changes = []
        
        for key in keys1 & keys2:
            if map1[key]['level'] != map2[key]['level']:
                hierarchy_changes.append({
                    'heading': key,
                    'old_level': map1[key]['level'],
                    'new_level': map2[key]['level'],
                    'change': 'promoted' if map2[key]['level'] < map1[key]['level'] else 'demoted'
                })
                modified.append(map2[key])
        
        return {
            'added': added,
            'removed': removed,
            'modified': modified,
            'hierarchy_changes': hierarchy_changes
        }
    
    def _detect_reordering(self, struct1: List[Dict], struct2: List[Dict]) -> List[Dict]:
        """Detect sections that were reordered"""
        # Find common sections
        norm1 = [s['normalized'] for s in struct1]
        norm2 = [s['normalized'] for s in struct2]
        
        reordered = []
        
        for norm in set(norm1) & set(norm2):
            idx1 = norm1.index(norm)
            idx2 = norm2.index(norm)
            
            if abs(idx1 - idx2) > 1:  # Moved by more than 1 position
                reordered.append({
                    'heading': norm,
                    'old_position': idx1,
                    'new_position': idx2,
                    'moved_by': idx2 - idx1
                })
        
        return reordered


class SemanticDiffTool(AgenticTool):
    """Semantic comparison using embeddings to detect paraphrased/moved content"""
    
    def __init__(self, api_key: str):
        super().__init__("semantic_diff", "Find semantically similar content across documents")
        self.embeddings = AzureOpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=api_key
        )
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Perform semantic comparison between documents"""
        try:
            # Get chunking result from previous step
            previous_output = context.get('previous_output', '')
            
            if not previous_output.startswith('CHUNKING_RESULT:'):
                return "Error: Semantic diff requires chunking result from previous step"
            
            # Parse chunking result
            json_data = previous_output.replace('CHUNKING_RESULT:', '').strip()
            chunking_result = json.loads(json_data)
            
            chunks1 = chunking_result['doc1_chunks']
            chunks2 = chunking_result['doc2_chunks']
            
            if streaming_callback:
                streaming_callback("🔍 Performing semantic analysis...")
            
            # Extract embeddings
            embeddings1 = np.array([c['embedding'] for c in chunks1])
            embeddings2 = np.array([c['embedding'] for c in chunks2])
            
            # Compute similarity matrix
            emb1_norm = embeddings1 / np.linalg.norm(embeddings1, axis=1, keepdims=True)
            emb2_norm = embeddings2 / np.linalg.norm(embeddings2, axis=1, keepdims=True)
            
            similarity_matrix = np.dot(emb1_norm, emb2_norm.T)
            
            if streaming_callback:
                streaming_callback("🔍 Identifying semantic matches...")
            
            # Find semantic matches (threshold: 0.85 for high similarity)
            semantic_matches = []
            moved_content = []
            paraphrased_content = []
            
            for i in range(len(chunks1)):
                best_match_idx = np.argmax(similarity_matrix[i])
                best_similarity = similarity_matrix[i][best_match_idx]
                
                if best_similarity > 0.85:
                    chunk1 = chunks1[i]
                    chunk2 = chunks2[best_match_idx]
                    
                    match_data = {
                        'chunk1_id': chunk1['id'],
                        'chunk2_id': chunk2['id'],
                        'similarity': float(best_similarity),
                        'chunk1_text': chunk1['text'][:200],  # First 200 chars
                        'chunk2_text': chunk2['text'][:200],
                        'position_shift': best_match_idx - i
                    }
                    
                    semantic_matches.append(match_data)
                    
                    # Classify as moved or paraphrased
                    if abs(best_match_idx - i) > 2:
                        moved_content.append(match_data)
                    elif best_similarity < 0.95:
                        paraphrased_content.append(match_data)
            
            # Find new content (chunks in doc2 with no good match in doc1)
            matched_chunks2 = set()
            for match in semantic_matches:
                matched_chunks2.add(match['chunk2_id'])
            
            new_content = []
            for chunk in chunks2:
                if chunk['id'] not in matched_chunks2:
                    # Check if this chunk has any reasonable similarity
                    chunk_idx = chunk['id']
                    if chunk_idx < len(similarity_matrix[0]):
                        max_sim = np.max(similarity_matrix[:, chunk_idx])
                        if max_sim < 0.7:  # Truly new content
                            new_content.append({
                                'chunk_id': chunk['id'],
                                'text': chunk['text'][:200],
                                'word_count': chunk['word_count']
                            })
            
            # Find removed content
            matched_chunks1 = set()
            for match in semantic_matches:
                matched_chunks1.add(match['chunk1_id'])
            
            removed_content = []
            for chunk in chunks1:
                if chunk['id'] not in matched_chunks1:
                    chunk_idx = chunk['id']
                    if chunk_idx < len(similarity_matrix):
                        max_sim = np.max(similarity_matrix[chunk_idx])
                        if max_sim < 0.7:
                            removed_content.append({
                                'chunk_id': chunk['id'],
                                'text': chunk['text'][:200],
                                'word_count': chunk['word_count']
                            })
            
            # Create result
            result = {
                'semantic_matches': semantic_matches,
                'moved_content': moved_content,
                'paraphrased_content': paraphrased_content,
                'new_content': new_content,
                'removed_content': removed_content,
                'summary': {
                    'total_matches': len(semantic_matches),
                    'moved_chunks': len(moved_content),
                    'paraphrased_chunks': len(paraphrased_content),
                    'new_chunks': len(new_content),
                    'removed_chunks': len(removed_content),
                    'avg_similarity': float(np.mean([m['similarity'] for m in semantic_matches])) if semantic_matches else 0.0
                }
            }
            
            output = f"SEMANTIC_DIFF:{json.dumps(result)}"
            
            if streaming_callback:
                streaming_callback(f"✅ Semantic analysis complete!\n\n**Summary:**\n- {len(semantic_matches)} semantic matches\n- {len(moved_content)} moved chunks\n- {len(paraphrased_content)} paraphrased chunks\n- {len(new_content)} new chunks\n- {len(removed_content)} removed chunks")
            
            return output
            
        except Exception as e:
            error_msg = f"**Semantic diff error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg


class ComparisonSummaryTool(AgenticTool):
    """Extract summaries from comparison analysis outputs for LLM consumption"""
    
    def __init__(self):
        super().__init__("comparison_summary", "Extract key statistics from comparison analysis")
    
    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Extract summaries from previous comparison steps"""
        try:
            step_history = context.get('step_history', [])
            
            if not step_history or len(step_history) < 4:
                return "Error: Insufficient analysis steps completed"
            
            if streaming_callback:
                streaming_callback("📊 Extracting key statistics from analysis...")
            
            summaries = []
            
            # Extract from each analysis step
            for idx, step_data in enumerate(step_history[:4]):  # First 4 steps
                output = step_data.get('output', '')
                
                # Chunking results
                if output.startswith('CHUNKING_RESULT:'):
                    json_data = output.replace('CHUNKING_RESULT:', '').strip()
                    try:
                        data = json.loads(json_data)
                        summaries.append(f"**Chunking Analysis:**\n- Strategy: {data.get('strategy')}\n- Document 1: {data.get('doc1_word_count')} words in {len(data.get('doc1_chunks', []))} chunks\n- Document 2: {data.get('doc2_word_count')} words in {len(data.get('doc2_chunks', []))} chunks\n- Estimated pages: ~{data.get('estimated_pages')}")
                    except:
                        pass
                
                # Enhanced diff
                elif output.startswith('ENHANCED_DIFF:'):
                    json_data = output.replace('ENHANCED_DIFF:', '').strip()
                    try:
                        data = json.loads(json_data)
                        stats = data.get('statistics', {})
                        summaries.append(f"**Visual Diff Statistics:**\n- Words removed: {stats.get('removed_words', 0)}\n- Words added: {stats.get('added_words', 0)}\n- Words unchanged: {stats.get('unchanged_words', 0)}\n- Change percentage: {stats.get('change_percentage', 0)}%\n- Total words: {stats.get('total_words', 0)}")
                    except:
                        pass
                
                # Structural analysis
                elif output.startswith('STRUCTURAL_ANALYSIS:'):
                    json_data = output.replace('STRUCTURAL_ANALYSIS:', '').strip()
                    try:
                        data = json.loads(json_data)
                        summary = data.get('summary', {})
                        summaries.append(f"**Structural Changes:**\n- Sections added: {summary.get('sections_added', 0)}\n- Sections removed: {summary.get('sections_removed', 0)}\n- Sections modified: {summary.get('sections_modified', 0)}\n- Sections reordered: {summary.get('sections_reordered', 0)}\n- Total sections in Doc 1: {summary.get('total_sections_doc1', 0)}\n- Total sections in Doc 2: {summary.get('total_sections_doc2', 0)}")
                    except:
                        pass
                
                # Semantic diff
                elif output.startswith('SEMANTIC_DIFF:'):
                    json_data = output.replace('SEMANTIC_DIFF:', '').strip()
                    try:
                        data = json.loads(json_data)
                        summary = data.get('summary', {})
                        summaries.append(f"**Semantic Analysis:**\n- Total semantic matches: {summary.get('total_matches', 0)}\n- Moved chunks: {summary.get('moved_chunks', 0)}\n- Paraphrased chunks: {summary.get('paraphrased_chunks', 0)}\n- New chunks: {summary.get('new_chunks', 0)}\n- Removed chunks: {summary.get('removed_chunks', 0)}\n- Average similarity: {summary.get('avg_similarity', 0):.1%}")
                    except:
                        pass
            
            if not summaries:
                return "No analysis summaries could be extracted."
            
            output = "\n\n".join(summaries)
            
            if streaming_callback:
                streaming_callback(f"✅ Summary extraction complete!\n\n{output}")
            
            return output
            
        except Exception as e:
            error_msg = f"**Summary extraction error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg


class ToolRegistry:
    """Registry for all available agentic tools"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.tools = {
            'llm_prompt': LLMPromptTool(api_key),
            'web_search': WebSearchTool(),
            'document_analysis': DocumentAnalysisTool(),
            'fact_check': FactCheckTool(api_key),
            'content_enrichment': ContentEnrichmentTool(api_key),
            'data_validation': DataValidationTool(),
            'podcast_generator': PodcastGeneratorTool(api_key),
            'alignment': AlignmentTool(api_key),
            'compare_analysis': CompareAnalysisTool(api_key),
            'rag_setup': RAGSetupTool(api_key),
            'redline_diff': RedlineDiffTool(),
            'derivative_analysis': DerivativeAnalysisTool(api_key),
            'update_derivative': UpdateDerivativeTool(api_key),
            'smart_chunker': SmartChunkerTool(api_key),
            'enhanced_diff': EnhancedDiffTool(),
            'structural_analysis': StructuralAnalysisTool(),
            'semantic_diff': SemanticDiffTool(api_key),
            'comparison_summary': ComparisonSummaryTool(),
        }
    
    def get_tool(self, tool_type: str) -> Optional[AgenticTool]:
        """Get tool by type"""
        return self.tools.get(tool_type)
    
    def list_tools(self) -> Dict[str, str]:
        """List all available tools with descriptions"""
        return {
            name: tool.description 
            for name, tool in self.tools.items()
        }
    
    def execute_step(self, step: Dict[str, Any], context: Dict[str, Any], 
                     streaming_callback: Optional[Callable] = None) -> str:
        """Execute a step using the appropriate tool"""
        step_type = step.get('step_type', 'llm_prompt')
        tool = self.get_tool(step_type)
        
        if not tool:
            return f"Error: Unknown tool type '{step_type}'"
        
        # Get user options and substitute in parameters
        user_options = context.get('user_options', {})
        step_parameters = step.get('parameters', {}).copy()
        
        # Substitute user option placeholders in parameter values
        for param_key, param_value in step_parameters.items():
            if isinstance(param_value, str):
                for option_key, option_value in user_options.items():
                    placeholder = f'{{{option_key}}}'
                    if placeholder in param_value:
                        step_parameters[param_key] = param_value.replace(placeholder, str(option_value))
        
        # Prepare context with step parameters
        execution_context = {
            **context,
            **step_parameters,
            'prompt': step.get('prompt', ''),
            'template_variables': step.get('template_variables', [])
        }
        
        return tool.execute(execution_context, streaming_callback)

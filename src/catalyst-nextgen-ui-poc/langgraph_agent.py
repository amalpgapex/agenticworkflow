"""
LangGraph Agent for Document Transformation
Orchestrates multi-step transformations using LangGraph with multiple agentic tools
"""

from typing import TypedDict, List, Dict, Callable, Optional
from langchain_openai import ChatOpenAI
from langchain_core.callbacks.base import BaseCallbackHandler
from langgraph.graph import StateGraph, END
import os
from agentic_tools import ToolRegistry


class AgentState(TypedDict):
    """State object passed between agent steps"""
    document_content: str
    transformation_key: str
    steps: List[Dict]
    current_step_index: int
    previous_output: str
    final_output: str
    step_outputs: List[Dict]
    error: Optional[str]
    all_documents: Optional[List[Dict]]  # For multiple file support


class StreamingCallbackHandler(BaseCallbackHandler):
    """Custom callback handler for streaming tokens"""
    
    def __init__(self, callback_func: Optional[Callable[[str], None]] = None):
        self.callback_func = callback_func
        self.text = ""
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Called when a new token is generated"""
        self.text += token
        if self.callback_func:
            self.callback_func(self.text)


class DocumentTransformationAgent:
    """Agent that executes multi-step document transformations"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the agent with OpenAI API key and tool registry
        
        Args:
            api_key: OpenAI API key (can be passed directly or via OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4o-mini, alternatives: gpt-4o, gpt-4)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Please configure in app.py or set OPENAI_API_KEY environment variable.")
        
        self.llm = ChatOpenAI(
            model=model,
            temperature=0.7,
            api_key=self.api_key,
            streaming=True  # Enable streaming
        )
        
        # Initialize tool registry for multi-tool support
        self.tool_registry = ToolRegistry(self.api_key)
        
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("execute_step", self._execute_step)
        workflow.add_node("finalize", self._finalize)
        
        # Set entry point
        workflow.set_entry_point("execute_step")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "execute_step",
            self._should_continue,
            {
                "continue": "execute_step",
                "finalize": "finalize",
                "error": END
            }
        )
        
        # Add edge from finalize to end
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    def _execute_step(self, state: AgentState) -> AgentState:
        """Execute a single step using the appropriate agentic tool"""
        current_index = state['current_step_index']
        steps = state['steps']
        
        if current_index >= len(steps):
            return state
        
        current_step = steps[current_index]
        step_name = current_step['step_name']
        step_type = current_step.get('step_type', 'llm_prompt')  # Default to LLM prompt
        
        try:
            # Prepare context for tool execution
            context = {
                'document_content': state['document_content'],
                'previous_output': state['previous_output'],
                'step_index': current_index,
                'total_steps': len(steps),
                'all_documents': state.get('all_documents', [])
            }
            
            # Prepare streaming callback if available
            streaming_callback = None
            if hasattr(self, 'streaming_callback') and self.streaming_callback:
                streaming_callback = lambda text: self.streaming_callback(text, state['current_step_index'])
            
            # Execute step using tool registry
            output = self.tool_registry.execute_step(
                step=current_step,
                context=context,
                streaming_callback=streaming_callback
            )
            
            # Store step output
            state['step_outputs'].append({
                'step_name': step_name,
                'step_type': step_type,
                'output': output
            })
            
            # Update state
            state['previous_output'] = output
            state['current_step_index'] += 1
            
        except Exception as e:
            state['error'] = f"Error in step '{step_name}': {str(e)}"
        
        return state
    
    def _format_prompt(self, template: str, document_content: str, previous_output: str) -> str:
        """Format prompt template with available variables"""
        formatted = template.replace('{document_content}', document_content)
        formatted = formatted.replace('{previous_output}', previous_output)
        return formatted
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue to next step or finalize"""
        if state.get('error'):
            return "error"
        
        if state['current_step_index'] >= len(state['steps']):
            return "finalize"
        
        return "continue"
    
    def _finalize(self, state: AgentState) -> AgentState:
        """Finalize the transformation and set final output"""
        # The final output is the output of the last step
        if state['step_outputs']:
            state['final_output'] = state['step_outputs'][-1]['output']
        else:
            state['final_output'] = state['document_content']
        
        return state
    
    def transform_document(
        self,
        document_content: str,
        transformation_steps: List[Dict],
        transformation_key: str,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        streaming_callback: Optional[Callable[[str, int], None]] = None,
        all_documents: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Transform a document using the specified prompt chain
        
        Args:
            document_content: The text content of the document
            transformation_steps: List of steps with step_name and prompt
            transformation_key: Key identifying the transformation
            progress_callback: Optional callback function(step_name, current, total)
            streaming_callback: Optional callback function(partial_text, step_index) for real-time streaming
            all_documents: Optional list of all uploaded documents for multi-file workflows
        
        Returns:
            Dict with 'success', 'output', 'step_outputs', and optional 'error'
        """
        # Initialize state
        initial_state = AgentState(
            document_content=document_content,
            transformation_key=transformation_key,
            steps=transformation_steps,
            current_step_index=0,
            previous_output="",
            final_output="",
            step_outputs=[],
            all_documents=all_documents or [],
            error=None
        )
        
        # Store streaming callback in instance for access in _execute_step
        self.streaming_callback = streaming_callback
        
        # Execute graph with progress tracking
        try:
            # Run the graph step by step if callback provided
            if progress_callback or streaming_callback:
                state = initial_state
                total_steps = len(transformation_steps)
                
                while state['current_step_index'] < total_steps and not state.get('error'):
                    current_step = transformation_steps[state['current_step_index']]
                    if progress_callback:
                        progress_callback(
                            current_step['step_name'],
                            state['current_step_index'] + 1,
                            total_steps
                        )
                    
                    state = self._execute_step(state)
                
                # Finalize
                if not state.get('error'):
                    state = self._finalize(state)
                
                final_state = state
            else:
                # Run entire graph at once
                final_state = self.graph.invoke(initial_state)
            
            if final_state.get('error'):
                return {
                    'success': False,
                    'error': final_state['error'],
                    'output': '',
                    'step_outputs': final_state['step_outputs']
                }
            
            return {
                'success': True,
                'output': final_state['final_output'],
                'step_outputs': final_state['step_outputs'],
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Agent execution failed: {str(e)}",
                'output': '',
                'step_outputs': []
            }

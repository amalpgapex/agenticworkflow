
from typing import Dict, Any, Optional, Callable

class AgenticTool:
    """Base class for agentic tools"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Execute the tool with given context"""
        raise NotImplementedError

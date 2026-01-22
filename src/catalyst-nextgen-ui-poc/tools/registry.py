
# agentic_tools/registry.py
from typing import Dict, Optional, Callable
import pkgutil, importlib, inspect
import tools
from tools.base import AgenticTool

class ToolRegistry:
    """Auto-registry of all AgenticTool classes from the agentic_tools/* package."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.tools: Dict[str, AgenticTool] = {}
        self._load_tools()

    def _load_tools(self):
        """
        Explore agentic_tools/*, import modules, and register each class inheriting from AgenticTool.
        If the constructor signature includes 'api_key', inject it automatically.
        """
        for _, mod_name, ispkg in pkgutil.iter_modules(agentic_tools.__path__, prefix='agentic_tools.'):
            if ispkg:
                continue
            mod = importlib.import_module(mod_name)
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                # Only classes that inherit from AgenticTool (excluding the base class)
                if not issubclass(obj, AgenticTool) or obj is AgenticTool:
                    continue
                # Must have a NAME attribute (avoid helper/utility classes)
                name_attr = getattr(obj, "NAME", None)
                if not isinstance(name_attr, str) or not name_attr:
                    continue

                # Smart instantiation: pass api_key if required by the constructor
                try:
                    init_sig = inspect.signature(obj.__init__)
                    if "api_key" in init_sig.parameters:
                        instance = obj(self.api_key)
                    else:
                        instance = obj()
                    self.tools[name_attr] = instance
                except Exception as e:
                    # Do not block startup; log the error and continue
                    print(f"[ToolRegistry] Could not instantiate {obj.__name__}: {e}")

        print(f"[ToolRegistry] Registered tools: {sorted(self.tools.keys())}")

    def get_tool(self, tool_type: str) -> Optional[AgenticTool]:
        return self.tools.get(tool_type)

    def list_tools(self) -> Dict[str, str]:
        """Return a mapping of tool names to their description."""
        return {name: tool.description for name, tool in self.tools.items()}

    def execute_step(self, step: Dict[str, str], context: Dict[str, str],
                     streaming_callback: Optional[Callable] = None) -> str:
        """
        Execute a step by resolving the tool via 'step_type' (defaults to 'llm_prompt').
        - Interpolates user options into step parameters when placeholders like '{option_key}' exist.
        - Merges step parameters and common context, then delegates execution to the tool.
        """
        step_type = step.get('step_type', 'llm_prompt')
        tool = self.get_tool(step_type)
        if not tool:
            return f"Error: Unknown tool type '{step_type}'"

        user_options = context.get('user_options', {})
        step_parameters = step.get('parameters', {}).copy()

        # Interpolate placeholders in parameter values with user options
        for param_key, param_value in step_parameters.items():
            if isinstance(param_value, str):
                for option_key, option_value in user_options.items():
                    placeholder = f'{{{option_key}}}'
                    if placeholder in param_value:
                        step_parameters[param_key] = param_value.replace(placeholder, str(option_value))
        
        # Merge common context with step-specific parameters
        execution_context = {
            **context,
            **step_parameters,
            'prompt': step.get('prompt', ''),
            'template_variables': step.get('template_variables', [])
        }

        return tool.execute(execution_context, streaming_callback)

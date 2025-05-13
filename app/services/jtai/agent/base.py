from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional

class Agent(ABC):
    def __init__(self,
                 model: Any,
                 tools: List[Dict],
                 max_iterations: Optional[int] = 5,
                 prompt_template: Optional[str] = None):
        self.model = model
        self.tools = {tool['name']: tool for tool in tools}
        self.max_iterations = max_iterations
        self.prompt_template = prompt_template
        self.conversations = []

        @abstractmethod
        def execute_tool(self, tool_name: str, parameters: Dict) -> Any:
            pass
        
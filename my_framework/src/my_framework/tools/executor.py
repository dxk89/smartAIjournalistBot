# File: src/my_framework/tools/executor.py

from typing import List, Dict, Any
from my_framework.agents.tools import BaseTool

class ToolExecutor:
    """
    Executes a single tool call based on a name and input.
    """
    tools: List[BaseTool]
    tool_map: Dict[str, BaseTool]

    def __init__(self, tools: List[BaseTool]):
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """
        Finds the tool by name and runs it with the given input.
        """
        if tool_name not in self.tool_map:
            return f"Error: Tool '{tool_name}' not found."
        
        tool = self.tool_map[tool_name]
        try:
            print(f"   - Executing tool '{tool_name}'...")
            result = tool.run(tool_input)
            print("   - ✅ Tool execution successful.")
            return result
        except Exception as e:
            return f"Error executing tool {tool_name}: {e}"
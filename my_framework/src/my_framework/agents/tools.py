# File: src/my_framework/agents/tools.py

from typing import Callable, Any
from pydantic import BaseModel, Field

class BaseTool(BaseModel):
    """Base class for a tool the agent can use."""
    name: str
    description: str

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the tool."""
        raise NotImplementedError("Tool does not have a run method.")

class Tool(BaseTool):
    """
    A tool created from a Python function.
    The agent uses the function's name and docstring to understand the tool.
    """
    func: Callable

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the tool by calling the underlying function."""
        return self.func(*args, **kwargs)

def tool(func: Callable) -> Tool:
    """
    A decorator that turns a Python function into a Tool for an agent.
    The function's name and docstring are used as the tool's name and description.
    """
    return Tool(
        name=func.__name__,
        description=func.__doc__ or "",
        func=func
    )
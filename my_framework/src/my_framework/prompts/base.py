# File: src/my_framework/prompts/base.py

from abc import abstractmethod
from typing import Dict, Any, List

from ..core.runnables import Runnable
from ..core.schemas import MessageType

class BasePromptTemplate(Runnable[Dict[str, Any], List[MessageType]]):
    """
    Abstract base class for a prompt template.
    It takes a dictionary of variables and returns a formatted list of messages.
    """

    @abstractmethod
    def format_prompt(self, **kwargs: Any) -> List[MessageType]:
        """Format the prompt with the given variables."""
        pass
    
    def invoke(self, input: Dict[str, Any], config=None) -> List[MessageType]:
        return self.format_prompt(**input)
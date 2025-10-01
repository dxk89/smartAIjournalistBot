# File: src/my_framework/parsers/base.py

from abc import abstractmethod
from typing import TypeVar, Generic

from ..core.runnables import Runnable
from ..core.schemas import AIMessage

# The type of the parsed output
Output = TypeVar("Output")

class BaseOutputParser(Runnable[AIMessage | str, Output], Generic[Output]):
    """
    Abstract base class for parsing the output of a language model.
    It takes an AI message or a string and returns a structured output.
    """

    @abstractmethod
    def parse(self, text: str) -> Output:
        """Parse the raw text output from the LLM."""
        pass

    def invoke(self, input: AIMessage | str, config=None) -> Output:
        text_to_parse = input.content if isinstance(input, AIMessage) else input
        return self.parse(text_to_parse)
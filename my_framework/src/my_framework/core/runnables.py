# File: src/my_framework/core/runnables.py

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Iterator, TypeVar, Generic
from pydantic import BaseModel, Field # <--- THIS LINE IS THE FIX

# Using TypeVars for better type hinting of inputs and outputs
Input = TypeVar("Input")
Output = TypeVar("Output")

class RunnableConfig(BaseModel):
    """A class to hold runtime configuration for a Runnable."""
    run_id: str | None = None
    tags: List[str] = Field(default_factory=list)
    max_concurrency: int = 5

class Runnable(Generic[Input, Output], ABC):
    """
    The core interface for all components in the framework.
    All components (prompts, models, parsers, etc.) will implement this interface,
    which allows them to be chained together in a standardized way.
    """

    @abstractmethod
    def invoke(self, input: Input, config: RunnableConfig | None = None) -> Output:
        """Execute the component with a single input."""
        pass

    def stream(self, input: Input, config: RunnableConfig | None = None) -> Iterator[Output]:
        """Stream the output of the component in chunks."""
        # Default implementation for non-streaming components
        yield self.invoke(input, config)

    def batch(self, inputs: List[Input], config: RunnableConfig | None = None) -> List[Output]:
        """Process a list of inputs in parallel."""
        # A simple, non-parallel default implementation
        return [self.invoke(i, config) for i in inputs]

    def __or__(self, other: Runnable[Output, Any]) -> RunnableSequence:
        """
        The pipe operator (|) for chaining Runnables together.
        Example: prompt | model | parser
        """
        return RunnableSequence(first=self, last=other)

class RunnableSequence(Runnable[Input, Output]):
    """
    Represents a sequence of two or more Runnables chained together.
    """
    def __init__(self, first: Runnable, last: Runnable):
        self.first = first
        self.middle = []
        if isinstance(last, RunnableSequence):
            self.middle.extend([last.first] + last.middle)
            self.last = last.last
        else:
            self.last = last

    def invoke(self, input: Input, config: RunnableConfig | None = None) -> Output:
        """Invoke the sequence of runnables."""
        result = self.first.invoke(input, config)
        for runnable in self.middle:
            result = runnable.invoke(result, config)
        return self.last.invoke(result, config)

    def __or__(self, other: Runnable[Output, Any]) -> RunnableSequence:
        """Append another runnable to the sequence."""
        if isinstance(other, RunnableSequence):
            self.middle.extend([other.first] + other.middle)
            self.last = other.last
        else:
            self.middle.append(self.last)
            self.last = other
        return self

class RunnablePassthrough(Runnable[Input, Input]):
    """
    A special Runnable that simply passes its input through.
    Useful for branching chains.
    """
    def invoke(self, input: Input, config: RunnableConfig | None = None) -> Input:
        return input
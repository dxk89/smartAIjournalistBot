# File: src/my_framework/core/schemas.py

from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field

class Document(BaseModel):
    """A class to represent a piece of text and its associated metadata."""
    page_content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BaseMessage(BaseModel):
    """The base class for a message in a chat conversation."""
    content: str
    # FIX: The field is renamed from 'type' to 'role'
    role: str

    def __str__(self):
        return self.content

class HumanMessage(BaseMessage):
    """A message from the human user."""
    # FIX: Renamed to 'role' and value changed from 'human' to 'user'
    role: Literal["user"] = "user"

class AIMessage(BaseMessage):
    """A message from the AI."""
    # FIX: Renamed to 'role' and value changed from 'ai' to 'assistant'
    role: Literal["assistant"] = "assistant"

class SystemMessage(BaseMessage):
    """A message to set the persona or context for the AI."""
    # FIX: Renamed to 'role'
    role: Literal["system"] = "system"

# A union type to allow for any of the message types
MessageType = HumanMessage | AIMessage | SystemMessage
# File: src/my_framework/prompts/templates.py

from typing import Any, Dict, List
from pydantic import BaseModel

from .base import BasePromptTemplate
from ..core.schemas import MessageType, HumanMessage, AIMessage, SystemMessage

class MessagesPlaceholder(BaseModel):
    """A placeholder for a list of messages in a prompt template."""
    variable_name: str

# THE FIX IS ON THE LINE BELOW: The order of inheritance is swapped
class ChatPromptTemplate(BaseModel, BasePromptTemplate):
    """
    A template for creating a list of chat messages.
    """
    messages: List[MessageType | MessagesPlaceholder]
    
    class Config:
        arbitrary_types_allowed = True

    def format_prompt(self, **kwargs: Any) -> List[MessageType]:
        formatted_messages: List[MessageType] = []
        for msg_template in self.messages:
            if isinstance(msg_template, MessagesPlaceholder):
                history = kwargs.get(msg_template.variable_name, [])
                formatted_messages.extend(history)
            else:
                formatted_content = msg_template.content.format(**kwargs)
                if isinstance(msg_template, HumanMessage):
                    formatted_messages.append(HumanMessage(content=formatted_content))
                elif isinstance(msg_template, AIMessage):
                    formatted_messages.append(AIMessage(content=formatted_content))
                elif isinstance(msg_template, SystemMessage):
                    formatted_messages.append(SystemMessage(content=formatted_content))
        return formatted_messages
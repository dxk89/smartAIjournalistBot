# File: src/my_framework/models/base.py

from abc import abstractmethod
from typing import List
from pydantic import BaseModel

from ..core.runnables import Runnable
from ..core.schemas import AIMessage, MessageType, Document

class BaseChatModel(Runnable[List[MessageType], AIMessage]):
    """
    Abstract base class for a chat model.
    It standardizes the interface for interacting with any chat-based LLM.
    """
    
    @abstractmethod
    def invoke(self, input: List[MessageType], config=None) -> AIMessage:
        """
        Takes a list of messages and returns an AI message.
        """
        pass

class BaseEmbedding(BaseModel):
    """
    Abstract base class for an embedding model.
    It standardizes the interface for converting text into numerical vectors.
    """

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Takes a list of documents and returns a list of vector embeddings.
        """
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """
        Takes a single query text and returns its vector embedding.
        """
        pass
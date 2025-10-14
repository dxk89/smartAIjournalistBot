# File: src/my_framework/src/my_framework/models/openai.py
import json
import textwrap
from openai import OpenAI
from ..core.schemas import AIMessage, HumanMessage, SystemMessage, MessageType
from ..models.base import BaseChatModel
from typing import List
import os
from pantic import Field, BaseModel

# ---- JSON Helper Functions ---- #

def extract_first_json_block(text: str) -> str | None:
    """
    Finds the first balanced {...} or [...] JSON object in text.
    Returns the substring or None if not found.
    """
    start_brace = text.find("{")
    start_bracket = text.find("[")

    if start_brace == -1 and start_bracket == -1:
        return None

    if start_brace == -1:
        start = start_bracket
        start_char = '['
        end_char = ']'
    elif start_bracket == -1:
        start = start_brace
        start_char = '{'
        end_char = '}'
    else:
        if start_brace < start_bracket:
            start = start_brace
            start_char = '{'
            end_char = '}'
        else:
            start = start_bracket
            start_char = '['
            end_char = ']'
    
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == start_char:
            depth += 1
        elif c == end_char:
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None


def safe_load_json(maybe_json: str):
    """
    Safely loads JSON, even if the AI response has stray text.
    """
    # Try direct parse
    try:
        return json.loads(maybe_json)
    except Exception:
        pass

    # Try extracting first {...} block
    block = extract_first_json_block(maybe_json)
    if not block:
        raise ValueError("No JSON object found in model output.")

    # Clean up weird quotes or backticks
    cleaned = (
        block.replace("“", "\"")
             .replace("”", "\"")
             .replace("’", "'")
             .replace("`", "")
    )
    return json.loads(cleaned)


def normalize_article(doc: dict) -> dict:
    """
    Normalizes metadata fields into lists.
    """
    if isinstance(doc.get("seo_keywords"), str):
        doc["seo_keywords"] = [s.strip() for s in doc["seo_keywords"].split(",") if s.strip()]
    if isinstance(doc.get("hashtags"), str):
        doc["hashtags"] = [s.strip() for s in doc["hashtags"].split(",") if s.strip()]
    return doc


# ---- ChatOpenAI Wrapper Class ---- #

class ChatOpenAI(BaseModel, BaseChatModel):
    """
    A lightweight wrapper around OpenAI’s chat completions API that fits into the framework.
    """
    model_name: str = "gpt-5-nano"
    temperature: float = 0.5
    api_key: str | None = None
    max_completion_tokens: int = 2000
    client: OpenAI = Field(default=None, exclude=True)

    model_config = {
        "arbitrary_types_allowed": True,
        "protected_namespaces": ()
    }

    def __init__(self, **data):
        super().__init__(**data)
        self.client = OpenAI(api_key=self.api_key or os.environ.get("OPENAI_API_KEY"))

    def invoke(self, input: List[MessageType], config=None) -> AIMessage:
        """
        Send a list of messages to the chat model and return an AIMessage.
        """
        formatted_messages = []
        for m in input:
            if isinstance(m, (HumanMessage, AIMessage, SystemMessage)):
                formatted_messages.append(m.model_dump())
            elif isinstance(m, dict) and "role" in m and "content" in m:
                formatted_messages.append(m)
            else:
                raise ValueError(f"Unsupported message type: {m!r}")

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=formatted_messages,
            temperature=self.temperature,
            max_tokens=self.max_completion_tokens,
        )
        
        return AIMessage(content=response.choices[0].message.content)
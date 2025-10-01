# File: src/my_framework/parsers/standard.py

import json
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError

from .base import BaseOutputParser

# For Pydantic parser
T = TypeVar("T", bound=BaseModel)

class StrOutputParser(BaseOutputParser[str]):
    """The simplest parser, just returns the string content."""
    def parse(self, text: str) -> str:
        return text

class JsonOutputParser(BaseOutputParser[dict]):
    """Parses a JSON string from the LLM output into a Python dictionary."""
    def parse(self, text: str) -> dict:
        # The LLM might wrap the JSON in markdown code blocks
        clean_text = text.strip().removeprefix("```json").removesuffix("```").strip()
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON: {e}\n\nGot text: {text}") from e

class PydanticOutputParser(BaseOutputParser[T]):
    """
    Parses LLM output into a Pydantic model instance.
    """
    pydantic_model: Type[T]

    def __init__(self, *, pydantic_model: Type[T]):
        super().__init__()
        self.pydantic_model = pydantic_model

    def get_format_instructions(self) -> str:
        """Returns instructions for the LLM on how to format its output."""
        schema = self.pydantic_model.model_json_schema()
        
        # Reduced schema for brevity in the prompt
        reduced_schema = {
            "title": schema.get("title", ""),
            "description": schema.get("description", ""),
            "properties": schema.get("properties", {}),
            "required": schema.get("required", []),
        }

        return (
            "Please respond with a JSON object formatted according to the following schema:\n"
            "```json\n"
            f"{json.dumps(reduced_schema, indent=2)}\n"
            "```"
        )

    def parse(self, text: str) -> T:
        """Parses the text into an instance of the Pydantic model."""
        try:
            # First, try to parse it as JSON
            json_parser = JsonOutputParser()
            json_obj = json_parser.parse(text)
            # Then, validate and instantiate the Pydantic model
            return self.pydantic_model.model_validate(json_obj)
        except (ValidationError, ValueError) as e:
            raise ValueError(
                f"Failed to parse LLM output into Pydantic model {self.pydantic_model.__name__}.\n"
                f"Got error: {e}\nGot text: {text}"
            ) from e
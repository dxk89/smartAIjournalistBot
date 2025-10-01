# File: src/my_framework/agents/writer.py

from my_framework.core.runnables import Runnable
from my_framework.models.base import BaseChatModel
# UPDATED IMPORT PATH
from my_framework.tools.llm_calls import get_initial_draft

class WriterAgent(Runnable):
    """
    Takes a research brief and composes a high-quality first draft.
    """
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def invoke(self, input: dict, config=None) -> str:
        print("-> Writer Agent invoked")
        source_content = input.get("source_content")
        user_prompt = input.get("user_prompt")

        if not source_content or not user_prompt:
            return {"error": "Writer requires 'source_content' and 'user_prompt'."}

        draft = get_initial_draft(
            llm=self.llm,
            user_prompt=user_prompt,
            source_content=source_content
        )
        return draft
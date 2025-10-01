# File: src/my_framework/agents/summarizer.py

import logging
from my_framework.core.runnables import Runnable
from my_framework.models.base import BaseChatModel
from my_framework.core.schemas import SystemMessage, HumanMessage
from my_framework.apps import rules

class SummarizerAgent(Runnable):
    """
    Takes a long text and creates a concise summary.
    """
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def invoke(self, input: dict, config=None) -> str:
        logging.info("-> Summarizer Agent invoked")
        source_content = input.get("source_content")

        if not source_content:
            return {"error": "Summarizer requires 'source_content'."}

        prompt = [
            SystemMessage(content=rules.SUMMARIZER_SYSTEM_PROMPT),
            HumanMessage(content=f"Please summarize the following text:\n\n{source_content}")
        ]

        summary_response = self.llm.invoke(prompt)
        return summary_response.content
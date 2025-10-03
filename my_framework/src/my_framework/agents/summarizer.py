# File: src/my_framework/agents/summarizer.py

from my_framework.core.runnables import Runnable
from my_framework.models.base import BaseChatModel
from my_framework.core.schemas import SystemMessage, HumanMessage
from my_framework.apps import rules
from my_framework.agents.loggerbot import LoggerBot

class SummarizerAgent(Runnable):
    """
    Takes a long text and creates a concise summary.
    """
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel, logger=None):
        self.llm = llm
        self.logger = logger or LoggerBot.get_logger()

    def invoke(self, input: dict, config=None) -> str:
        self.logger.info("-> Summarizer Agent invoked")
        source_content = input.get("source_content")

        if not source_content:
            self.logger.error("Summarizer requires 'source_content'.")
            return {"error": "Summarizer requires 'source_content'."}

        self.logger.info("   - Generating summary...")
        prompt = [
            SystemMessage(content=rules.SUMMARIZER_SYSTEM_PROMPT),
            HumanMessage(content=f"Please summarize the following text:\n\n{source_content}")
        ]

        summary_response = self.llm.invoke(prompt)
        self.logger.info("   - Summary generated.")
        return summary_response.content
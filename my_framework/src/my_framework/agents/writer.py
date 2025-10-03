# File: src/my_framework/agents/writer.py

from my_framework.core.runnables import Runnable
from my_framework.models.base import BaseChatModel
# UPDATED IMPORT PATH
from my_framework.tools.llm_calls import get_initial_draft
from my_framework.agents.loggerbot import LoggerBot

class WriterAgent(Runnable):
    """
    Takes a research brief and composes a high-quality first draft.
    """
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel, logger=None):
        self.llm = llm
        self.logger = logger or LoggerBot.get_logger()

    def invoke(self, input: dict, config=None) -> str:
        self.logger.info("-> Writer Agent invoked")
        source_content = input.get("source_content")
        user_prompt = input.get("user_prompt")

        if not source_content or not user_prompt:
            self.logger.error("Writer requires 'source_content' and 'user_prompt'.")
            return {"error": "Writer requires 'source_content' and 'user_prompt'."}

        self.logger.info("   - Generating initial draft...")
        draft = get_initial_draft(
            llm=self.llm,
            user_prompt=user_prompt,
            source_content=source_content,
            logger=self.logger
        )
        self.logger.info("   - Initial draft generated.")
        return draft
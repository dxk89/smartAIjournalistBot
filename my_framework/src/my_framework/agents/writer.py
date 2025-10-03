# File: src/my_framework/agents/writer.py

from my_framework.core.runnables import Runnable
from my_framework.models.base import BaseChatModel
from my_framework.core.schemas import SystemMessage, HumanMessage
from my_framework.apps import rules
from my_framework.agents.loggerbot import LoggerBot

def get_initial_draft(llm: BaseChatModel, user_prompt: str, source_content: str, logger=None) -> str:
    """This function lives here to prevent circular imports."""
    log = logger or LoggerBot.get_logger()
    log.debug("-> Building prompt for initial draft.")
    draft_prompt = [
        SystemMessage(content=rules.WRITER_SYSTEM_PROMPT),
        HumanMessage(content=f"ADDITIONAL PROMPT INSTRUCTIONS: \"{user_prompt}\"\n\nSOURCE CONTENT:\n---\n{source_content[:8000]}\n---\n\nWrite the initial draft of the article now.")
    ]
    log.info("-> Sending request to LLM for initial draft...")
    draft_response = llm.invoke(draft_prompt)
    return draft_response.content

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
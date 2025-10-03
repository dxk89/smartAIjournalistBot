# File: src/my_framework/agents/publisher.py
from my_framework.core.runnables import Runnable
from my_framework.tools.cms_poster import post_article_to_cms
import json
from my_framework.agents.loggerbot import LoggerBot

class PublisherAgent(Runnable):
    """
    Handles the final steps of publishing to the CMS.
    """
    def __init__(self, logger=None):
        self.logger = logger or LoggerBot.get_logger()
        self.tools = [post_article_to_cms]

    def invoke(self, input: dict, config=None) -> str:
        self.logger.info("-> Publisher Agent invoked")
        article_json = input.get("article_json_string")
        username = input.get("username")
        password = input.get("password")

        # 1. Post to CMS
        self.logger.info("   - Posting article to CMS...")
        post_result = post_article_to_cms.func(article_json, username, password, self.logger)
        self.logger.info("   - CMS posting process completed.")
        
        return post_result
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

    def invoke(self, input: dict, config=None) -> str:
        self.logger.info("-> Publisher Agent invoked")
        
        article_json = input.get("article_json_string")
        username = input.get("username")
        password = input.get("password")

        # --- FIX: Hardcode URLs directly in the Publisher Agent ---
        login_url = "https://cms.intellinews.com/user/login"
        create_article_url = "https://cms.intellinews.com/node/add/article"
        self.logger.info(f"   - Using hardcoded Login URL: {login_url}")
        self.logger.info(f"   - Using hardcoded Create Article URL: {create_article_url}")

        if not all([article_json, username, password]):
            missing_params = [k for k, v in {"article_json": article_json, "username": username, "password": password}.items() if not v]
            error_msg = f"PublisherAgent missing required inputs: {', '.join(missing_params)}"
            self.logger.error(error_msg)
            return f"Error: {error_msg}"

        # 1. Post to CMS
        self.logger.info("   - Posting article to CMS...")
        post_result = post_article_to_cms(
            article_json=article_json,
            username=username,
            password=password,
            login_url=login_url,
            create_article_url=create_article_url,
            logger=self.logger
        )
        self.logger.info("   - CMS posting process completed.")
        
        return post_result
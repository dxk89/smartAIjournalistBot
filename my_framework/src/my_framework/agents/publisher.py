# File: src/my_framework/agents/publisher.py
from my_framework.core.runnables import Runnable
from my_framework.tools.cms_poster import post_article_to_cms
import json

class PublisherAgent(Runnable):
    """
    Handles the final steps of publishing to the CMS.
    """
    def __init__(self):
        self.tools = [post_article_to_cms]

    def invoke(self, input: dict, config=None) -> str:
        print("-> Publisher Agent invoked")
        article_json = input.get("article_json_string")
        username = input.get("username")
        password = input.get("password")

        # 1. Post to CMS
        post_result = post_article_to_cms.func(article_json, username, password)
        
        return post_result
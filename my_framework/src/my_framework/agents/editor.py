# File: src/my_framework/agents/editor.py

import json
from my_framework.core.runnables import Runnable
from my_framework.models.base import BaseChatModel
# UPDATED IMPORT PATH
from my_framework.tools.llm_calls import get_reflection, get_refined_article, get_seo_metadata
from my_framework.agents.loggerbot import LoggerBot

class EditorReflectorAgent(Runnable):
    """
    Critiques drafts for style, accuracy, and quality, and then refines them.
    Also handles metadata generation for the final article.
    """
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel, logger=None):
        self.llm = llm
        self.logger = logger or LoggerBot.get_logger()

    def invoke(self, input: dict, config=None) -> str:
        self.logger.info("-> Editor/Reflector Agent invoked")
        draft_article = input.get("draft_article")
        source_content = input.get("source_content")

        if not draft_article or not source_content:
            self.logger.error("Editor requires 'draft_article' and 'source_content'.")
            return {"error": "Editor requires 'draft_article' and 'source_content'."}

        # If the draft and source are the same, it's a pre-written article.
        # Skip reflection and refinement.
        if draft_article == source_content:
            self.logger.info("   - Pre-written article detected. Skipping reflection and refinement.")
            refined_article = draft_article
        else:
            # 1. Reflect
            self.logger.info("   - Critiquing draft...")
            reflection = get_reflection(self.llm, draft_article, source_content)
            self.logger.debug(f"   - Reflection received: {reflection[:100]}...")

            # 2. Refine
            self.logger.info("   - Refining article based on critique...")
            refined_article = get_refined_article(self.llm, draft_article, reflection)
            self.logger.info("   - Article refined.")

        # 3. Generate final metadata
        self.logger.info("   - Generating SEO metadata...")
        final_json_string = get_seo_metadata(self.llm, refined_article)
        self.logger.info("   - SEO metadata generated.")
        
        # Combine the refined article with its metadata
        try:
            parsed_data = json.loads(final_json_string)
            if "error" in parsed_data:
                 self.logger.error(f"   - Error in metadata generation: {parsed_data['error']}")
                 return final_json_string

            paragraphs = refined_article.strip().split('\n')
            body_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())
            parsed_data["body"] = body_html

            return json.dumps(parsed_data)
        # FIX: Broaden the exception clause to catch any potential errors
        except Exception as e:
            self.logger.error(f"   - Failed to merge refined article with metadata: {e}", exc_info=True)
            return json.dumps({"error": f"Failed to merge refined article with metadata: {e}"})
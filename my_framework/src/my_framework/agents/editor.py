# File: src/my_framework/agents/editor.py

import json
from my_framework.core.runnables import Runnable
from my_framework.models.base import BaseChatModel
# UPDATED IMPORT PATH
from my_framework.tools.llm_calls import get_reflection, get_refined_article, get_seo_metadata

class EditorReflectorAgent(Runnable):
    """
    Critiques drafts for style, accuracy, and quality, and then refines them.
    Also handles metadata generation for the final article.
    """
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def invoke(self, input: dict, config=None) -> str:
        print("-> Editor/Reflector Agent invoked")
        draft_article = input.get("draft_article")
        source_content = input.get("source_content")

        if not draft_article or not source_content:
            return {"error": "Editor requires 'draft_article' and 'source_content'."}

        # If the draft and source are the same, it's a pre-written article.
        # Skip reflection and refinement.
        if draft_article == source_content:
            print("   - Pre-written article detected. Skipping reflection and refinement.")
            refined_article = draft_article
        else:
            # 1. Reflect
            reflection = get_reflection(self.llm, draft_article, source_content)

            # 2. Refine
            refined_article = get_refined_article(self.llm, draft_article, reflection)

        # 3. Generate final metadata
        final_json_string = get_seo_metadata(self.llm, refined_article)
        
        # Combine the refined article with its metadata
        try:
            parsed_data = json.loads(final_json_string)
            if "error" in parsed_data:
                 return final_json_string

            paragraphs = refined_article.strip().split('\n')
            body_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())
            parsed_data["body"] = body_html

            return json.dumps(parsed_data)
        # FIX: Broaden the exception clause to catch any potential errors
        except Exception as e:
            return json.dumps({"error": f"Failed to merge refined article with metadata: {e}"})
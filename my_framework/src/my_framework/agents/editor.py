# File: src/my_framework/agents/editor.py
# FIXED VERSION - Proper callout length enforcement (232 chars max)

import json
from typing import List
from my_framework.core.runnables import Runnable
from my_framework.models.base import BaseChatModel
from my_framework.core.schemas import SystemMessage, HumanMessage
from my_framework.apps import rules
from my_framework.parsers.standard import PydanticOutputParser
from my_framework.apps.schemas import ArticleMetadata
from my_framework.agents.loggerbot import LoggerBot
from my_framework.agents.utils import COUNTRY_MAP, PUBLICATION_MAP, INDUSTRY_MAP

# --- LLM Call Functions ---

def _get_country_selection(llm: BaseChatModel, article_text: str, logger=None) -> List[str]:
    log = logger or LoggerBot.get_logger()
    country_names = list(COUNTRY_MAP.keys())
    prompt = [
        SystemMessage(content=rules.COUNTRY_SELECTION_SYSTEM_PROMPT),
        HumanMessage(content=f"AVAILABLE COUNTRIES:\n---\n{country_names}\n---\n\nARTICLE TEXT:\n---\n{article_text[:4000]}\n---")
    ]
    response = llm.invoke(prompt)
    log.debug(f"LLM raw response for countries: '{response.content}'")
    countries = [name.strip() for name in response.content.split(',') if name.strip() in country_names]
    return countries

def _get_publication_selection(llm: BaseChatModel, article_text: str, logger=None) -> List[str]:
    log = logger or LoggerBot.get_logger()
    publication_names = list(PUBLICATION_MAP.keys())
    prompt = [
        SystemMessage(content=rules.PUBLICATION_SELECTION_SYSTEM_PROMPT),
        HumanMessage(content=f"AVAILABLE PUBLICATIONS:\n---\n{publication_names}\n---\n\nARTICLE TEXT:\n---\n{article_text[:4000]}\n---")
    ]
    response = llm.invoke(prompt)
    log.debug(f"LLM raw response for publications: '{response.content}'")
    publications = [name.strip() for name in response.content.split(',') if name.strip() in publication_names]
    return publications

def _get_industry_selection(llm: BaseChatModel, article_text: str, logger=None) -> List[str]:
    log = logger or LoggerBot.get_logger()
    industry_names = list(INDUSTRY_MAP.keys())
    prompt = [
        SystemMessage(content=rules.INDUSTRY_SELECTION_SYSTEM_PROMPT),
        HumanMessage(content=f"AVAILABLE INDUSTRIES:\n---\n{industry_names}\n---\n\nARTICLE TEXT:\n---\n{article_text[:4000]}\n---")
    ]
    response = llm.invoke(prompt)
    log.debug(f"LLM raw response for industries: '{response.content}'")
    industries = [name.strip() for name in response.content.split(',') if name.strip() in industry_names]
    return industries

def _get_reflection(llm: BaseChatModel, draft_article: str, source_content: str, logger=None) -> str:
    log = logger or LoggerBot.get_logger()
    log.info("-> REFLECTION: Performing critique of the draft...")
    reflection_prompt_content = f"""
    You are a meticulous editor. Your task is to critique the following draft article based on several criteria.
    Provide a structured list of specific, actionable feedback points.
    CRITERIA:
    1.  **Factual Accuracy**: Compare the draft against the provided SOURCE CONTENT.
    2.  **Stylistic Adherence**: Review the draft for any violations of the house style guide.
    3.  **Clarity and Coherence**: Assess the overall flow, structure, and readability.
    SOURCE CONTENT:\n---\n{source_content[:8000]}\n---\n\nDRAFT ARTICLE TO CRITIQUE:\n---\n{draft_article[:8000]}\n---
    """
    messages = [
        SystemMessage(content=rules.EDITOR_REFLECTION_SYSTEM_PROMPT),
        HumanMessage(content=reflection_prompt_content)
    ]
    response = llm.invoke(messages)
    log.info("-> REFLECTION: Critique received.")
    return response.content

def _get_refined_article(llm: BaseChatModel, draft_article: str, reflection_feedback: str, logger=None) -> str:
    log = logger or LoggerBot.get_logger()
    log.info("-> REFINEMENT: Rewriting article based on feedback...")
    refinement_prompt_content = f"""
    You are a writer tasked with revising an article based on editor feedback.
    Your goal is to produce a final, polished version of the article that incorporates all the required changes.
    EDITOR FEEDBACK:\n---\n{reflection_feedback}\n---\n\nORIGINAL DRAFT ARTICLE:\n---\n{draft_article[:8000]}\n---
    """
    messages = [
        SystemMessage(content=rules.EDITOR_REFINEMENT_SYSTEM_PROMPT),
        HumanMessage(content=refinement_prompt_content)
    ]
    response = llm.invoke(messages)
    log.info("-> REFINEMENT: Final version generated.")
    return response.content

def _get_seo_metadata(llm: BaseChatModel, revised_article: str, logger=None) -> str:
    log = logger or LoggerBot.get_logger()
    log.info("-> Building structured prompt for main SEO metadata...")
    parser = PydanticOutputParser(pydantic_model=ArticleMetadata)
    main_metadata_prompt = [
        SystemMessage(content=rules.SEO_METADATA_SYSTEM_PROMPT),
        HumanMessage(content=f"{parser.get_format_instructions()}\n\nHere is the article to analyze:\n---\n{revised_article[:8000]}\n---")
    ]
    try:
        response = llm.invoke(main_metadata_prompt)
        parsed_output = parser.parse(response.content)
        metadata = parsed_output.model_dump()
        
        log.info("   - Getting country selection...")
        metadata['countries'] = _get_country_selection(llm, revised_article, log)
        log.info(f"   - Countries selected by LLM: {metadata['countries']}")

        log.info("   - Getting publication selection...")
        metadata['publications'] = _get_publication_selection(llm, revised_article, log)
        log.info(f"   - Publications selected by LLM: {metadata['publications']}")

        log.info("   - Getting industry selection...")
        metadata['industries'] = _get_industry_selection(llm, revised_article, log)
        log.info(f"   - Industries selected by LLM: {metadata['industries']}")
        
        # FIX: Ensure weekly_title matches title
        if 'title' in metadata:
            metadata['weekly_title_value'] = metadata['title']
            log.info(f"   - Set weekly_title_value = title")
        
        # ============================================================================
        # FIX #2: CALLOUT LENGTH ENFORCEMENT (232 CHARACTERS MAX)
        # ============================================================================
        
        # Extract first sentence for callouts
        paragraphs = revised_article.strip().split('\n')
        first_sentence = ""
        for p in paragraphs:
            p_clean = p.strip()
            if p_clean:
                # Split by period but handle edge cases
                sentences = p_clean.split('.')
                if sentences[0].strip():
                    first_sentence = sentences[0].strip() + '.'
                    break
        
        # Website callout = first sentence (max 232 chars - ENFORCED)
        if first_sentence:
            if len(first_sentence) > 232:
                # Truncate at word boundary before 229 chars (leave room for "...")
                truncated = first_sentence[:229].rsplit(' ', 1)[0] + '...'
                metadata['website_callout_value'] = truncated
                log.info(f"   - Set website_callout_value (truncated to {len(truncated)} chars)")
            else:
                metadata['website_callout_value'] = first_sentence
                log.info(f"   - Set website_callout_value ({len(first_sentence)} chars)")
        
        # Social media callout = first sentence + hashtags (max 232 chars - ENFORCED)
        if first_sentence and metadata.get('hashtags'):
            # Calculate available space for sentence
            hashtags_list = metadata['hashtags'][:3]  # Max 3 hashtags
            hashtags_str = ' '.join(hashtags_list)
            available_space = 232 - len(hashtags_str) - 1  # -1 for space between sentence and hashtags
            
            if len(first_sentence) > available_space:
                # Truncate sentence to fit with hashtags
                truncated_sentence = first_sentence[:available_space-3].rsplit(' ', 1)[0] + '...'
                social_callout = f"{truncated_sentence} {hashtags_str}"
            else:
                social_callout = f"{first_sentence} {hashtags_str}"
            
            # Final safety check
            if len(social_callout) > 232:
                social_callout = social_callout[:229] + '...'
            
            metadata['social_media_callout_value'] = social_callout
            log.info(f"   - Set social_media_callout_value with hashtags ({len(social_callout)} chars)")
        elif first_sentence:
            # No hashtags - just use sentence (with length check)
            if len(first_sentence) > 232:
                truncated = first_sentence[:229].rsplit(' ', 1)[0] + '...'
                metadata['social_media_callout_value'] = truncated
            else:
                metadata['social_media_callout_value'] = first_sentence
            log.info(f"   - Set social_media_callout_value without hashtags ({len(metadata['social_media_callout_value'])} chars)")
        
        # ============================================================================
        
        # Google news keywords = SEO keywords
        if metadata.get('seo_keywords'):
            metadata['google_news_keywords_value'] = metadata['seo_keywords']
            log.info(f"   - Set google_news_keywords_value = seo_keywords")
        
        # Abstract = title
        if 'title' in metadata:
            metadata['abstract_value'] = metadata['title']
            log.info(f"   - Set abstract_value = title")
        
        # Remove SEO description (auto-filled by CMS)
        if 'seo_description' in metadata:
            metadata.pop('seo_description')
            log.info(f"   - Removed seo_description (auto-filled by CMS)")
        
        # Byline should be empty by default
        metadata['byline_value'] = ""
        log.info(f"   - Set byline_value to empty (will be filled by CMS or left blank)")
        
        return json.dumps(metadata)
    except Exception as e:
        log.error(f"Failed to generate metadata: {e}", exc_info=True)
        return json.dumps({"error": f"Failed to generate metadata: {e}"})


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
        source_url = input.get("source_url")

        if not draft_article or not source_content:
            self.logger.error("Editor requires 'draft_article' and 'source_content'.")
            return {"error": "Editor requires 'draft_article' and 'source_content'."}

        if draft_article == source_content:
            self.logger.info("   - Pre-written article detected. Skipping reflection and refinement.")
            refined_article = draft_article
        else:
            self.logger.info("   - Critiquing draft...")
            reflection = _get_reflection(self.llm, draft_article, source_content, self.logger)
            self.logger.debug(f"   - Reflection received: {reflection[:100]}...")

            self.logger.info("   - Refining article based on critique...")
            refined_article = _get_refined_article(self.llm, draft_article, reflection, self.logger)
            self.logger.info("   - Article refined.")

        self.logger.info("   - Generating SEO metadata...")
        final_json_string = _get_seo_metadata(self.llm, refined_article, self.logger)
        self.logger.info("   - SEO metadata generated.")
        
        try:
            parsed_data = json.loads(final_json_string)
            if "error" in parsed_data:
                 self.logger.error(f"   - Error in metadata generation: {parsed_data['error']}")
                 return final_json_string

            # Exclude title from the body and add source URL
            paragraphs = refined_article.strip().split('\n')
            
            # The title is in metadata, so the body should not contain it.
            # Assuming refined_article contains the full text including title.
            # Let's remove the title from the article body.
            title = parsed_data.get('title', '')
            article_body_text = refined_article.replace(title, '', 1).strip()
            
            body_paragraphs = article_body_text.strip().split('\n')

            body_html = "".join(f"<p>{p.strip()}</p>" for p in body_paragraphs if p.strip())
            
            if source_url:
                body_html += f"<p>Source: <a href=\"{source_url}\">{source_url}</a></p>"
            
            parsed_data["body"] = body_html


            return json.dumps(parsed_data)
        except Exception as e:
            self.logger.error(f"   - Failed to merge refined article with metadata: {e}", exc_info=True)
            return json.dumps({"error": f"Failed to merge refined article with metadata: {e}"})
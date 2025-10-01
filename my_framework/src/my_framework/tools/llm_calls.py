# File: src/my_framework/tools/llm_calls.py

import json
from ..models.openai import ChatOpenAI
from ..core.schemas import SystemMessage, HumanMessage
from ..apps import rules
from ..parsers.standard import PydanticOutputParser
from ..apps.schemas import ArticleMetadata
from ..agents.utils import COUNTRY_MAP, PUBLICATION_MAP, INDUSTRY_MAP
from typing import List

def log(message):
    print(f"   - {message}", flush=True)

def get_initial_draft(llm: ChatOpenAI, user_prompt: str, source_content: str) -> str:
    log("-> Building prompt for initial draft.")
    draft_prompt = [
        SystemMessage(content=rules.WRITER_SYSTEM_PROMPT),
        HumanMessage(content=f"ADDITIONAL PROMPT INSTRUCTIONS: \"{user_prompt}\"\n\nSOURCE CONTENT:\n---\n{source_content[:8000]}\n---\n\nWrite the initial draft of the article now.")
    ]
    log("-> Sending request to LLM for initial draft...")
    draft_response = llm.invoke(draft_prompt)
    return draft_response.content

def get_reflection(llm: ChatOpenAI, draft_article: str, source_content: str) -> str:
    log("-> REFLECTION: Performing critique of the draft...")
    reflection_prompt_content = f"""
    You are a meticulous editor. Your task is to critique the following draft article based on several criteria.
    Provide a structured list of specific, actionable feedback points.

    CRITERIA:
    1.  **Factual Accuracy**: Compare the draft against the provided SOURCE CONTENT. Identify any claims in the draft that are not supported by the source.
    2.  **Stylistic Adherence**: Review the draft for any violations of the house style guide.
    3.  **Clarity and Coherence**: Assess the overall flow, structure, and readability.

    SOURCE CONTENT:
    ---
    {source_content[:8000]}
    ---

    DRAFT ARTICLE TO CRITIQUE:
    ---
    {draft_article[:8000]}
    ---
    """
    messages = [
        SystemMessage(content=rules.EDITOR_REFLECTION_SYSTEM_PROMPT),
        HumanMessage(content=reflection_prompt_content)
    ]
    response = llm.invoke(messages)
    log("-> REFLECTION: Critique received.")
    return response.content

def get_refined_article(llm: ChatOpenAI, draft_article: str, reflection_feedback: str) -> str:
    log("-> REFINEMENT: Rewriting article based on feedback...")
    refinement_prompt_content = f"""
    You are a writer tasked with revising an article based on editor feedback.
    Your goal is to produce a final, polished version of the article that incorporates all the required changes.

    EDITOR FEEDBACK:
    ---
    {reflection_feedback}
    ---

    ORIGINAL DRAFT ARTICLE:
    ---
    {draft_article[:8000]}
    ---
    """
    messages = [
        SystemMessage(content=rules.EDITOR_REFINEMENT_SYSTEM_PROMPT),
        HumanMessage(content=refinement_prompt_content)
    ]
    response = llm.invoke(messages)
    log("-> REFINEMENT: Final version generated.")
    return response.content

def get_seo_metadata(llm: ChatOpenAI, revised_article: str) -> str:
    log("-> Building structured prompt for main SEO metadata...")
    parser = PydanticOutputParser(pydantic_model=ArticleMetadata)
    main_metadata_prompt = [
        SystemMessage(content=rules.SEO_METADATA_SYSTEM_PROMPT),
        HumanMessage(content=f"{parser.get_format_instructions()}\n\nHere is the article to analyze:\n---\n{revised_article[:8000]}\n---")
    ]
    
    try:
        response = llm.invoke(main_metadata_prompt)
        parsed_output = parser.parse(response.content)
        metadata = parsed_output.model_dump()
        
        metadata['countries'] = get_country_selection(llm, revised_article)
        metadata['publications'] = get_publication_selection(llm, revised_article)
        metadata['industries'] = get_industry_selection(llm, revised_article)
        
        return json.dumps(metadata)
    except Exception as e:
        return json.dumps({"error": f"Failed to generate metadata: {e}"})

def get_country_selection(llm: ChatOpenAI, article_text: str) -> List[str]:
    country_names = list(COUNTRY_MAP.keys())
    prompt = [
        SystemMessage(content=rules.COUNTRY_SELECTION_SYSTEM_PROMPT),
        HumanMessage(content=f"AVAILABLE COUNTRIES:\n---\n{country_names}\n---\n\nARTICLE TEXT:\n---\n{article_text[:4000]}\n---")
    ]
    response = llm.invoke(prompt)
    return [name.strip() for name in response.content.split(',')]

def get_publication_selection(llm: ChatOpenAI, article_text: str) -> List[str]:
    publication_names = list(PUBLICATION_MAP.keys())
    prompt = [
        SystemMessage(content=rules.PUBLICATION_SELECTION_SYSTEM_PROMPT),
        HumanMessage(content=f"AVAILABLE PUBLICATIONS:\n---\n{publication_names}\n---\n\nARTICLE TEXT:\n---\n{article_text[:4000]}\n---")
    ]
    response = llm.invoke(prompt)
    return [name.strip() for name in response.content.split(',')]

def get_industry_selection(llm: ChatOpenAI, article_text: str) -> List[str]:
    industry_names = list(INDUSTRY_MAP.keys())
    prompt = [
        SystemMessage(content=rules.INDUSTRY_SELECTION_SYSTEM_PROMPT),
        HumanMessage(content=f"AVAILABLE INDUSTRIES:\n---\n{industry_names}\n---\n\nARTICLE TEXT:\n---\n{article_text[:4000]}\n---")
    ]
    response = llm.invoke(prompt)
    return [name.strip() for name in response.content.split(',')]
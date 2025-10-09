# File: src/my_framework/style_guru/deep_analyzer.py

import os
import json
import re
import feedparser
from ..models.openai import ChatOpenAI
from ..core.schemas import SystemMessage, HumanMessage
from ..agents.loggerbot import LoggerBot
from ..models.openai import safe_load_json

# --- CONFIGURATION ---
RSS_FEEDS = [
    "https://www.intellinews.com/rss/0/0/",
    "https://www.intellinews.com/rss/0/1/",
    "https://www.intellinews.com/rss/0/2/",
    "https://www.intellinews.com/rss/0/3/",
    "https://www.intellinews.com/rss/0/4/",
    "https://www.intellinews.com/rss/0/5/"
]
DEEP_ANALYSIS_PROMPT = """
You are a senior editor at IntelliNews, tasked with analyzing a batch of articles to create a definitive style guide for a new AI writing assistant. Your analysis must be incredibly detailed, covering everything from high-level structure to subtle nuances of tone and punctuation.

Analyze the following articles and produce a JSON object that codifies the "IntelliNews Style".

Your JSON output MUST include the following sections:
1.  **tone_and_voice**: Describe the overall tone. Is it formal, neutral, analytical, objective? What is the voice? (e.g., "Authoritative, expert, and slightly detached"). Provide principles for maintaining this tone.
2.  **structure**: Detail the typical article structure.
    * **headline**: Analyze the capitalization (e.g., "Title Case"), length, and style. Are they direct or creative?
    * **dateline**: Specify the exact format (e.g., "CITY, Country –").
    * **lead_paragraph**: Describe its purpose and structure. Is it a direct summary (inverted pyramid)? How long is it?
    * **body_paragraphs**: Typical length, use of subheadings (and their format), and how they develop the story.
    * **quotes**: How are quotes attributed (e.g., "...," he said.)? How are they integrated?
3.  **language_and_grammar**:
    * **vocabulary**: Preferred terminology, level of complexity, and any words to avoid (e.g., jargon, clichés).
    * **punctuation**: Rules for commas (e.g., Oxford comma usage), hyphens vs. dashes, etc.
    * **numbers_and_dates**: Rules for writing out numbers vs. using digits. Specify date format (e.g., "Month Day").
    * **acronyms**: How are they introduced (e.g., "European Union (EU)")?
4.  **formatting_and_presentation**:
    * **bolding_and_italics**: How and when are they used? For emphasis? For foreign words?
    * **hyperlinks**: How is hyperlink text phrased?
5.  **content_rules**:
    * **sourcing_and_attribution**: How are sources cited within the text?
    * **objectivity**: Principles for maintaining a neutral, fact-based perspective.

Here are the articles:
---
{articles_text}
---
"""
FRAMEWORK_FILE = "intellinews_style_framework.json"

def get_articles_from_rss(max_articles, logger):
    """Fetches and cleans articles from RSS feeds."""
    logger.info(f"   - Fetching up to {max_articles} articles from {len(RSS_FEEDS)} RSS feeds...")
    articles = []
    seen_links = set()

    for feed_url in RSS_FEEDS:
        if len(articles) >= max_articles:
            break
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                if len(articles) >= max_articles:
                    break
                if entry.link not in seen_links:
                    seen_links.add(entry.link)
                    # Basic cleaning
                    summary = re.sub('<[^<]+?>', '', entry.summary)
                    articles.append({"title": entry.title, "summary": summary})
        except Exception as e:
            logger.error(f"   - ❌ Could not parse RSS feed {feed_url}: {e}")
            
    logger.info(f"   - ✅ Fetched {len(articles)} unique articles.")
    return articles

def deep_style_analysis(max_articles: int = 100):
    """
    Performs a deep analysis of articles from RSS feeds to generate a style framework.
    """
    logger = LoggerBot.get_logger()
    logger.info("=" * 70)
    logger.info("🎨 STARTING STYLE GURU DEEP ANALYSIS")
    logger.info("=" * 70)

    # Step 1: Get articles
    articles = get_articles_from_rss(max_articles, logger)
    if not articles:
        logger.error("   - ❌ No articles found. Aborting.")
        return None

    # Step 2: Format for LLM
    articles_text = "\n\n---\n\n".join([f"Title: {a['title']}\n\n{a['summary']}" for a in articles])
    
    # Step 3: Run analysis with LLM
    try:
        logger.info("   - 🧠 Sending articles to LLM for deep analysis (this may take several minutes)...")
        llm = ChatOpenAI(model_name="gpt-4o", temperature=0.2)
        
        messages = [
            SystemMessage(content=DEEP_ANALYSIS_PROMPT.format(articles_text=articles_text))
        ]
        
        response = llm.invoke(messages)
        framework_json = safe_load_json(response.content)
        
        logger.info("   - ✅ LLM analysis complete.")
        
    except Exception as e:
        logger.critical(f"   - 🔥 LLM analysis failed: {e}", exc_info=True)
        return None

    # Step 4: Save the framework
    try:
        framework_json["articles_analyzed"] = len(articles)
        framework_json["version"] = "2.0"
        
        # Determine the correct path to the framework file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        framework_path = os.path.join(os.path.dirname(os.path.dirname(script_dir)), FRAMEWORK_FILE)
        
        with open(framework_path, "w", encoding='utf-8') as f:
            json.dump(framework_json, f, indent=4)
            
        logger.info(f"   - ✅ Style framework saved to '{framework_path}'")
        
    except Exception as e:
        logger.error(f"   - 🔥 Failed to save style framework: {e}", exc_info=True)
        return None
        
    logger.info("="*70)
    logger.info("🎨 DEEP ANALYSIS COMPLETE")
    logger.info("="*70)
    
    return framework_json

if __name__ == '__main__':
    deep_style_analysis(max_articles=100)
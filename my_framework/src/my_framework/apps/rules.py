# File: src/my_framework/apps/rules.py

import re
import numpy as np
import nltk
from collections import Counter
import json
import os
from ..agents.tools import tool
from ..models.openai import ChatOpenAI
from ..core.schemas import SystemMessage, HumanMessage
from ..style_guru.training import fetch_rss
from ..style_guru.model import AdvancedNeuralAgent
from ..style_guru.features import text_features

# Download necessary NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)
try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger', quiet=True)


@tool
def style_scoring_tool(article_text: str) -> float:
    """Score an article's adherence to IntelliNews style."""
    feats = text_features(article_text).reshape(1, -1)
    agent = AdvancedNeuralAgent(input_size=feats.shape[1])
    try:
        agent.load("data/model_weights.npz")
        score = agent.predict(feats)[0, 0]
        return score
    except Exception as e:
        return 0.0


def analyze_articles_with_llm(text: str, api_key: str) -> dict:
    """
    Perform LLM-based stylistic analysis on article text.
    This provides deeper insights beyond basic statistics.
    """
    llm = ChatOpenAI(api_key=api_key, model_name="gpt-4o", temperature=0)
    
    prompt = f"""
    Analyze the following article text to create a style profile.
    Provide your response as a single, valid JSON object with the following keys:
    - "pos_distribution": An object showing the percentage distribution of the top 5 parts of speech (e.g., {{"NOUN": "25.3%", "VERB": "18.1%"}}).
    - "top_bigrams": A list of the 5 most common and meaningful two-word phrases.
    - "top_trigrams": A list of the 5 most common and meaningful three-word phrases.
    - "quote_density": An estimated number of direct quotes per 1000 words.
    - "top_attribution_verbs": The 3 most common verbs used to attribute quotes (e.g., said, according to, stated).
    - "signposting_freq": An object showing the count of common transition words like 'however', 'meanwhile', etc.
    - "compression_ratio": An estimated percentage of the text that is information-dense (entities and numbers).

    ARTICLE TEXT:
    ---
    {text[:8000]} 
    ---
    """
    
    messages = [
        SystemMessage(content="You are an expert linguistic analyst. Your output is only a single valid JSON object."),
        HumanMessage(content=prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        # Remove markdown and clean up the response
        clean_response = response.content.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(clean_response)
    except Exception as e:
        return {}


def get_writing_style_guide():
    """
    Generate a comprehensive style guide from recent IntelliNews articles.
    Returns actual writing examples and patterns, not just statistics.
    """
    articles = fetch_rss()
    
    if not articles or len(articles) < 3:
        return None
    
    # Take the 5 most recent articles as examples
    sample_articles = articles[:5]
    
    # Build the style sheet with actual examples
    style_sheet = """
=================================================================
INTELLINEWS HOUSE STYLE GUIDE (Generated from Recent Articles)
=================================================================

CRITICAL: This is the EXACT style you must match. Study these examples carefully.

-------------------------------------------------------------------
SECTION 1: OPENING PARAGRAPH EXAMPLES (Study These Carefully)
-------------------------------------------------------------------

These are REAL opening paragraphs from recent IntelliNews articles.
Your articles MUST follow this exact style and structure:

"""
    
    # Add actual opening paragraphs as examples
    for i, article in enumerate(sample_articles, 1):
        paragraphs = article['text'].split('\n\n')
        if paragraphs:
            first_para = paragraphs[0].strip()
            if first_para and len(first_para) > 50:
                style_sheet += f"""
Example {i} - "{article['title']}":
{first_para}

"""
    
    # Analyze all articles for patterns
    all_text = " ".join([article['text'] for article in articles])
    sentences = nltk.sent_tokenize(all_text)
    words = nltk.word_tokenize(all_text)
    
    # Calculate statistics
    avg_sentence_length = np.mean([len(nltk.word_tokenize(s)) for s in sentences]) if sentences else 0
    em_dash_freq = all_text.count('—') / len(words) * 1000 if words else 0
    semicolon_freq = all_text.count(';') / len(words) * 1000 if words else 0
    
    # Extract common sentence starters
    sentence_starters = []
    for sent in sentences[:50]:  # First 50 sentences
        words_in_sent = nltk.word_tokenize(sent)
        if len(words_in_sent) >= 2:
            starter = ' '.join(words_in_sent[:2])
            sentence_starters.append(starter)
    
    common_starters = Counter(sentence_starters).most_common(10)
    
    # Extract common phrases (bigrams and trigrams)
    bigrams = list(nltk.bigrams(words))
    trigrams = list(nltk.trigrams(words))
    
    # Filter for meaningful phrases (exclude stopwords at start)
    stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
    meaningful_bigrams = [' '.join(bg) for bg in bigrams if bg[0].lower() not in stopwords]
    meaningful_trigrams = [' '.join(tg) for tg in trigrams if tg[0].lower() not in stopwords]
    
    common_bigrams = Counter(meaningful_bigrams).most_common(10)
    common_trigrams = Counter(meaningful_trigrams).most_common(10)
    
    style_sheet += f"""
-------------------------------------------------------------------
SECTION 2: STRUCTURAL PATTERNS
-------------------------------------------------------------------

Average Sentence Length: {avg_sentence_length:.1f} words
- Keep sentences between 15-25 words for optimal readability
- Vary sentence length to maintain reader interest
- Lead sentences can be slightly longer (25-30 words)

Punctuation Usage:
- Em dash frequency: {em_dash_freq:.2f} per 1000 words
- Semicolon frequency: {semicolon_freq:.2f} per 1000 words
- Use em dashes (—) for emphasis or additional information
- Use semicolons sparingly for complex lists or closely related clauses

Common Sentence Starters (Use these patterns):
"""
    
    for starter, count in common_starters:
        style_sheet += f"  • {starter}...\n"
    
    style_sheet += f"""

Common Two-Word Phrases:
"""
    for phrase, count in common_bigrams[:8]:
        style_sheet += f"  • {phrase}\n"
    
    style_sheet += f"""

Common Three-Word Phrases:
"""
    for phrase, count in common_trigrams[:8]:
        style_sheet += f"  • {phrase}\n"
    
    # Optional: Add LLM analysis if API key is available
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            llm_analysis = analyze_articles_with_llm(all_text, api_key)
            if llm_analysis:
                style_sheet += f"""

-------------------------------------------------------------------
SECTION 3: ADVANCED LINGUISTIC PATTERNS (LLM Analysis)
-------------------------------------------------------------------

Part of Speech Distribution:
"""
                if 'pos_distribution' in llm_analysis:
                    for pos, pct in llm_analysis['pos_distribution'].items():
                        style_sheet += f"  • {pos}: {pct}\n"
                
                if 'top_attribution_verbs' in llm_analysis:
                    style_sheet += f"""
Attribution Verbs (Use these):
"""
                    for verb in llm_analysis['top_attribution_verbs']:
                        style_sheet += f"  • {verb}\n"
                
                if 'quote_density' in llm_analysis:
                    style_sheet += f"""
Quote Density: {llm_analysis['quote_density']} quotes per 1000 words
- Include direct quotes from sources
- Always attribute quotes properly
"""
    except Exception as e:
        pass
    
    style_sheet += """

-------------------------------------------------------------------
SECTION 4: WRITING RULES (MANDATORY)
-------------------------------------------------------------------

STRUCTURE:
1. Lead with the most newsworthy fact in the first sentence
2. Second sentence provides essential context
3. Third paragraph adds details and background
4. Include source attribution throughout
5. End with forward-looking statement or context

TONE & STYLE:
• Objective and factual - no editorial opinions
• Professional but readable - avoid jargon
• Active voice preferred (e.g., "The company announced" not "It was announced")
• British English spelling (favour, colour, organisation)
• Numbers: spell out one through nine, use digits for 10+

ATTRIBUTION:
• Use "said" for direct quotes (most common)
• Acceptable: "according to", "stated", "told reporters"
• Avoid: "claimed", "alleged" (unless legally necessary)
• Always attribute information to specific sources

FORBIDDEN WORDS & PHRASES (NEVER USE):
• Furthermore, Moreover, Additionally, Consequently
• Nevertheless, Subsequently, In essence
• It's worth noting that, It's important to understand
• Various, Numerous, Myriad, Plethora
• Comprehensive, Robust, Dynamic, Innovative, Cutting-edge
• Delve, Dive into, Unpack

DATES & NUMBERS:
• Never use future dates
• Format: "15 January 2024" or "January 15, 2024"
• Always verify dates match the source
• Currency: "$1.5bn" or "$1.5 billion" (spell out for amounts over $1mn)

-------------------------------------------------------------------
SECTION 5: EXAMPLES OF WHAT NOT TO DO
-------------------------------------------------------------------

❌ BAD: "The company is poised to leverage cutting-edge technology."
✅ GOOD: "The company plans to use new technology."

❌ BAD: "It's worth noting that the market has seen robust growth."
✅ GOOD: "The market grew 15% last year."

❌ BAD: "Furthermore, the CEO stated..."
✅ GOOD: "The CEO said..."

❌ BAD: "**This is important.**"
✅ GOOD: "This is important." (NO markdown formatting)

❌ BAD: "The innovative startup is disrupting the industry."
✅ GOOD: "The startup has entered the market with a new approach."

-------------------------------------------------------------------
CRITICAL REMINDERS:
-------------------------------------------------------------------

1. NO MARKDOWN FORMATTING (**, *, _, etc.) - Write in plain text only
2. Match the examples above - study the opening paragraphs carefully
3. Lead with facts, not context or background
4. Keep it concise and newsworthy
5. Always cite sources for claims
6. British English spelling throughout
7. Write like a professional journalist, not an AI

=================================================================
"""
    
    # Save to file for reference
    try:
        with open("latest_style_sheet.txt", "w", encoding="utf-8") as f:
            f.write(style_sheet)
    except Exception as e:
        pass
    
    return style_sheet


# --- AGENT SYSTEM PROMPTS ----------------------------------------------------
ORCHESTRATOR_SYSTEM_PROMPT = """
You are the "Editor-in-Chief," a master orchestrator of a digital newsroom. Your job is to create a step-by-step plan to fulfill the user's request.

You have the following agents available:
- `research`: Scrapes content from a URL or reads from a Google Sheet. Use this first for URL-based tasks.
- `write`: Takes source content and a user prompt to write a first draft.
- `edit`: Takes a draft and source content, reflects on it, and refines it. It also generates all the necessary metadata.
- `publish`: Takes the final article JSON and posts it to the CMS and logs it to a Google Sheet.

Based on the user's goal, create a JSON list of steps. Each step must be a dictionary with an "agent" and a "task" key. The task dictionary should contain the specific inputs for that agent.

**Example Plan:**
If the user provides a URL, the plan should look like this:
```json
[
  {
    "agent": "research",
    "task": {
      "source_url": "{source_url}"
    }
  },
  {
    "agent": "write",
    "task": {
      "source_content": "{step_1_output}",
      "user_prompt": "{user_goal}"
    }
  },
  {
    "agent": "edit",
    "task": {
      "draft_article": "{step_2_output}",
      "source_content": "{step_1_output}",
      "source_url": "{source_url}"
    }
  },
  {
    "agent": "publish",
    "task": {
      "article_json_string": "{step_3_output}",
      "username": "{username}",
      "password": "{password}",
      "sheet_url": "{sheet_url}",
      "worksheet_name": "{worksheet_name}"
    }
  }
]"""

SUMMARIZER_SYSTEM_PROMPT = "You are an expert summarization engine. Create a concise, factual summary of the provided text, ensuring all key names, dates, locations, and financial figures are retained. The summary should be dense with information and ready for a journalist to use as a source."

WRITER_SYSTEM_PROMPT = get_writing_style_guide()

EDITOR_FACT_CHECK_SYSTEM_PROMPT = f"""You are a journalist for a news agency IntelliNews.

You must write a draft article in English in the style of the Financial Times using the provided text and retaining all quotes.

Write in a news article style following these guidelines:

**Headlines:**
- Use sentence case only (first word capitalized).
- Headlines must be clear and informative.
- No clickbait or questions in headlines.
- Always include the country in the title of the story.
- Never use "emphasised" in headlines.
- Never write days of the week in headlines.
- No colons in headlines.

**Numbers:**
- Write out numbers under ten, except when in headlines.
- Use digits for numbers 10 and above.
- Use "mn" for million and "bn" for billion.
- Always provide the USD equivalent after a local currency using the format: "AED19.95bn ($5.43bn)".
- Use three-letter currency codes (except for $).
- Use the percentage sign (%) instead of writing out the word "percent".

**Dates and Attribution:**
- Write dates as "on February 10" (not Feb 10 or February 10th).
- Include the source and date in the first paragraph, like this: "*Publication Name* reported on February 10".
- Never write the day of the week (e.g., "Monday", "Tuesday").
- Italicize the names of news agencies or newspapers when citing them as a source. Do not italicize government ministries.
- Format the final source citation as "Source. Source Name" with no quotation marks or asterisks, and with only the first letter of the source name capitalized.

**Language:**
- Use British English spelling exclusively (e.g., organisation, centre, programme).
- Never use "emphasized" or "underscored" unless it is part of a direct quote.
- Maintain a formal and objective tone.
- Use full job titles on the first reference.
- Italicize publication names using asterisks (*Publication Name*).

**Structure:**
- The first paragraph must be sharp and to the point, leading with the most important information.
- Each subsequent paragraph should add detail in decreasing order of importance.
- Include relevant quotes with proper attribution.
- Write in a straight news style, with no summaries or analysis paragraphs.
- Do not use bullet points or numbered lists unless specifically requested.
- Each paragraph should be able to be cut from the bottom without losing the core news value of the story.
- End the article with a relevant quote or fact, not a summary.
- NEVER fabricate or invent facts, people, or quotes that are not in the original source text.
- If a source is in English, you must rephrase and rewrite the content to avoid copyright infringement.
- Keep the article around 300-350 words, or shorter if the source text is brief.
- NEVER ADD a conclusion paragraph. You are emulating the AP style.
- DO NOT write "reflects" or an explainer as the last sentence.

**Style:**
- Avoid unnecessary adjectives and editorial commentary.
- Maintain an objective tone throughout.
- At the end of the article, you must include tags (not hashtags) and a 250-character website callout.

**Forbidden Words and Phrases:**
YOU MUST NEVER USE THESE WORDS:
- "Furthermore", "Moreover", "Additionally", "Consequently", "Nevertheless", "Subsequently", "In essence", "It's worth noting that", "It's important to understand"

Overused Qualifiers to Avoid:
- "Various", "Numerous", "Myriad", "Plethora", "Multifaceted", "Comprehensive", "Robust", "Dynamic", "Innovative", "Cutting-edge"

Generic Descriptors to Avoid:
- "Landscape" (as in "the digital landscape"), "Ecosystem", "Framework", "Paradigm", "Game-changer", "Revolutionary", "Seamless", "Holistic", "Strategic", "Optimise"

Hedging Language to Avoid:
- "Arguably", "Potentially", "Seemingly", "Presumably", "Essentially", "Fundamentally", "Inherently", "Particularly"

Conclusion Starters to Avoid:
- "In conclusion", "To summarise", "In summary", "All things considered", "Ultimately"

Business Buzzwords to Avoid:
- "Leverage", "Synergy", "Scalable", "Streamline", "Enhance", "Facilitate", "Implement"

You must follow these rules: {get_writing_style_guide()}
"""

EDITOR_REFLECTION_SYSTEM_PROMPT = "You are a critical editor providing structured feedback on a draft. Analyze it for factual accuracy against the source, stylistic adherence, and overall clarity. CRITICAL: Ensure the draft contains NO markdown formatting like ** or other special characters."

EDITOR_REFINEMENT_SYSTEM_PROMPT = "You are a writer tasked with revising an article based on specific editor feedback. CRITICAL: Your output must be in plain text with NO markdown formatting (**, *, _, etc.). Write naturally without any special formatting characters. Your goal is to produce a final, polished version that incorporates all the required changes."

SEO_METADATA_SYSTEM_PROMPT = f"""You are an expert sub-editor generating metadata for an article.

CRITICAL FORMATTING RULES:
- Do NOT use markdown formatting (**, *, _, etc.) anywhere in your output
- All text must be plain text without any special formatting characters
- Write naturally and professionally
- The JSON values should contain plain text only

Your task is to generate a valid JSON object with creative and SEO-related metadata for an article. Do NOT include 'publications', 'countries', or 'industries' in this JSON object.

CRITICAL DROPDOWN FIELD RULES - You MUST choose from these EXACT options:

"daily_subject_value" - Choose EXACTLY ONE from:
  - "Macroeconomic News"
  - "Banking And Finance"
  - "Companies and Industries"
  - "Political"

"key_point_value" - Choose EXACTLY ONE from:
  - "Yes"
  - "No"

"machine_written_value" - Choose EXACTLY ONE from:
  - "Yes"
  - "No"

"ballot_box_value" - Choose EXACTLY ONE from:
  - "Yes"  (ONLY if article is about elections)
  - "No"

For regional sections, if the article is about a specific country/region, choose the MOST SPECIFIC option:

"africa_daily_section_value" - Choose ONE from: "- None -", "Regional News", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi", "Cameroon", "Cape Verde", "Central African Republic", "Chad", "Comoros", "Congo", "Cote d'Ivoire", "Democratic Republic of Congo", "Djibouti", "Egypt", "Equatorial Guinea", "Eritrea", "Ethiopia", "Gabon", "Gambia", "Ghana", "Guinea", "Guinea-Bissau", "Kenya", "Lesotho", "Liberia", "Madagascar", "Malawi", "Mali", "Mauritania", "Mauritius", "Mayotte", "Morocco", "Mozambique", "Namibia", "Niger", "Nigeria", "Réunion", "Rwanda", "Saint Helena, Ascension and Tristan da Cunha", "Sao Tome and Principe", "Senegal", "Seychelles", "Sierra Leone", "Somalia", "South Africa", "South Sudan", "Sudan", "Swaziland", "Tanzania", "Togo", "Uganda", "Zambia", "Zimbabwe"

"southeast_europe_today_sections_value" - Choose ONE from: "- None -", "Albania", "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Montenegro", "North Macedonia", "Romania", "Serbia", "Turkey"

"cee_news_watch_country_sections_value" - Choose ONE from: "- None -", "Albania", "Armenia", "Azerbaijan", "Baltic States", "Belarus", "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Czech Republic", "Georgia", "Hungary", "Kazakhstan", "Kosovo", "Kyrgyzstan", "Moldova", "Montenegro", "North Macedonia", "Poland", "Romania", "Russia", "Serbia", "Slovakia", "Slovenia", "Tajikistan", "Turkey", "Turkmenistan", "Ukraine", "Uzbekistan"

"n_africa_today_section_value" - Choose ONE from: "- None -", "Regional", "Algeria", "Bahrain", "Egypt", "Jordan", "Libya", "Morocco", "Syria", "Tunisia"

"middle_east_today_section_value" - Choose ONE from: "- None -", "Bahrain", "Iran", "Iraq", "Israel", "Kuwait", "Lebanon", "Oman", "Palestine", "Qatar", "Saudia Arabia", "UAE", "Yemen"

"baltic_states_today_sections_value" - Choose ONE from: "- None -", "Estonia", "Latvia", "Lithuania"

"asia_today_sections_value" - Choose ONE from: "- None -", "Bangladesh", "Bhutan", "Brunei", "Cambodia", "China", "Hong Kong", "India", "Indonesia", "Japan", "Laos", "Malaysia", "Myanmar", "Nepal", "Pakistan", "Philippines", "Singapore", "South Korea", "Sri Lanka", "Taiwan", "Thailand", "Vietnam"

"latam_today_value" - Choose ONE from: "- None -", "Argentina", "Belize", "Bolivia", "Brazil", "Chile", "Columbia", "Costa Rica", "Ecuador", "El Salvador", "French Guiana", "Guatemala", "Guyana", "Honduras", "Mexico", "Nicaragua", "Panama", "Paraguay", "Peru", "Suriname", "Uruguay", "Venezuela"

DEFAULT VALUES IF UNSURE:
- daily_subject_value: "Companies and Industries"
- key_point_value: "No"
- machine_written_value: "Yes"
- ballot_box_value: "No"
- All regional sections: "- None -" (unless article clearly pertains to that region)

You must follow these rules: {get_writing_style_guide()}"""

COUNTRY_SELECTION_SYSTEM_PROMPT = "You are an expert data extractor. Your only task is to identify the main country or countries discussed in the provided article text. You must choose from the list of available countries. Your response must be a single, comma-separated string of the selected country names."

PUBLICATION_SELECTION_SYSTEM_PROMPT = "You are an expert sub-editor. Your only task is to select the most appropriate publications for an article from a provided list. You must choose the MOST SPECIFIC publication possible. Your response must be a single, comma-separated string of the selected publication names."

INDUSTRY_SELECTION_SYSTEM_PROMPT = "You are an expert data analyst. Your only task is to select the most relevant industries for an article from a provided list. You must choose the MOST SPECIFIC industry possible, and you MUST select at least one industry. Your response must be a single, comma-separated string of the selected industry names."
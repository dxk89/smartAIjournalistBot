# File: src/my_framework/style_guru/analyzer.py

import re
import numpy as np
import nltk
from collections import Counter
import json
import os
from ..agents.tools import tool
from ..models.openai import ChatOpenAI
from ..core.schemas import SystemMessage, HumanMessage
from .training import fetch_rss
from .model import AdvancedNeuralAgent
from .features import text_features

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


def generate_style_sheet():
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
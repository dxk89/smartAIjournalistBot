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
    print("   - 🤖 Running Style Scoring Tool...")
    feats = text_features(article_text).reshape(1, -1)
    agent = AdvancedNeuralAgent(input_size=feats.shape[1])
    try:
        agent.load("data/model_weights.npz")
        score = agent.predict(feats)[0, 0]
        print(f"   - ✅ Style Score: {score:.3f}")
        return score
    except Exception as e:
        print(f"   - ⚠️ Error loading style model or predicting: {e}")
        return 0.0


def analyze_articles_with_llm(text: str, api_key: str) -> dict:
    print("   - 🤖 Performing LLM-based stylistic analysis...")
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
        print(f"   - 🔥 LLM analysis failed: {e}")
        return {}


def generate_style_sheet():
    print("[ℹ️] Generating new style sheet from latest articles...")
    articles = fetch_rss()
    
    if articles:
        all_text = " ".join([article['text'] for article in articles])
        words = nltk.word_tokenize(all_text)
        sentences = nltk.sent_tokenize(all_text)
        
        avg_sentence_length = np.mean([len(nltk.word_tokenize(s)) for s in sentences]) if sentences else 0
        em_dash_freq = all_text.count('—') / len(words) * 1000 if words else 0
        semicolon_freq = all_text.count(';') / len(words) * 1000 if words else 0
        
        llm_analysis = analyze_articles_with_llm(all_text, os.environ.get("OPENAI_API_KEY"))

        style_profile = {
            "avg_sentence_length": f"{avg_sentence_length:.2f}",
            "em_dash_freq_per_1000_words": f"{em_dash_freq:.2f}",
            "semicolon_freq_per_1000_words": f"{semicolon_freq:.2f}",
            **llm_analysis
        }
        
        house_style_sheet = "## House Style Sheet (Generated)\n\n"
        for key, value in style_profile.items():
            value_str = json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value)
            house_style_sheet += f"- **{key.replace('_', ' ').title()}**:\n  ```\n{value_str}\n  ```\n"
            
        print("[✅] Style sheet generated successfully.")
        return house_style_sheet
    else:
        print("[❌] No articles found to generate style sheet.")
        return None
# File: src/my_framework/style_guru/deep_analyzer.py

import json
import os
from typing import List, Dict
from ..models.openai import ChatOpenAI
from ..core.schemas import SystemMessage, HumanMessage
from .training import fetch_rss

def analyze_article_batch(articles: List[Dict], llm: ChatOpenAI, batch_num: int) -> Dict:
    """
    Deep analysis of a batch of articles using GPT-4.
    Extracts nuanced patterns, style characteristics, and writing techniques.
    """
    print(f"   [Batch {batch_num}] Analyzing {len(articles)} articles with GPT-4...")
    
    # Combine articles for analysis
    combined_text = ""
    for i, article in enumerate(articles, 1):
        combined_text += f"\n\n=== ARTICLE {i}: {article['title']} ===\n"
        combined_text += article['text'][:2000]  # First 2000 chars of each
    
    analysis_prompt = f"""
You are an expert style analyst. Analyze these {len(articles)} IntelliNews articles and provide a DETAILED analysis.

ARTICLES TO ANALYZE:
{combined_text[:15000]}

Provide your response as a valid JSON object with these keys:

1. "lead_patterns": Array of 5+ common patterns used in opening sentences
2. "sentence_structures": Array of typical sentence structures (e.g., "Subject + active verb + object")
3. "vocabulary_preferences": Object with "prefer" and "avoid" arrays
4. "attribution_style": Detailed notes on how sources are cited
5. "tone_characteristics": Array describing the writing tone
6. "paragraph_structure": Description of how paragraphs are organized
7. "transitions": Array of common transition phrases between ideas
8. "data_presentation": How numbers, statistics, and data are presented
9. "quote_integration": How quotes are woven into articles
10. "writing_techniques": Array of specific techniques used (e.g., "Uses concrete examples")

Be specific and provide examples where possible.
"""
    
    messages = [
        SystemMessage(content="You are an expert journalist and style analyst. Provide detailed, actionable insights."),
        HumanMessage(content=analysis_prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        clean_response = response.content.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(clean_response)
    except Exception as e:
        print(f"   [Batch {batch_num}] ⚠️ Analysis failed: {e}")
        return {}


def deep_style_analysis(max_articles: int = 300) -> Dict:
    """
    Perform deep analysis on up to 300 IntelliNews articles.
    Returns a comprehensive style framework.
    """
    print("\n" + "="*70)
    print("DEEP STYLE ANALYSIS - 300 ARTICLES")
    print("="*70)
    
    # Fetch articles
    print("\n[1/4] Fetching articles from RSS feeds...")
    articles = fetch_rss()
    
    if not articles:
        print("❌ No articles fetched!")
        return {}
    
    # Limit to requested number
    articles = articles[:max_articles]
    print(f"✅ Fetched {len(articles)} articles for analysis")
    
    # Initialize LLM
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ No OpenAI API key found!")
        return {}
    
    llm = ChatOpenAI(api_key=api_key, model_name="gpt-4o", temperature=0)
    
    # Analyze in batches (10 articles per batch to stay within token limits)
    print("\n[2/4] Analyzing articles in batches...")
    batch_size = 10
    all_analyses = []
    
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        analysis = analyze_article_batch(batch, llm, batch_num)
        if analysis:
            all_analyses.append(analysis)
    
    print(f"✅ Completed {len(all_analyses)} batch analyses")
    
    # Synthesize all analyses into one framework
    print("\n[3/4] Synthesizing comprehensive style framework...")
    synthesis = synthesize_analyses(all_analyses, llm, len(articles))
    
    # Save framework
    print("\n[4/4] Saving style framework...")
    save_style_framework(synthesis, articles[:10])  # Include 10 example articles
    
    print("\n" + "="*70)
    print("✅ DEEP ANALYSIS COMPLETE")
    print("="*70)
    
    return synthesis


def synthesize_analyses(analyses: List[Dict], llm: ChatOpenAI, total_articles: int) -> Dict:
    """
    Synthesize multiple batch analyses into one comprehensive framework.
    """
    print(f"   Synthesizing {len(analyses)} batch analyses...")
    
    # Combine all analyses
    combined = json.dumps(analyses, indent=2)
    
    synthesis_prompt = f"""
You analyzed {total_articles} IntelliNews articles in {len(analyses)} batches.
Now synthesize ALL the batch analyses into ONE comprehensive style framework.

BATCH ANALYSES:
{combined[:20000]}

Create a MASTER style guide as a JSON object with:

1. "core_principles": Array of 10 fundamental writing principles
2. "sentence_patterns": Array of most common sentence structures with examples
3. "vocabulary_guide": Object with "always_use", "often_use", "never_use" arrays
4. "lead_formula": Step-by-step guide for writing opening paragraphs
5. "attribution_rules": Detailed rules for citing sources
6. "tone_guidelines": Specific guidance on maintaining the right tone
7. "structure_template": Article structure from lead to conclusion
8. "style_nuances": Array of subtle style points that distinguish IntelliNews
9. "common_mistakes": Array of things to avoid
10. "quality_checklist": Array of items to verify before publishing

Make this actionable and specific. Include examples.
"""
    
    messages = [
        SystemMessage(content="You are creating the definitive IntelliNews style guide. Be comprehensive and specific."),
        HumanMessage(content=synthesis_prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        clean_response = response.content.strip().removeprefix("```json").removesuffix("```").strip()
        framework = json.loads(clean_response)
        print("   ✅ Synthesis complete")
        return framework
    except Exception as e:
        print(f"   ⚠️ Synthesis failed: {e}")
        return {}


def save_style_framework(framework: Dict, example_articles: List[Dict]):
    """
    Save the style framework to a file with examples.
    """
    output = {
        "framework": framework,
        "example_articles": [
            {
                "title": article["title"],
                "opening_paragraph": article["text"].split('\n\n')[0] if '\n\n' in article["text"] else article["text"][:500]
            }
            for article in example_articles
        ],
        "version": "2.0",
        "articles_analyzed": 300
    }
    
    # Save as JSON
    try:
        with open("intellinews_style_framework.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print("   ✅ Framework saved to: intellinews_style_framework.json")
    except Exception as e:
        print(f"   ⚠️ Could not save framework: {e}")
    
    # Also create a human-readable version
    try:
        readable = format_framework_readable(framework, example_articles)
        with open("intellinews_style_guide.txt", "w", encoding="utf-8") as f:
            f.write(readable)
        print("   ✅ Readable guide saved to: intellinews_style_guide.txt")
    except Exception as e:
        print(f"   ⚠️ Could not save readable guide: {e}")


def format_framework_readable(framework: Dict, examples: List[Dict]) -> str:
    """
    Format the framework into a readable text document.
    """
    output = """
╔══════════════════════════════════════════════════════════════════╗
║       INTELLINEWS COMPREHENSIVE STYLE FRAMEWORK v2.0             ║
║              Based on Analysis of 300 Articles                   ║
╚══════════════════════════════════════════════════════════════════╝

"""
    
    # Core Principles
    if "core_principles" in framework:
        output += "\n▼ CORE PRINCIPLES\n" + "─"*70 + "\n"
        for i, principle in enumerate(framework["core_principles"], 1):
            output += f"{i}. {principle}\n"
    
    # Lead Formula
    if "lead_formula" in framework:
        output += "\n▼ LEAD PARAGRAPH FORMULA\n" + "─"*70 + "\n"
        if isinstance(framework["lead_formula"], list):
            for step in framework["lead_formula"]:
                output += f"• {step}\n"
        else:
            output += str(framework["lead_formula"]) + "\n"
    
    # Sentence Patterns
    if "sentence_patterns" in framework:
        output += "\n▼ SENTENCE PATTERNS\n" + "─"*70 + "\n"
        if isinstance(framework["sentence_patterns"], list):
            for pattern in framework["sentence_patterns"]:
                output += f"• {pattern}\n"
        else:
            output += str(framework["sentence_patterns"]) + "\n"
    
    # Vocabulary Guide
    if "vocabulary_guide" in framework:
        output += "\n▼ VOCABULARY GUIDE\n" + "─"*70 + "\n"
        vocab = framework["vocabulary_guide"]
        if "always_use" in vocab:
            output += "\nALWAYS USE:\n"
            for word in vocab["always_use"]:
                output += f"  ✓ {word}\n"
        if "often_use" in vocab:
            output += "\nOFTEN USE:\n"
            for word in vocab["often_use"]:
                output += f"  • {word}\n"
        if "never_use" in vocab:
            output += "\nNEVER USE:\n"
            for word in vocab["never_use"]:
                output += f"  ✗ {word}\n"
    
    # Attribution Rules
    if "attribution_rules" in framework:
        output += "\n▼ ATTRIBUTION RULES\n" + "─"*70 + "\n"
        if isinstance(framework["attribution_rules"], list):
            for rule in framework["attribution_rules"]:
                output += f"• {rule}\n"
        else:
            output += str(framework["attribution_rules"]) + "\n"
    
    # Tone Guidelines
    if "tone_guidelines" in framework:
        output += "\n▼ TONE GUIDELINES\n" + "─"*70 + "\n"
        if isinstance(framework["tone_guidelines"], list):
            for guideline in framework["tone_guidelines"]:
                output += f"• {guideline}\n"
        else:
            output += str(framework["tone_guidelines"]) + "\n"
    
    # Structure Template
    if "structure_template" in framework:
        output += "\n▼ ARTICLE STRUCTURE TEMPLATE\n" + "─"*70 + "\n"
        if isinstance(framework["structure_template"], list):
            for item in framework["structure_template"]:
                output += f"• {item}\n"
        else:
            output += str(framework["structure_template"]) + "\n"
    
    # Style Nuances
    if "style_nuances" in framework:
        output += "\n▼ STYLE NUANCES\n" + "─"*70 + "\n"
        for nuance in framework["style_nuances"]:
            output += f"• {nuance}\n"
    
    # Common Mistakes
    if "common_mistakes" in framework:
        output += "\n▼ COMMON MISTAKES TO AVOID\n" + "─"*70 + "\n"
        for mistake in framework["common_mistakes"]:
            output += f"✗ {mistake}\n"
    
    # Quality Checklist
    if "quality_checklist" in framework:
        output += "\n▼ PRE-PUBLISH QUALITY CHECKLIST\n" + "─"*70 + "\n"
        for item in framework["quality_checklist"]:
            output += f"☐ {item}\n"
    
    # Example Articles
    output += "\n▼ EXAMPLE OPENING PARAGRAPHS\n" + "─"*70 + "\n"
    for i, article in enumerate(examples, 1):
        output += f"\nExample {i}: {article['title']}\n"
        opening = article['text'].split('\n\n')[0] if '\n\n' in article['text'] else article['text'][:400]
        output += f"{opening}\n"
    
    output += "\n" + "═"*70 + "\n"
    output += "END OF STYLE FRAMEWORK\n"
    output += "═"*70 + "\n"
    
    return output


# Convenience function to run analysis
def run_deep_analysis():
    """Run the deep style analysis process."""
    framework = deep_style_analysis(max_articles=300)
    return framework


if __name__ == "__main__":
    run_deep_analysis()
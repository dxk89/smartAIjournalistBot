# File: src/my_framework/style_guru/scorer.py

import json
import os
import numpy as np
from typing import Dict, Tuple
from ..models.openai import ChatOpenAI
from ..core.schemas import SystemMessage, HumanMessage
from .features import text_features
from .model import AdvancedNeuralAgent


def load_style_framework() -> Dict:
    """Load the comprehensive style framework."""
    try:
        with open("intellinews_style_framework.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ Style framework not found. Run deep_analyzer.py first.")
        return {}


def statistical_score(article_text: str) -> float:
    """
    Score using the trained neural network model.
    Returns a score between 0 and 1.
    """
    try:
        feats = text_features(article_text).reshape(1, -1)
        agent = AdvancedNeuralAgent(input_size=feats.shape[1])
        agent.load("data/model_weights.npz")
        score = agent.predict(feats)[0, 0]
        return float(np.clip(score, 0, 1))
    except Exception as e:
        print(f"⚠️ Statistical scoring failed: {e}")
        return 0.5  # Default to neutral score


def llm_based_score(article_text: str, framework: Dict) -> Tuple[float, str]:
    """
    Use GPT-4 to score the article against the IntelliNews style framework.
    Returns (score, detailed_feedback).
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return 0.5, "No API key available for LLM scoring"
    
    llm = ChatOpenAI(api_key=api_key, model_name="gpt-4o", temperature=0)
    
    # Extract key framework elements
    core_principles = framework.get("framework", {}).get("core_principles", [])
    vocabulary = framework.get("framework", {}).get("vocabulary_guide", {})
    style_nuances = framework.get("framework", {}).get("style_nuances", [])
    
    framework_summary = f"""
CORE PRINCIPLES: {', '.join(core_principles[:5])}
NEVER USE: {', '.join(vocabulary.get('never_use', [])[:10])}
STYLE NUANCES: {', '.join(style_nuances[:5])}
"""
    
    scoring_prompt = f"""
You are an expert editor for IntelliNews. Score this article against our house style.

INTELLINEWS STYLE FRAMEWORK:
{framework_summary}

CRITICAL: The opening sentence MUST be punchy, direct, and to-the-point.
BAD openings: "In a recent development...", "According to reports...", "It has been announced..."
GOOD openings: "Russia raised interest rates to 21%.", "Ukraine signed a €2.5bn defence deal."

ARTICLE TO SCORE:
---
{article_text[:3000]}
---

Provide your response as a JSON object with:
{{
  "overall_score": 0.0-1.0,
  "lead_quality": 0.0-1.0,
  "structure_score": 0.0-1.0,
  "vocabulary_score": 0.0-1.0,
  "tone_score": 0.0-1.0,
  "attribution_score": 0.0-1.0,
  "strengths": ["strength 1", "strength 2"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "specific_feedback": "Detailed feedback paragraph",
  "revision_priorities": ["priority 1", "priority 2", "priority 3"]
}}

SCORING CRITERIA:
- lead_quality: Is the first sentence punchy and direct? Does it immediately convey the key news?
- structure_score: Is the article well-organized with clear flow?
- vocabulary_score: Appropriate word choice, avoids forbidden words?
- tone_score: Professional, objective journalism?
- attribution_score: Proper source citations throughout?

Be honest and critical. A score of 0.9+ should be rare and exceptional.
If the opening sentence is weak or generic, lead_quality should be 0.6 or lower.
"""
    
    messages = [
        SystemMessage(content="You are a senior editor at IntelliNews with 20 years of experience. You have high standards."),
        HumanMessage(content=scoring_prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        clean_response = response.content.strip().removeprefix("```json").removesuffix("```").strip()
        result = json.loads(clean_response)
        
        overall_score = result.get("overall_score", 0.5)
        
        # Format detailed feedback
        feedback = f"""
╔══════════════════════════════════════════════════════════════════╗
║                    STYLE GURU FEEDBACK                           ║
╚══════════════════════════════════════════════════════════════════╝

OVERALL SCORE: {overall_score:.2f}/1.00

COMPONENT SCORES:
  Lead Quality:    {result.get('lead_quality', 0):.2f}/1.00
  Structure:       {result.get('structure_score', 0):.2f}/1.00
  Vocabulary:      {result.get('vocabulary_score', 0):.2f}/1.00
  Tone:            {result.get('tone_score', 0):.2f}/1.00
  Attribution:     {result.get('attribution_score', 0):.2f}/1.00

STRENGTHS:
"""
        for strength in result.get("strengths", []):
            feedback += f"  ✓ {strength}\n"
        
        feedback += "\nWEAKNESSES:\n"
        for weakness in result.get("weaknesses", []):
            feedback += f"  ✗ {weakness}\n"
        
        feedback += f"\nDETAILED FEEDBACK:\n{result.get('specific_feedback', 'No specific feedback')}\n"
        
        feedback += "\nREVISION PRIORITIES:\n"
        for i, priority in enumerate(result.get("revision_priorities", []), 1):
            feedback += f"  {i}. {priority}\n"
        
        feedback += "\n" + "═"*70 + "\n"
        
        return overall_score, feedback
        
    except Exception as e:
        print(f"⚠️ LLM scoring failed: {e}")
        return 0.5, f"LLM scoring failed: {e}"


def score_article(article_text: str) -> Tuple[float, str]:
    """
    Score an article using both statistical and LLM-based methods.
    Returns (combined_score, detailed_feedback).
    """
    print("\n" + "─"*70)
    print("SCORING ARTICLE AGAINST INTELLINEWS STYLE")
    print("─"*70)
    
    # Load framework
    framework = load_style_framework()
    
    # Statistical score (30% weight)
    print("\n[1/2] Running statistical analysis...")
    stat_score = statistical_score(article_text)
    print(f"   Statistical Score: {stat_score:.3f}")
    
    # LLM score (70% weight - more reliable)
    print("\n[2/2] Running LLM-based analysis...")
    llm_score, llm_feedback = llm_based_score(article_text, framework)
    print(f"   LLM Score: {llm_score:.3f}")
    
    # Combined score
    combined_score = (stat_score * 0.3) + (llm_score * 0.7)
    
    print("\n" + "─"*70)
    print(f"FINAL COMBINED SCORE: {combined_score:.3f}/1.00")
    print("─"*70)
    
    # Add statistical score to feedback
    full_feedback = f"""
COMBINED SCORE: {combined_score:.3f}/1.00
  - Statistical Score: {stat_score:.3f} (30% weight)
  - LLM Score:         {llm_score:.3f} (70% weight)

{llm_feedback}
"""
    
    return combined_score, full_feedback


def meets_threshold(score: float, threshold: float = 0.80) -> bool:
    """Check if the score meets the quality threshold."""
    return score >= threshold


def score_with_verdict(article_text: str, threshold: float = 0.80) -> Dict:
    """
    Score an article and return a verdict.
    """
    score, feedback = score_article(article_text)
    
    verdict = {
        "score": score,
        "feedback": feedback,
        "passes": meets_threshold(score, threshold),
        "threshold": threshold
    }
    
    if verdict["passes"]:
        verdict["message"] = f"✅ ACCEPTED - Score {score:.3f} meets threshold {threshold:.2f}"
    else:
        verdict["message"] = f"❌ NEEDS REVISION - Score {score:.3f} below threshold {threshold:.2f}"
    
    return verdict
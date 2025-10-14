# File: src/my_framework/agents/iterative_writer.py

import json
from typing import Dict, List
from ..core.runnables import Runnable
from ..models.base import BaseChatModel
from ..core.schemas import SystemMessage, HumanMessage
from ..apps import rules
from ..style_guru.scorer import score_with_verdict, load_style_framework
from ..agents.loggerbot import LoggerBot


class IterativeWriterAgent(Runnable):
    """
    An agent that iteratively writes and refines articles until they meet
    the IntelliNews style standards as judged by the Style Guru.
    """
    
    def __init__(self, llm: BaseChatModel, max_iterations: int = 5, score_threshold: float = 0.80, logger=None):
        self.llm = llm
        self.max_iterations = max_iterations
        self.score_threshold = score_threshold
        self.framework = load_style_framework()
        self.logger = logger or LoggerBot.get_logger()
    
    def invoke(self, input: dict, config=None) -> Dict:
        """
        Main entry point. Writes an article iteratively until it passes Style Guru scoring.
        
        Input should contain:
        - source_content: The scraped content to base the article on
        - user_prompt: Additional instructions for the article
        
        Returns:
        - final_article: The accepted article text
        - score: Final score
        - iterations: Number of iterations taken
        - history: List of all attempts with scores
        """
        self.logger.info("\n" + "="*70)
        self.logger.info("ITERATIVE WRITER AGENT - WRITE → SCORE → REFINE LOOP")
        self.logger.info("="*70)
        
        source_content = input.get("source_content", "")
        user_prompt = input.get("user_prompt", "Write a news article")
        
        if not source_content:
            self.logger.error("No source content provided to IterativeWriterAgent")
            return {"error": "No source content provided"}
        
        # Prepare style framework context
        framework_context = self._prepare_framework_context()
        
        history = []
        current_article = None
        current_feedback = None
        
        for iteration in range(1, self.max_iterations + 1):
            self.logger.info(f"\n{'▼'*70}")
            self.logger.info(f"ITERATION {iteration}/{self.max_iterations}")
            self.logger.info(f"{'▼'*70}")
            
            # Write or refine the article
            if iteration == 1:
                self.logger.info("\n[1/3] Writing initial draft...")
                current_article = self._write_initial_draft(
                    source_content, user_prompt, framework_context
                )
            else:
                self.logger.info(f"\n[1/3] Refining article (attempt {iteration})...")
                current_article = self._refine_article(
                    current_article, current_feedback, source_content, framework_context
                )
            
            self.logger.info(f"   Article length: {len(current_article)} characters")
            
            # Score the article
            self.logger.info("\n[2/3] Scoring article with Style Guru...")
            verdict = score_with_verdict(current_article, self.score_threshold)
            
            score = verdict["score"]
            current_feedback = verdict["feedback"]
            passes = verdict["passes"]
            
            # Record this iteration
            history.append({
                "iteration": iteration,
                "article": current_article,
                "score": score,
                "feedback": current_feedback,
                "passes": passes
            })
            
            self.logger.info(f"\n[3/3] Result: {verdict['message']}")
            
            # Check if we're done
            if passes:
                self.logger.info("\n" + "✅"*35)
                self.logger.info(f"SUCCESS! Article accepted after {iteration} iteration(s)")
                self.logger.info("✅"*35)
                return {
                    "final_article": current_article,
                    "score": score,
                    "iterations": iteration,
                    "history": history,
                    "success": True
                }
            else:
                self.logger.info(f"\n❌ Score {score:.3f} below threshold {self.score_threshold:.2f}")
                self.logger.info(f"   Continuing to iteration {iteration + 1}...")
                self.logger.debug("\nFeedback from Style Guru:")
                self.logger.debug(current_feedback)
        
        # Max iterations reached without passing
        self.logger.warning("\n" + "⚠️"*35)
        self.logger.warning(f"MAX ITERATIONS REACHED ({self.max_iterations})")
        self.logger.warning(f"Best score achieved: {max(h['score'] for h in history):.3f}")
        self.logger.warning("⚠️"*35)
        
        # Return best attempt
        best_attempt = max(history, key=lambda x: x['score'])
        
        return {
            "final_article": best_attempt["article"],
            "score": best_attempt["score"],
            "iterations": self.max_iterations,
            "history": history,
            "success": False,
            "message": f"Did not meet threshold after {self.max_iterations} iterations. Returning best attempt."
        }
    
    def _prepare_framework_context(self) -> str:
        """
        Prepare a condensed version of the style framework for the LLM.
        """
        if not self.framework or "framework" not in self.framework:
            return "Write in a professional journalistic style."
        
        fw = self.framework["framework"]
        
        context = "INTELLINEWS STYLE FRAMEWORK:\n\n"
        
        # Core principles
        if "core_principles" in fw:
            context += "CORE PRINCIPLES:\n"
            for principle in fw["core_principles"][:8]:
                context += f"• {principle}\n"
            context += "\n"
        
        # Lead formula
        if "lead_formula" in fw:
            context += "LEAD PARAGRAPH FORMULA:\n"
            if isinstance(fw["lead_formula"], list):
                for step in fw["lead_formula"]:
                    context += f"• {step}\n"
            else:
                context += str(fw["lead_formula"]) + "\n"
            context += "\n"
        
        # Vocabulary
        if "vocabulary_guide" in fw:
            vocab = fw["vocabulary_guide"]
            if "never_use" in vocab:
                context += "NEVER USE THESE WORDS/PHRASES:\n"
                for word in vocab["never_use"][:15]:
                    context += f"✗ {word}\n"
                context += "\n"
        
        # Style nuances
        if "style_nuances" in fw:
            context += "STYLE NUANCES:\n"
            for nuance in fw["style_nuances"][:8]:
                context += f"• {nuance}\n"
            context += "\n"
        
        # Example articles
        if "example_articles" in self.framework:
            context += "EXAMPLE OPENING PARAGRAPHS (Study these carefully):\n"
            for i, example in enumerate(self.framework["example_articles"][:3], 1):
                context += f"\nExample {i}: {example['title']}\n"
                context += f"{example['opening_paragraph']}\n"
        
        return context
    
    def _write_initial_draft(self, source_content: str, user_prompt: str, framework_context: str) -> str:
        """
        Write the initial draft using the style framework.
        """
        system_prompt = f"""You are an expert journalist writing for IntelliNews.

{framework_context}

CRITICAL RULES:
- NO markdown formatting (**, *, _, etc.) - plain text only
- Follow the IntelliNews style framework exactly
- Lead with the most newsworthy fact
- Use British English spelling
- Include proper source attribution
- Write like a professional journalist, not an AI

{rules.get_writing_style_guide()}
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""Write a news article based on this source content.

USER INSTRUCTIONS: {user_prompt}

SOURCE CONTENT:
---
{source_content[:8000]}
---

Write the complete article now. Remember: NO markdown formatting, follow IntelliNews style exactly, and use British English spelling.""")
        ]
        
        response = self.llm.invoke(messages)
        return response.content.strip()
    
    def _refine_article(self, current_article: str, feedback: str, source_content: str, framework_context: str) -> str:
        """
        Refine the article based on Style Guru feedback.
        """
        system_prompt = f"""You are an expert journalist revising an article for IntelliNews.

{framework_context}

The Style Guru has reviewed your article and provided detailed feedback.
Your task is to revise the article to address ALL the feedback points.

CRITICAL RULES:
- NO markdown formatting (**, *, _, etc.) - plain text only
- Follow the IntelliNews style framework exactly
- Address every point in the feedback
- Maintain factual accuracy to the source content
- Use British English spelling
- Write like a professional journalist, not an AI

{rules.get_writing_style_guide()}
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""Here is your current article:

CURRENT ARTICLE:
---
{current_article}
---

STYLE GURU FEEDBACK:
---
{feedback}
---

SOURCE CONTENT (for reference):
---
{source_content[:8000]}
---

Revise the article to address ALL the feedback points. Output ONLY the revised article. Remember to use British English spelling.""")
        ]
        
        response = self.llm.invoke(messages)
        return response.content.strip()
# File: my_framework/src/my_framework/agents/orchestrator.py

import json
import os
import re
from my_framework.core.runnables import Runnable
from my_framework.models.base import BaseChatModel
from my_framework.agents.researcher import ResearcherAgent
from my_framework.agents.writer import WriterAgent
from my_framework.agents.iterative_writer import IterativeWriterAgent
from my_framework.agents.editor import EditorReflectorAgent
from my_framework.agents.publisher import PublisherAgent
from my_framework.agents.summarizer import SummarizerAgent
from my_framework.core.schemas import SystemMessage, HumanMessage
from my_framework.apps import rules
from my_framework.models.openai import safe_load_json
from my_framework.agents.loggerbot import LoggerBot

try:
    from my_framework.style_guru.scorer import score_article
    STYLE_GURU_AVAILABLE = True
except ImportError:
    STYLE_GURU_AVAILABLE = False

class OrchestratorAgent(Runnable):
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel, use_style_guru: bool = True, score_threshold: float = 0.80, logger=None):
        self.llm = llm
        self.logger = logger or LoggerBot.get_logger()
        self.researcher = ResearcherAgent(logger=self.logger)
        self.summarizer = SummarizerAgent(llm=llm, logger=self.logger)
        
        self.use_style_guru = use_style_guru
        if use_style_guru:
            if os.path.exists("intellinews_style_framework.json"):
                self.logger.info("✅ Style Guru enabled - using IterativeWriterAgent")
                self.writer = IterativeWriterAgent(llm=llm, max_iterations=5, score_threshold=score_threshold, logger=self.logger)
            else:
                self.logger.warning("⚠️ Style framework not found. Falling back to regular WriterAgent")
                self.writer = WriterAgent(llm=llm, logger=self.logger)
                self.use_style_guru = False
        else:
            self.logger.info("Style Guru disabled - using regular WriterAgent")
            self.writer = WriterAgent(llm=llm, logger=self.logger)
        
        self.editor = EditorReflectorAgent(llm=llm, logger=self.logger)
        self.publisher = PublisherAgent(logger=self.logger)
        
        self.agent_map = {
            "research": self.researcher,
            "summarize": self.summarizer,
            "write": self.writer,
            "edit": self.editor,
            "publish": self.publisher,
        }
        self.memory = []

    def invoke(self, input: dict, config=None) -> str:
        self.logger.info("--- Orchestrator Agent Starting Workflow ---")
        
        user_goal = input.get("input")
        self.memory.append(HumanMessage(content=user_goal))
        
        is_prewritten = "source_content" in input and input["source_content"] and not input.get("source_url")
        
        if is_prewritten:
            self.logger.info("📄 PRE-WRITTEN ARTICLE DETECTED")
            return self._handle_prewritten_article(input)
        
        self.logger.info("Orchestrator: 🧠 Planning the workflow...")
        plan_prompt = [
            SystemMessage(content=rules.ORCHESTRATOR_SYSTEM_PROMPT),
            HumanMessage(content=user_goal)
        ]
        plan_response = self.llm.invoke(plan_prompt)
        self.logger.info("Orchestrator: 📝 Plan received from LLM")
        
        try:
            plan = safe_load_json(plan_response.content)
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Orchestrator: ❌ Failed to parse plan from LLM: {e}")
            return f"Error: Could not decode the workflow plan. {e}"

        context = {"user_goal": user_goal, **input}
        for i, step in enumerate(plan):
            agent_name = step["agent"]
            agent_input = step["task"]
            
            self.logger.info(f"Orchestrator: 🔄 Step {i+1}: Delegating to {agent_name.title()} Agent.")
            
            for key, value in agent_input.items():
                if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                    lookup_key = value.strip("{}")
                    agent_input[key] = context.get(lookup_key)
                    self.logger.debug(f"Orchestrator:  dynamically setting '{key}' from context.")

            if agent_name == "publish":
                agent_input["cms_config_json"] = context.get("cms_config_json")

            if agent_name in self.agent_map:
                agent = self.agent_map[agent_name]
                result = agent.invoke(agent_input)
                
                if agent_name == "write" and self.use_style_guru and isinstance(result, dict):
                    context[f"step_{i+1}_output"] = result["final_article"]
                else:
                    context[f"step_{i+1}_output"] = result
                
                self.memory.append(HumanMessage(content=f"Step {i+1} ({agent_name}): completed"))
                self.logger.info(f"Orchestrator: ✅ Step {i+1} completed.")
            else:
                context[f"step_{i+1}_output"] = f"Error: Agent '{agent_name}' not found."
                self.logger.error(f"Orchestrator: ❌ Agent '{agent_name}' not found.")

        self.logger.info("--- Orchestrator Workflow Complete ---")
        return context.get(f"step_{len(plan)}_output", "Workflow finished with no final output.")

    def _handle_prewritten_article(self, input: dict) -> str:
        source_content = input.get("source_content")
        
        self.logger.info("\n" + "="*70)
        self.logger.info("PRE-WRITTEN ARTICLE WORKFLOW")
        
        if self.use_style_guru and STYLE_GURU_AVAILABLE:
            self.logger.info("\n[1/3] 📊 Scoring pre-written article with Style Guru...")
            try:
                score, feedback = score_article(source_content)
                self.logger.info(f"\n✨ STYLE GURU SCORE: {score:.3f}/1.00")
            except Exception as e:
                self.logger.error(f"⚠️ Could not score article: {e}", exc_info=True)
        
        self.logger.info("\n[2/3] 📝 Generating metadata...")
        editor_input = { "draft_article": source_content, "source_content": source_content }
        article_json = self.editor.invoke(editor_input)
        self.logger.info("✅ Metadata generated")
        
        self.logger.info("\n[3/3] 🚀 Publishing to CMS...")
        publisher_input = {
            "article_json_string": article_json,
            "username": input.get("username"),
            "password": input.get("password"),
            "cms_config_json": input.get("cms_config_json")
        }
        result = self.publisher.invoke(publisher_input)
        
        self.logger.info("\n" + "="*70)
        self.logger.info("✅ PRE-WRITTEN ARTICLE WORKFLOW COMPLETE")
        
        return result
    
    def rewrite_only(self, input: dict) -> dict:
        source_url = input.get("source_url")
        if not source_url:
            return {"error": "No source URL provided"}
        
        self.logger.info("REWRITE ONLY WORKFLOW")
        
        self.logger.info("\n[1/3] 📡 Scraping URL...")
        source_content = self.researcher.invoke({"source_url": source_url})
        if isinstance(source_content, dict) and "error" in source_content:
            return source_content
        self.logger.info(f"✅ Scraped {len(source_content)} characters")
        
        self.logger.info("\n[2/3] ✍️ Writing article with Style Guru...")
        writer_input = { "source_content": source_content, "user_prompt": "Write a news article based on this content" }
        result = self.writer.invoke(writer_input)
        
        article, score, feedback, iterations = "", 0.0, "", 0
        component_scores = { "lead_quality": 0.0, "structure": 0.0, "vocabulary": 0.0, "tone": 0.0, "attribution": 0.0 }
        
        if isinstance(result, dict):
            article = result.get("final_article", "")
            score = result.get("score", 0.0)
            iterations = result.get("iterations", 0)
            if result.get("history"):
                feedback = result["history"][-1].get("feedback", "")
        else:
            article = str(result)
            feedback = "Style Guru not available"
        
        self.logger.info("\n[3/3] 📊 Extracting component scores...")
        if feedback:
            patterns = {
                "lead_quality": r"Lead Quality:\s*([\d.]+)\/",
                "structure": r"Structure:\s*([\d.]+)\/",
                "vocabulary": r"Vocabulary:\s*([\d.]+)\/",
                "tone": r"Tone:\s*([\d.]+)\/",
                "attribution": r"Attribution:\s*([\d.]+)\/"
            }
            
            for component, pattern in patterns.items():
                match = re.search(pattern, feedback, re.IGNORECASE)
                if match:
                    component_scores[component] = float(match.group(1))
                    self.logger.debug(f"   Extracted {component}: {component_scores[component]:.2f}")
        
        if article:
            lines = article.split('\n')
            # Exclude title from article body
            if len(lines) > 1:
                article = '\n'.join(lines[1:]).strip()
            
            cleaned_lines = [line for line in lines if not any(marker in line for marker in ['OVERALL SCORE:', 'COMPONENT SCORES:', 'STRENGTHS:', 'WEAKNESSES:', 'DETAILED FEEDBACK:', 'REVISION PRIORITIES:'])]
            article = '\n'.join(cleaned_lines).strip()
            # Add source URL to the end
            article += f"\n\nSource: {source_url}"
        
        self.logger.info("✅ REWRITE COMPLETE")
        
        return {
            "article": article,
            "score": float(score),
            "component_scores": {k: float(v) for k, v in component_scores.items()},
            "feedback": feedback,
            "iterations": iterations,
            "success": True
        }
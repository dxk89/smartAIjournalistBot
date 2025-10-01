# File: src/my_framework/agents/orchestrator.py

import json
import logging
import os
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

# Import Style Guru scorer for pre-written articles
try:
    from my_framework.style_guru.scorer import score_article
    STYLE_GURU_AVAILABLE = True
except ImportError:
    STYLE_GURU_AVAILABLE = False

class OrchestratorAgent(Runnable):
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel, use_style_guru: bool = True, score_threshold: float = 0.80):
        self.llm = llm
        self.researcher = ResearcherAgent()
        self.summarizer = SummarizerAgent(llm=llm)
        
        # Use iterative writer if style guru is enabled
        self.use_style_guru = use_style_guru
        if use_style_guru:
            # Check if style framework exists
            if os.path.exists("intellinews_style_framework.json"):
                logging.info("✅ Style Guru enabled - using IterativeWriterAgent")
                self.writer = IterativeWriterAgent(llm=llm, max_iterations=5, score_threshold=score_threshold)
            else:
                logging.warning("⚠️ Style framework not found. Run setup_style_guru.py first!")
                logging.info("   Falling back to regular WriterAgent")
                self.writer = WriterAgent(llm=llm)
                self.use_style_guru = False
        else:
            logging.info("Style Guru disabled - using regular WriterAgent")
            self.writer = WriterAgent(llm=llm)
        
        self.editor = EditorReflectorAgent(llm=llm)
        self.publisher = PublisherAgent()
        
        self.agent_map = {
            "research": self.researcher,
            "summarize": self.summarizer,
            "write": self.writer,
            "edit": self.editor,
            "publish": self.publisher,
        }
        self.memory = []

    def invoke(self, input: dict, config=None) -> str:
        logging.info("--- Orchestrator Agent Starting Workflow ---")
        
        if self.use_style_guru:
            logging.info("🎨 STYLE GURU MODE: Articles will be iteratively refined")
        
        user_goal = input.get("input")
        self.memory.append(HumanMessage(content=user_goal))
        
        # Check if this is a pre-written article (source_content provided directly)
        is_prewritten = "source_content" in input and not input.get("source_url")
        
        if is_prewritten:
            logging.info("📄 PRE-WRITTEN ARTICLE DETECTED")
            return self._handle_prewritten_article(input)
        
        # 1. Plan (for non-pre-written articles)
        logging.info("Orchestrator: 🧠 Planning the workflow...")
        plan_prompt = [
            SystemMessage(content=rules.ORCHESTRATOR_SYSTEM_PROMPT),
            HumanMessage(content=user_goal)
        ]
        plan_response = self.llm.invoke(plan_prompt)
        logging.info(f"Orchestrator: 📝 Plan received from LLM")
        
        try:
            plan = safe_load_json(plan_response.content)
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"Orchestrator: ❌ Failed to parse plan from LLM: {e}")
            return f"Error: Could not decode the workflow plan. {e}"

        # 2. Execute Plan
        context = {"user_goal": user_goal, **input}
        for i, step in enumerate(plan):
            agent_name = step["agent"]
            agent_input = step["task"]
            
            logging.info(f"Orchestrator: 🔄 Step {i+1}: Delegating to {agent_name.title()} Agent.")
            
            # Substitute context from previous steps
            for key, value in agent_input.items():
                if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                    lookup_key = value.strip("{}")
                    agent_input[key] = context.get(lookup_key)
                    logging.info(f"Orchestrator:  dynamically setting '{key}' from context.")

            if agent_name in self.agent_map:
                agent = self.agent_map[agent_name]
                result = agent.invoke(agent_input)
                
                # For iterative writer, extract the final article
                if agent_name == "write" and self.use_style_guru and isinstance(result, dict):
                    if result.get("success"):
                        logging.info(f"Orchestrator: ✅ Article accepted after {result.get('iterations')} iterations")
                        logging.info(f"Orchestrator:    Final score: {result.get('score'):.3f}")
                        context[f"step_{i+1}_output"] = result["final_article"]
                        
                        # Log iteration history
                        for iter_data in result.get("history", []):
                            logging.info(f"   Iteration {iter_data['iteration']}: Score {iter_data['score']:.3f}")
                    else:
                        logging.warning(f"Orchestrator: ⚠️ Article did not reach threshold after {result.get('iterations')} iterations")
                        logging.warning(f"Orchestrator:    Best score: {result.get('score'):.3f}")
                        context[f"step_{i+1}_output"] = result["final_article"]
                else:
                    context[f"step_{i+1}_output"] = result
                
                self.memory.append(HumanMessage(content=f"Step {i+1} ({agent_name}): completed"))
                logging.info(f"Orchestrator: ✅ Step {i+1} completed.")
            else:
                context[f"step_{i+1}_output"] = f"Error: Agent '{agent_name}' not found."
                logging.error(f"Orchestrator: ❌ Agent '{agent_name}' not found.")

        logging.info("--- Orchestrator Workflow Complete ---")
        return context.get(f"step_{len(plan)}_output", "Workflow finished with no final output.")

    def _handle_prewritten_article(self, input: dict) -> str:
        """
        Special handler for pre-written articles.
        Scores them with Style Guru (for informational purposes) but doesn't refine.
        """
        source_content = input.get("source_content")
        username = input.get("username")
        password = input.get("password")
        
        logging.info("\n" + "="*70)
        logging.info("PRE-WRITTEN ARTICLE WORKFLOW")
        logging.info("="*70)
        
        # Step 1: Score with Style Guru (informational only)
        if self.use_style_guru and STYLE_GURU_AVAILABLE:
            logging.info("\n[1/3] 📊 Scoring pre-written article with Style Guru...")
            logging.info("   (This is informational only - article will not be modified)")
            
            try:
                score, feedback = score_article(source_content)
                logging.info(f"\n✨ STYLE GURU SCORE: {score:.3f}/1.00")
                logging.info("\n" + "─"*70)
                logging.info("FEEDBACK SUMMARY:")
                logging.info("─"*70)
                # Log just the first part of feedback (not the whole thing)
                feedback_lines = feedback.split('\n')[:15]
                for line in feedback_lines:
                    logging.info(line)
                logging.info("─"*70)
                
                if score >= 0.80:
                    logging.info("✅ Article meets quality threshold!")
                else:
                    logging.info("⚠️ Article below quality threshold (0.80)")
                    logging.info("   However, pre-written articles are submitted as-is")
                
            except Exception as e:
                logging.warning(f"⚠️ Could not score article: {e}")
        else:
            logging.info("\n[1/3] ⚠️ Style Guru not available - skipping scoring")
        
        # Step 2: Generate metadata (using Editor agent)
        logging.info("\n[2/3] 📝 Generating metadata...")
        editor_input = {
            "draft_article": source_content,
            "source_content": source_content  # Same as draft for pre-written
        }
        article_json = self.editor.invoke(editor_input)
        logging.info("✅ Metadata generated")
        
        # Step 3: Publish
        logging.info("\n[3/3] 🚀 Publishing to CMS...")
        publisher_input = {
            "article_json_string": article_json,
            "username": username,
            "password": password
        }
        result = self.publisher.invoke(publisher_input)
        
        logging.info("\n" + "="*70)
        logging.info("✅ PRE-WRITTEN ARTICLE WORKFLOW COMPLETE")
        logging.info("="*70)
        
        return result
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
        
        # 1. Plan
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
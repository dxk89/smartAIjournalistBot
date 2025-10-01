# File: src/my_framework/agents/orchestrator.py

import json
import logging
from my_framework.core.runnables import Runnable
from my_framework.models.base import BaseChatModel
from my_framework.agents.researcher import ResearcherAgent
from my_framework.agents.writer import WriterAgent
from my_framework.agents.editor import EditorReflectorAgent
from my_framework.agents.publisher import PublisherAgent
from my_framework.agents.summarizer import SummarizerAgent
from my_framework.core.schemas import SystemMessage, HumanMessage
from my_framework.apps import rules
from my_framework.models.openai import safe_load_json # Import the safe loader

class OrchestratorAgent(Runnable):
    llm: BaseChatModel

    def __init__(self, llm: BaseChatModel):
        self.llm = llm
        self.researcher = ResearcherAgent()
        self.summarizer = SummarizerAgent(llm=llm)
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
        user_goal = input.get("input")
        self.memory.append(HumanMessage(content=user_goal))
        
        # 1. Plan
        logging.info("Orchestrator: 🧠 Planning the workflow...")
        plan_prompt = [
            SystemMessage(content=rules.ORCHESTRATOR_SYSTEM_PROMPT),
            HumanMessage(content=user_goal)
        ]
        plan_response = self.llm.invoke(plan_prompt)
        logging.info(f"Orchestrator: 📝 Plan received from LLM: {plan_response.content}")
        
        # FIX: Use the safe JSON loader to handle malformed LLM output
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
                context[f"step_{i+1}_output"] = result
                self.memory.append(HumanMessage(content=f"Step {i+1} ({agent_name}): {result}"))
                logging.info(f"Orchestrator: ✅ Step {i+1} completed.")
            else:
                context[f"step_{i+1}_output"] = f"Error: Agent '{agent_name}' not found."
                logging.error(f"Orchestrator: ❌ Agent '{agent_name}' not found.")

        logging.info("--- Orchestrator Workflow Complete ---")
        return context.get(f"step_{len(plan)}_output", "Workflow finished with no final output.")
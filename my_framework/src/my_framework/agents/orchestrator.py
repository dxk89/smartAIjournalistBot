# File: src/my_framework/agents/orchestrator.py

import json
from my_framework.models.openai import ChatOpenAI
from my_framework.parsers.standard import StandardParser
from my_framework.prompts.templates import planning_template
from my_framework.agents.researcher import ResearcherAgent
from my_framework.agents.writer import WriterAgent
from my_framework.agents.iterative_writer import IterativeWriterAgent
from my_framework.agents.editor import EditorAgent
from my_framework.agents.publisher import PublisherAgent
from my_framework.agents.loggerbot import LoggerBot

logger = LoggerBot.get_logger()

class OrchestratorAgent:
    def __init__(self, context):
        self.context = context
        self.llm = ChatOpenAI(
            model_name="gpt-4o",
            temperature=0.5,
            api_key=self.context.get('openai_api_key')
        )
        self.parser = StandardParser()
        self.researcher = ResearcherAgent(context)
        
        # Conditionally initialize the writer agent based on Style Guru's status
        if self.context.get("style_guru_enabled"):
            logger.info("✅ Style Guru enabled - using IterativeWriterAgent")
            self.writer = IterativeWriterAgent(context)
        else:
            logger.info("❌ Style Guru disabled - using standard WriterAgent")
            self.writer = WriterAgent(context)
            
        self.editor = EditorAgent(context)
        self.publisher = PublisherAgent(context)

    def generate_plan(self, user_goal):
        logger.info("Orchestrator: 🧠 Planning the workflow...")
        prompt = planning_template.format(user_goal=user_goal)
        response = self.llm.invoke(prompt)
        try:
            plan = json.loads(response)
            logger.info("Orchestrator: 📝 Plan received from LLM")
            return plan
        except json.JSONDecodeError:
            logger.error("Orchestrator: ❌ Failed to parse plan from LLM response.")
            return None

    def invoke(self, initial_context):
        logger.info("--- Orchestrator Agent Starting Workflow ---")
        user_goal = initial_context.get("user_goal")
        if not user_goal:
            return {"error": "User goal is required."}

        plan = self.generate_plan(user_goal)
        if not plan:
            return {"error": "Failed to generate a workflow plan."}

        # Initialize a dictionary to hold the results from each step
        workflow_results = {}
        
        # Add initial context to the results
        workflow_results.update(initial_context)

        for i, step in enumerate(plan.get("plan", []), 1):
            agent_name = step.get("agent")
            instruction = step.get("instruction")
            
            # Prepare the input for the agent, combining previous results with the new instruction
            agent_input = workflow_results.copy()
            agent_input["instruction"] = instruction

            logger.info(f"Orchestrator: 🔄 Step {i}: Delegating to {agent_name} Agent.")
            
            result = None
            if agent_name == "Research":
                result = self.researcher.invoke(agent_input)
            elif agent_name == "Write":
                result = self.writer.invoke(agent_input)
            elif agent_name == "Edit":
                result = self.editor.invoke(agent_input)
            elif agent_name == "Publish":
                # Ensure cms_config_json is in the input for the publisher
                agent_input['cms_config_json'] = self.context.get('cms_config_json')
                result = self.publisher.invoke(agent_input)
            
            if result:
                 # Ensure result is a dictionary before updating
                if isinstance(result, dict):
                    workflow_results.update(result)
                else:
                    # If result is not a dict, store it under a generic key
                    workflow_results[f'step_{i}_output'] = result

            logger.info(f"Orchestrator: ✅ Step {i} completed.")

        return workflow_results
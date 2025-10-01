# File: src/my_framework/agents/researcher.py
from my_framework.core.runnables import Runnable
from my_framework.tools.web_scraper import scrape_content
from my_framework.tools.google_sheets import sheets_tool

class ResearcherAgent(Runnable):
    def __init__(self):
        self.tools = [scrape_content, sheets_tool.read_tasks_from_sheet]

    def invoke(self, input: dict, config=None):
        # In a more complex system, this agent would have its own LLM to decide which tool to use.
        # For this workflow, we assume it's directly told which tool to use by the orchestrator.
        print("-> Researcher Agent invoked")
        if "source_url" in input:
            return scrape_content.func(input["source_url"])
        elif "sheet_url" in input:
            return sheets_tool.read_tasks_from_sheet(input["sheet_url"], input["worksheet_name"])
        else:
            return {"error": "Researcher needs a 'source_url' or 'sheet_url' to proceed."}
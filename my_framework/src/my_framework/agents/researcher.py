# File: src/my_framework/agents/researcher.py
from my_framework.core.runnables import Runnable
from my_framework.tools.web_scraper import scrape_content
from my_framework.tools.google_sheets import sheets_tool
from my_framework.agents.loggerbot import LoggerBot

class ResearcherAgent(Runnable):
    def __init__(self, logger=None):
        self.logger = logger or LoggerBot.get_logger()
        self.tools = [scrape_content, sheets_tool.read_tasks_from_sheet]

    def invoke(self, input: dict, config=None):
        self.logger.info("-> Researcher Agent invoked")
        if "source_url" in input:
            self.logger.info(f"   - Scraping content from URL: {input['source_url']}")
            return scrape_content.func(input["source_url"], self.logger)
        elif "sheet_url" in input:
            self.logger.info(f"   - Reading tasks from Google Sheet: {input['sheet_url']}")
            return sheets_tool.read_tasks_from_sheet(input["sheet_url"], input["worksheet_name"])
        else:
            self.logger.error("Researcher needs a 'source_url' or 'sheet_url' to proceed.")
            return {"error": "Researcher needs a 'source_url' or 'sheet_url' to proceed."}
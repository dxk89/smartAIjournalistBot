# File: src/my_framework/tools/google_sheets.py

import os
import gspread
from google.oauth2.service_account import Credentials
from ..agents.tools import tool
from ..agents.loggerbot import LoggerBot

# --- Google Sheets Tool ---

class GoogleSheetsTool:
    def __init__(self, logger=None):
        self.logger = logger or LoggerBot.get_logger()
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_path = os.environ.get("GCP_CREDENTIALS_PATH", "gcp_credentials.json")
        try:
            creds = Credentials.from_service_account_file(creds_path, scopes=self.scopes)
            self.client = gspread.authorize(creds)
            self.logger.info("Google Sheets client authenticated.")
        except FileNotFoundError:
            self.logger.error(f"🔥 Google Sheets credentials not found at {creds_path}. The tool will not work.")
            self.client = None

    @tool
    def read_tasks_from_sheet(self, sheet_url: str, worksheet_name: str) -> list[dict]:
        """
        Reads all rows from a specified worksheet and returns them as a list of dictionaries.
        Useful for fetching new article assignments.
        """
        if not self.client:
            self.logger.error("Google Sheets client not authenticated.")
            return {"error": "Google Sheets client not authenticated."}
        self.logger.info(f"   -  Reading tasks from sheet: {worksheet_name}")
        sheet = self.client.open_by_url(sheet_url)
        worksheet = sheet.worksheet(worksheet_name)
        return worksheet.get_all_records()

    @tool
    def log_completed_article(self, sheet_url: str, worksheet_name: str, article_data: list) -> str:
        """
        Appends a new row to the specified worksheet to log a completed task.
        article_data should be a list of values in the order of the columns.
        """
        if not self.client:
            self.logger.error("Google Sheets client not authenticated.")
            return "Error: Google Sheets client not authenticated."
        self.logger.info(f"   - Logging completed article to sheet: {worksheet_name}")
        sheet = self.client.open_by_url(sheet_url)
        worksheet = sheet.worksheet(worksheet_name)
        worksheet.append_row(article_data)
        return "Successfully logged article to Google Sheet."

# Instantiate the tool to make it available for import
sheets_tool = GoogleSheetsTool()
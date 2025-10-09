# File: src/my_framework/tools/google_sheets.py

import os
import gspread
from google.oauth2.service_account import Credentials
from ..agents.tools import tool
from ..agents.loggerbot import LoggerBot
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class GoogleSheetsTool:
    def __init__(self, logger=None):
        self.logger = logger or LoggerBot.get_logger()
        self.client = None  # Initialize client as None
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_path = os.environ.get("GCP_CREDENTIALS_PATH", "gcp_credentials.json")
        try:
            creds = Credentials.from_service_account_file(creds_path, scopes=self.scopes)
            self.client = gspread.authorize(creds)
            self.logger.info("✅ Google Sheets client authenticated successfully.")
        except FileNotFoundError:
            self.logger.warning(f"⚠️ Google Sheets credentials not found at '{creds_path}'. Google Sheets tool will be disabled.")
        except Exception as e:
            self.logger.error(f"🔥 An unexpected error occurred during Google Sheets initialization: {e}", exc_info=True)

    def get_sheet(self):
        """Opens and returns the Google Sheet specified by SHEET_URL."""
        if not self.client:
            self.logger.error("Google Sheets tool is disabled. Cannot get sheet.")
            return None
        try:
            sheet_url = os.environ.get("SHEET_URL")
            if not sheet_url:
                self.logger.error("SHEET_URL not found in environment variables.")
                return None
            self.logger.info(f"   - Opening Google Sheet: {sheet_url}")
            sheet = self.client.open_by_url(sheet_url)
            return sheet
        except Exception as e:
            self.logger.error(f"Failed to open Google Sheet: {e}", exc_info=True)
            return None

    @tool
    def read_tasks_from_sheet(self, sheet_url: str, worksheet_name: str) -> list[dict]:
        """
        Reads all rows from a specified worksheet.
        """
        if not self.client:
            self.logger.error("Google Sheets tool is disabled. Cannot read from sheet.")
            return {"error": "Google Sheets client not authenticated."}
        try:
            self.logger.info(f"   - Reading tasks from sheet: {worksheet_name}")
            sheet = self.client.open_by_url(sheet_url)
            worksheet = sheet.worksheet(worksheet_name)
            return worksheet.get_all_records()
        except Exception as e:
            self.logger.error(f"Failed to read from Google Sheet: {e}", exc_info=True)
            return {"error": f"Failed to read from Google Sheet: {e}"}

    @tool
    def log_completed_article(self, sheet_url: str, worksheet_name: str, article_data: list) -> str:
        """
        Appends a new row to the specified worksheet.
        """
        if not self.client:
            self.logger.error("Google Sheets tool is disabled. Cannot log to sheet.")
            return "Error: Google Sheets client not authenticated."
        try:
            self.logger.info(f"   - Logging completed article to sheet: {worksheet_name}")
            sheet = self.client.open_by_url(sheet_url)
            worksheet = sheet.worksheet(worksheet_name)
            worksheet.append_row(article_data)
            return "Successfully logged article to Google Sheet."
        except Exception as e:
            self.logger.error(f"Failed to log to Google Sheet: {e}", exc_info=True)
            return f"Error: Failed to log to Google Sheet: {e}"

# Instantiate the tool
sheets_tool = GoogleSheetsTool()
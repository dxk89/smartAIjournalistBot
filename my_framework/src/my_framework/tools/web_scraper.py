# File: src/my_framework/tools/web_scraper.py

import requests
from bs4 import BeautifulSoup
import json
from ..agents.tools import tool
from ..agents.loggerbot import LoggerBot

@tool
def scrape_content(source_url: str, logger=None) -> str:
    """
    Scrapes the main article content from a given URL by intelligently finding the
    primary content container. Input must be a single URL string.
    """
    log = logger or LoggerBot.get_logger()
    log.info(f"-> Scraping content from {source_url}...")
    try:
        log.info("   - Making GET request...")
        response = requests.get(source_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=90)
        log.info(f"   - GET request completed with status code: {response.status_code}")
        response.raise_for_status()

        log.info("   - Parsing HTML content with BeautifulSoup...")
        soup = BeautifulSoup(response.text, 'html.parser')

        log.info("   - Removing unnecessary tags (header, footer, nav, script, style)...")
        for selector in ['header', 'footer', 'nav', 'script', 'style', '.sidebar', '[role="navigation"]', '[class*="comments"]']:
            for element in soup.select(selector):
                element.decompose()
        log.info("   - Unnecessary tags removed.")

        log.info("   - Finding the main content container...")
        main_content = max(soup.find_all('div'), key=lambda tag: len(" ".join(p.get_text() for p in tag.find_all('p'))), default=soup.body)
        
        if not main_content:
            main_content = soup.body
            log.warning("   - Could not find a specific main content div, falling back to the entire body.")
            
        log.info("   - Extracting paragraphs from the main content...")
        paragraphs = main_content.find_all('p')
        source_content = '\n\n'.join(p.get_text().strip() for p in paragraphs if p.get_text().strip())

        if not source_content.strip():
            log.error("   - URL scraping failed: No paragraph content found.")
            return json.dumps({"error": "URL scraping failed: No paragraph content found."})

        log.info(f"-> Scraping successful ({len(source_content)} characters).")
        return source_content

    except requests.exceptions.RequestException as e:
        log.critical(f"   - URL scraping failed: Could not connect to the URL. {e}", exc_info=True)
        return json.dumps({"error": f"URL scraping failed: Could not connect to the URL. {e}"})
    except Exception as e:
        log.critical(f"   - An unexpected error occurred during scraping: {e}", exc_info=True)
        return json.dumps({"error": f"URL scraping failed: {e}"})
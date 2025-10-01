# File: src/my_framework/tools/web_scraper.py

import requests
from bs4 import BeautifulSoup
import json
from ..agents.tools import tool
import logging # Import the logging module

# Use the existing logger from the main app
logger = logging.getLogger()

@tool
def scrape_content(source_url: str) -> str:
    """
    Scrapes the main article content from a given URL by intelligently finding the
    primary content container. Input must be a single URL string.
    """
    logger.info(f"-> Scraping content from {source_url}...")
    try:
        logger.info("   - Making GET request...")
        response = requests.get(source_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=90)
        logger.info(f"   - GET request completed with status code: {response.status_code}")
        response.raise_for_status()

        logger.info("   - Parsing HTML content with BeautifulSoup...")
        soup = BeautifulSoup(response.text, 'html.parser')

        logger.info("   - Removing unnecessary tags (header, footer, nav, script, style)...")
        for selector in ['header', 'footer', 'nav', 'script', 'style', '.sidebar', '[role="navigation"]', '[class*="comments"]']:
            for element in soup.select(selector):
                element.decompose()
        logger.info("   - Unnecessary tags removed.")

        logger.info("   - Finding the main content container...")
        main_content = max(soup.find_all('div'), key=lambda tag: len(" ".join(p.get_text() for p in tag.find_all('p'))), default=soup.body)
        
        if not main_content:
            main_content = soup.body
            logger.warning("   - Could not find a specific main content div, falling back to the entire body.")
            
        logger.info("   - Extracting paragraphs from the main content...")
        paragraphs = main_content.find_all('p')
        source_content = '\n\n'.join(p.get_text().strip() for p in paragraphs if p.get_text().strip())

        if not source_content.strip():
            logger.error("   - URL scraping failed: No paragraph content found.")
            return json.dumps({"error": "URL scraping failed: No paragraph content found."})

        logger.info(f"-> Scraping successful ({len(source_content)} characters).")
        return source_content

    except requests.exceptions.RequestException as e:
        logger.error(f"   - URL scraping failed: Could not connect to the URL. {e}", exc_info=True)
        return json.dumps({"error": f"URL scraping failed: Could not connect to the URL. {e}"})
    except Exception as e:
        logger.error(f"   - An unexpected error occurred during scraping: {e}", exc_info=True)
        return json.dumps({"error": f"URL scraping failed: {e}"})
# File: src/my_framework/style_guru/deep_analyzer.py
import requests
from bs4 import BeautifulSoup
import time
from my_framework.agents.loggerbot import LoggerBot

logger = LoggerBot.get_logger()

def get_article_urls(sheet, num_articles):
    """Gets the latest article URLs from the 'Articles' worksheet."""
    try:
        logger.info("   - Accessing 'Articles' worksheet...")
        articles_worksheet = sheet.worksheet('Articles')
        logger.info("   - Fetching all records from the worksheet...")
        all_records = articles_worksheet.get_all_records()
        logger.info(f"   - Found {len(all_records)} total records.")
        
        # Sort records by date in descending order to get the latest ones
        sorted_records = sorted(all_records, key=lambda x: x.get('Date', ''), reverse=True)
        
        # Get the URLs of the latest 'num_articles'
        urls = [record['URL'] for record in sorted_records[:num_articles] if 'URL' in record and record['URL']]
        logger.info(f"   - Extracted {len(urls)} URLs for analysis.")
        return urls
    except Exception as e:
        logger.error(f"   - ❌ Error getting article URLs: {e}")
        return []

def scrape_article_content(url):
    """Scrapes the main content of a single article."""
    try:
        # Define a User-Agent header to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # This is a generic approach; selector might need to be adapted for specific sites
        # Common selectors for article bodies: 'article', '.post-content', '[itemprop="articleBody"]'
        article_body = soup.find('div', class_='article-content') or soup.find('article')
        
        if article_body:
            return article_body.get_text(separator='\n', strip=True)
        else:
            logger.warning(f"   - ⚠️ Could not find article body for {url}. Skipping.")
            return None
    except requests.RequestException as e:
        logger.error(f"   - ❌ Failed to scrape {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"   - ❌ An unexpected error occurred while scraping {url}: {e}")
        return None

def deep_style_analysis(max_articles=100):
    """
    Performs a deep analysis of the latest articles to extract stylistic features.
    
    Args:
        max_articles: Maximum number of articles to analyze (default: 100)
    
    Returns:
        Dictionary containing analysis results, or None if analysis fails
    """
    logger.info(f"[1/3] Running deep analysis on up to {max_articles} articles...")
    
    # Get the Google Sheet connection
    try:
        from my_framework.style_guru.training import get_sheet
        sheet = get_sheet()
    except ImportError as e:
        logger.error(f"   - ❌ Failed to import get_sheet: {e}")
        return None
    except Exception as e:
        logger.error(f"   - ❌ Failed to get sheet connection: {e}")
        return None
    
    urls = get_article_urls(sheet, max_articles)
    if not urls:
        logger.error("   - ❌ No URLs found to analyze.")
        return None

    all_texts = []
    for i, url in enumerate(urls):
        logger.info(f"   - Scraping article {i+1}/{len(urls)}: {url}")
        content = scrape_article_content(url)
        if content:
            all_texts.append(content)
        time.sleep(1)  # Be respectful to the server

    if not all_texts:
        logger.error("   - ❌ Failed to scrape content from any URLs.")
        return None
        
    # Placeholder for actual analysis logic
    # In a real scenario, this would involve complex NLP feature extraction
    logger.info("   - Performing NLP analysis on scraped texts (placeholder)...")
    analysis_results = {
        "avg_sentence_length": 18.5, 
        "keyword_density": 0.02,
        "articles_analyzed": len(all_texts),
        "version": "1.0"
    }
    
    logger.info(f"[2/3] ✅ Deep analysis complete. Analyzed {len(all_texts)} articles.")
    return analysis_results
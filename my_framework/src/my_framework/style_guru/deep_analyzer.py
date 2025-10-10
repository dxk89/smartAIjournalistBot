# File: src/my_framework/style_guru/deep_analyzer.py
import requests
from bs4 import BeautifulSoup
import time
import re
from my_framework.agents.loggerbot import LoggerBot

logger = LoggerBot.get_logger()

RSS_URLS = [
    "https://www.intellinews.com/feed/atom?type=full_text",
    "https://www.intellinews.com/feed?client=bloomberg"
]

def clean_html_content(html_text):
    """Remove HTML tags and clean up the text content."""
    # Remove HTML tags
    clean_text = re.sub(r'<[^>]+>', '', html_text)
    # Remove extra whitespace
    clean_text = re.sub(r'\s+', ' ', clean_text)
    # Remove common HTML entities
    clean_text = clean_text.replace('&nbsp;', ' ')
    clean_text = clean_text.replace('&amp;', '&')
    clean_text = clean_text.replace('&lt;', '<')
    clean_text = clean_text.replace('&gt;', '>')
    return clean_text.strip()

def fetch_articles_from_rss(max_articles=100):
    """Fetch articles from IntelliNews RSS feeds."""
    all_articles = []
    
    logger.info(f"   - Fetching articles from {len(RSS_URLS)} RSS feeds...")
    
    for url in RSS_URLS:
        try:
            logger.info(f"   - Accessing RSS feed: {url}")
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            r.raise_for_status()
            
            # Parse as XML
            soup = BeautifulSoup(r.content, "xml")
            entries = soup.find_all("entry")
            logger.info(f"   - Found {len(entries)} entries in feed")
            
            for e in entries:
                try:
                    title_elem = e.find("title")
                    content_elem = e.find("content")
                    link_elem = e.find("link")
                    
                    if not title_elem or not content_elem:
                        continue
                    
                    title = title_elem.text.strip()
                    raw_content = content_elem.text
                    url = link_elem.get('href', '') if link_elem else ''
                    
                    # Clean HTML from content
                    clean_content = clean_html_content(raw_content)
                    
                    # Only include articles with substantial content (> 300 chars)
                    if len(clean_content) > 300:
                        all_articles.append({
                            "title": title,
                            "text": clean_content,
                            "url": url
                        })
                    
                    # Stop if we've reached the limit
                    if len(all_articles) >= max_articles:
                        break
                        
                except Exception as e:
                    logger.warning(f"   - ⚠️ Error parsing entry: {e}")
                    continue
            
            # Stop if we've reached the limit
            if len(all_articles) >= max_articles:
                break
                    
        except Exception as e:
            logger.error(f"   - ❌ Error fetching RSS feed {url}: {e}")
            continue
    
    logger.info(f"   - Successfully fetched {len(all_articles)} articles")
    return all_articles[:max_articles]

def analyze_text_style(text):
    """Analyze stylistic features of text."""
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Calculate basic metrics
    avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
    avg_sentence_length = len(words) / len(sentences) if sentences else 0
    
    # Count sentence types
    questions = len([s for s in sentences if s.strip().endswith('?')])
    exclamations = len([s for s in sentences if s.strip().endswith('!')])
    
    # Look for common journalistic patterns
    quotes = text.count('"')
    numbers = len(re.findall(r'\d+', text))
    
    return {
        "avg_word_length": avg_word_length,
        "avg_sentence_length": avg_sentence_length,
        "total_words": len(words),
        "total_sentences": len(sentences),
        "question_ratio": questions / len(sentences) if sentences else 0,
        "exclamation_ratio": exclamations / len(sentences) if sentences else 0,
        "quote_count": quotes,
        "number_count": numbers
    }

def deep_style_analysis(max_articles=100):
    """
    Performs a deep analysis of the latest articles to extract stylistic features.
    
    Args:
        max_articles: Maximum number of articles to analyze (default: 100)
    
    Returns:
        Dictionary containing analysis results, or None if analysis fails
    """
    logger.info(f"[1/3] Running deep analysis on up to {max_articles} articles...")
    
    # Fetch articles from RSS
    articles = fetch_articles_from_rss(max_articles)
    
    if not articles:
        logger.error("   - ❌ No articles found to analyze.")
        return None

    # Analyze stylistic features
    logger.info("   - Performing NLP analysis on fetched articles...")
    
    all_metrics = []
    for i, article in enumerate(articles, 1):
        try:
            text = article['text']
            metrics = analyze_text_style(text)
            all_metrics.append(metrics)
            
            if i % 10 == 0:
                logger.info(f"   - Analyzed {i}/{len(articles)} articles...")
                
        except Exception as e:
            logger.warning(f"   - ⚠️ Error analyzing article: {e}")
            continue
    
    if not all_metrics:
        logger.error("   - ❌ Failed to analyze any articles.")
        return None
    
    # Aggregate metrics
    analysis_results = {
        "articles_analyzed": len(all_metrics),
        "version": "1.0",
        "avg_word_length": sum(m["avg_word_length"] for m in all_metrics) / len(all_metrics),
        "avg_sentence_length": sum(m["avg_sentence_length"] for m in all_metrics) / len(all_metrics),
        "avg_words_per_article": sum(m["total_words"] for m in all_metrics) / len(all_metrics),
        "avg_sentences_per_article": sum(m["total_sentences"] for m in all_metrics) / len(all_metrics),
        "question_ratio": sum(m["question_ratio"] for m in all_metrics) / len(all_metrics),
        "exclamation_ratio": sum(m["exclamation_ratio"] for m in all_metrics) / len(all_metrics),
        "avg_quotes_per_article": sum(m["quote_count"] for m in all_metrics) / len(all_metrics),
        "avg_numbers_per_article": sum(m["number_count"] for m in all_metrics) / len(all_metrics)
    }
    
    # Save framework to file
    import json
    framework_path = "intellinews_style_framework.json"
    try:
        with open(framework_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2)
        logger.info(f"   - ✅ Saved style framework to {framework_path}")
    except Exception as e:
        logger.error(f"   - ⚠️ Failed to save framework: {e}")
    
    logger.info(f"[2/3] ✅ Deep analysis complete. Analyzed {len(all_metrics)} articles.")
    logger.info(f"   - Average sentence length: {analysis_results['avg_sentence_length']:.1f} words")
    logger.info(f"   - Average word length: {analysis_results['avg_word_length']:.1f} characters")
    
    return analysis_results
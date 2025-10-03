# File: src/my_framework/style_guru/training.py

import os
import re
import time
from pathlib import Path
import numpy as np
import requests
from bs4 import BeautifulSoup
from .model import AdvancedNeuralAgent
from .features import text_features

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

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

def fetch_rss():
    """Fetch articles from IntelliNews RSS feeds with full content."""
    all_articles = []
    
    for url in RSS_URLS:
        try:
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            r.raise_for_status()
            
            # Parse as XML
            soup = BeautifulSoup(r.content, "xml")
            entries = soup.find_all("entry")
            
            for e in entries:
                try:
                    title_elem = e.find("title")
                    content_elem = e.find("content")
                    
                    if not title_elem or not content_elem:
                        continue
                    
                    title = title_elem.text.strip()
                    raw_content = content_elem.text
                    
                    # Clean HTML from content
                    clean_content = clean_html_content(raw_content)
                    
                    # Only include articles with substantial content (> 300 chars)
                    if len(clean_content) > 300:
                        all_articles.append({
                            "title": title,
                            "text": clean_content
                        })
                    else:
                        pass
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            continue
    
    return all_articles

def build_dataset(limit=100):
    """Build training dataset from fetched articles."""
    articles = fetch_rss()
    
    if not articles:
        return
    
    articles = articles[:limit]

    X, y = [], []
    for idx, article in enumerate(articles, 1):
        try:
            body = article['text']
            if not body or not body.strip():
                continue
                
            feats = text_features(body)
            X.append(feats)
            y.append(1.0)  # All IntelliNews articles are positive examples
            
            word_count = len(body.split())
            
        except Exception as e:
            continue

    if X:
        X, y = np.array(X), np.array(y)
        np.save(DATA_DIR / "X.npy", X)
        np.save(DATA_DIR / "y.npy", y)
    else:
        pass

def train_model():
    """Train the neural style scoring model."""
    try:
        X = np.load(DATA_DIR / "X.npy")
        y = np.load(DATA_DIR / "y.npy")
        
        agent = AdvancedNeuralAgent(input_size=X.shape[1])
        agent.train(X, y, epochs=200)
        agent.save(DATA_DIR / "model_weights.npz")
        
    except FileNotFoundError:
        pass
    except Exception as e:
        pass
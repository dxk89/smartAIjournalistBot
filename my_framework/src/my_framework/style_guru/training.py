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
            print(f"[ℹ️] Fetching RSS feed: {url}")
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            r.raise_for_status()
            
            # Parse as XML
            soup = BeautifulSoup(r.content, "xml")
            entries = soup.find_all("entry")
            
            print(f"[ℹ️] Found {len(entries)} entries in feed")
            
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
                        print(f"[+] Added article: {title[:60]}... ({len(clean_content)} chars)")
                    else:
                        print(f"[!] Skipped short article: {title[:60]}...")
                        
                except Exception as e:
                    print(f"[!] Error processing entry: {e}")
                    continue
                    
        except Exception as e:
            print(f"[!] RSS fetch failed for {url}: {e}")
            continue
    
    print(f"[✅] Total articles fetched: {len(all_articles)}")
    return all_articles

def build_dataset(limit=100):
    """Build training dataset from fetched articles."""
    articles = fetch_rss()
    
    if not articles:
        print("[❌] No articles fetched - cannot build dataset")
        return
    
    articles = articles[:limit]
    print(f"[ℹ️] Building dataset with {len(articles)} articles")

    X, y = [], []
    for idx, article in enumerate(articles, 1):
        try:
            body = article['text']
            if not body or not body.strip():
                print(f"[!] Skipped empty article: {article['title']}")
                continue
                
            feats = text_features(body)
            X.append(feats)
            y.append(1.0)  # All IntelliNews articles are positive examples
            
            word_count = len(body.split())
            print(f"[+] ({idx}/{len(articles)}) {article['title'][:50]}... — {word_count} words")
            
        except Exception as e:
            print(f"[!] Failed processing {article['title']}: {e}")
            continue

    if X:
        X, y = np.array(X), np.array(y)
        np.save(DATA_DIR / "X.npy", X)
        np.save(DATA_DIR / "y.npy", y)
        print(f"[✅] Dataset built: {X.shape[0]} samples, {X.shape[1]} features")
    else:
        print("[❌] No valid articles processed — dataset not created")

def train_model():
    """Train the neural style scoring model."""
    try:
        X = np.load(DATA_DIR / "X.npy")
        y = np.load(DATA_DIR / "y.npy")
        
        print(f"[ℹ️] Training model with {len(X)} samples...")
        agent = AdvancedNeuralAgent(input_size=X.shape[1])
        agent.train(X, y, epochs=200)
        agent.save(DATA_DIR / "model_weights.npz")
        
        print("[✅] Model trained and saved.")
    except FileNotFoundError:
        print("[❌] Dataset files not found. Run build_dataset() first.")
    except Exception as e:
        print(f"[❌] Training failed: {e}")
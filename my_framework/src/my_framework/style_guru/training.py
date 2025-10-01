# File: src/my_framework/style_guru/training.py

import os
import re
import time
from pathlib import Path
import numpy as np
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from .model import AdvancedNeuralAgent
from .features import text_features

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

RSS_URLS = [
    "https://www.intellinews.com/feed/atom?type=full_text",
    "https://www.intellinews.com/feed?client=bloomberg"
]
START_URL = "https://intellinews.com/"
ARTICLE_PATTERN = re.compile(r"-\d{6}/")

def fetch_rss():
    all_articles = []
    for url in RSS_URLS:
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "xml")
            entries = soup.find_all("entry")
            for e in entries:
                title = e.find("title").text
                content = e.find("content").text
                all_articles.append({"title": title, "text": content})
            print(f"[ℹ️] RSS: found {len(entries)} articles from feed: {url}")
        except Exception as e:
            print(f"[!] RSS fetch failed for {url}: {e}")
    return all_articles

def build_dataset(limit=100):
    articles = fetch_rss()
    articles = articles[:limit]
    print(f"[ℹ️] Total articles to process: {len(articles)}")

    X, y = [], []
    for idx, article in enumerate(articles, 1):
        try:
            body = article['text']
            if not body or not body.strip():
                print(f"[!] Skipped empty or invalid article: {article['title']}")
                continue
            feats = text_features(body)
            X.append(feats)
            y.append(1.0) # Assume all fetched articles are style-compliant (positive examples)
            print(f"[+] ({idx}) {article['title']} — {len(body.split())} words")
        except Exception as e:
            print(f"[!] Failed processing {article['title']}: {e}")

    if X:
        X, y = np.array(X), np.array(y)
        np.save(DATA_DIR / "X.npy", X)
        np.save(DATA_DIR / "y.npy", y)
        print(f"[✅] Built dataset: {X.shape[0]} samples, {X.shape[1]} features")
    else:
        print("[❌] No articles processed — dataset not created")

def train_model():
    X = np.load("data/X.npy")
    y = np.load("data/y.npy")
    agent = AdvancedNeuralAgent(input_size=X.shape[1])
    agent.train(X, y, epochs=200)
    agent.save("data/model_weights.npz")
    print("[✅] Model trained and saved.")
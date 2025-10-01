# File: src/my_framework/style_guru/features.py

import numpy as np
import nltk

def text_features(text: str):
    """
    Calculates text features for a given string of text.
    """
    words = nltk.word_tokenize(text)
    n = len(words)
    avg_len = np.mean([len(w) for w in words]) if words else 0
    sents = nltk.sent_tokenize(text)
    avg_sent = np.mean([len(nltk.word_tokenize(s)) for s in sents]) if sents else 0
    numbers = sum(1 for w in words if w.isdigit())
    caps = sum(1 for w in words if w.isupper() and len(w) > 1)
    return np.array([n, avg_len, avg_sent, numbers, caps], dtype=float)
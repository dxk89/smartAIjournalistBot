# File: src/my_framework/style_guru/features.py

import numpy as np
import nltk

def text_features(text: str):
    """
    Calculates text features for a given string of text, now with safeguards.
    """
    if not isinstance(text, str) or not text.strip():
        return np.zeros(5, dtype=float)

    try:
        words = nltk.word_tokenize(text)
        sents = nltk.sent_tokenize(text)
    except Exception:
        # Fallback for tokenization errors on weird text
        words = text.split()
        sents = text.split('.')

    n = len(words)
    if n == 0:
        return np.zeros(5, dtype=float)

    # Calculate features, ensuring no division by zero
    avg_len = np.mean([len(w) for w in words]) if words else 0
    avg_sent = np.mean([len(nltk.word_tokenize(s)) for s in sents]) if sents else 0
    numbers = sum(1 for w in words if w.isdigit())
    caps = sum(1 for w in words if w.isupper() and len(w) > 1)
    
    return np.array([n, avg_len, avg_sent, numbers, caps], dtype=float)
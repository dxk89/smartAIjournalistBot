# File: my_framework/src/my_framework/style_guru/__init__.py

"""
Initializes the style_guru package, making key functions directly importable.
This helps create a cleaner and more robust package structure.
"""

from .deep_analyzer import deep_style_analysis
from .training import build_dataset, train_model

__all__ = [
    'deep_style_analysis',
    'build_dataset',
    'train_model'
]
"""
Categorizers for Browser Organiser MCP.

This module provides different categorization strategies:
- Rule-based categorization (fast, deterministic)
- AI-based categorization (smart, contextual)
- Hybrid categorization (combines both approaches)
"""

from .rule_categorizer import RuleCategorizer

__all__ = [
    "RuleCategorizer",
]

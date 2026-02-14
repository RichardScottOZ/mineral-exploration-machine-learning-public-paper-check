"""
Paper Accessibility Checker

A tool to check and manage accessibility of academic papers, reports, and theses.
"""

__version__ = "0.1.0"

from paper_checker.models import Paper, AccessibilityStatus
from paper_checker.database import PaperDatabase

__all__ = ["Paper", "AccessibilityStatus", "PaperDatabase"]

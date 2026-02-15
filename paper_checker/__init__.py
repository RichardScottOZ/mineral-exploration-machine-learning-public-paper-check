"""
Paper Accessibility Checker

A tool to check and manage accessibility of academic papers, reports, and theses.
Designed to work with the mineral-exploration-machine-learning repository by default.
"""

__version__ = "0.1.0"

from paper_checker.models import Paper, AccessibilityStatus
from paper_checker.database import PaperDatabase
from paper_checker.readme_parser import scan_repo, parse_readme, fetch_readme

__all__ = [
    "Paper",
    "AccessibilityStatus",
    "PaperDatabase",
    "scan_repo",
    "parse_readme",
    "fetch_readme",
]

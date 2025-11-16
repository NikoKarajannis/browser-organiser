"""
Browser Organiser MCP - Package Initialization

This package provides functionality to organize Microsoft Edge browser bookmarks
using a combination of AI-powered analysis and rule-based categorization.

Modules:
- `models`: Pydantic data models for bookmarks, folders, categories, and results
- `service`: BrowserCleanerService for bookmark organization
- `utils`: Helper functions for file handling and parsing
- `categorizers`: Rule-based and AI-based categorization engines
- `safety`: Safety checks and backup functionality
"""

from .models import (
    Bookmark,
    Folder,
    Category,
    CategoryRule,
    CategorizationMethod,
    CategorizationResult,
    BookmarkMove,
    OrganizationPlan,
    BackupMetadata,
    BookmarkOverview,
    AnalysisResult,
    OrganizationResult,
    SearchResult,
)
from .service import BrowserCleanerService
from .safety import SafetyChecker

__all__ = [
    "Bookmark",
    "Folder",
    "Category",
    "CategoryRule",
    "CategorizationMethod",
    "CategorizationResult",
    "BookmarkMove",
    "OrganizationPlan",
    "BackupMetadata",
    "BookmarkOverview",
    "AnalysisResult",
    "OrganizationResult",
    "SearchResult",
    "BrowserCleanerService",
    "SafetyChecker",
]

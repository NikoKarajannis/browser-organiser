"""
Pydantic models for Browser Organiser MCP.

This module defines all data models used throughout the application,
including bookmarks, folders, categories, and operation results.
"""

from pydantic import BaseModel, Field, HttpUrl, field_validator
from datetime import datetime, timedelta
from typing import Optional, Literal, Union
from enum import Enum
from pathlib import Path
import re


class CategorizationMethod(str, Enum):
    """Method used to categorize a bookmark"""
    AI = "ai"
    RULE = "rule"
    MANUAL = "manual"
    NONE = "none"


class Bookmark(BaseModel):
    """Represents a single bookmark entry"""
    id: str
    name: str
    url: HttpUrl
    date_added: datetime
    date_last_used: Optional[datetime] = None
    guid: str
    current_folder: Optional[str] = None
    suggested_category: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    categorization_method: CategorizationMethod = CategorizationMethod.NONE

    @field_validator('date_added', 'date_last_used', mode='before')
    @classmethod
    def parse_webkit_timestamp(cls, v):
        """Convert WebKit timestamp to datetime or parse ISO datetime"""
        if v is None:
            return None

        # If already a datetime, return as-is
        if isinstance(v, datetime):
            return v

        if isinstance(v, str):
            # Check if it's a WebKit timestamp (all digits, very large number)
            if v.isdigit() and len(v) > 15:  # WebKit timestamps are 17+ digits
                # WebKit timestamp: microseconds since Jan 1, 1601
                WEBKIT_EPOCH = datetime(1601, 1, 1)
                microseconds = int(v)
                return WEBKIT_EPOCH + timedelta(microseconds=microseconds)
            else:
                # Parse as ISO datetime string
                return datetime.fromisoformat(v.replace('Z', '+00:00'))

        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "123",
                    "name": "Python Documentation",
                    "url": "https://docs.python.org",
                    "date_added": "2024-03-15T10:20:00Z",
                    "guid": "abc-123-def",
                    "suggested_category": "Development/Documentation",
                    "confidence": 0.95,
                    "categorization_method": "rule"
                }
            ]
        }
    }


class Folder(BaseModel):
    """Represents a bookmark folder (can contain bookmarks and subfolders)"""
    id: str
    name: str
    children: list[Union['Bookmark', 'Folder']] = Field(default_factory=list)
    date_added: datetime
    date_modified: Optional[datetime] = None
    guid: str
    parent_path: str = ""
    type: Literal["folder"] = "folder"

    @field_validator('date_added', 'date_modified', mode='before')
    @classmethod
    def parse_webkit_timestamp(cls, v):
        """Convert WebKit timestamp to datetime or parse ISO datetime"""
        if v is None:
            return None

        # If already a datetime, return as-is
        if isinstance(v, datetime):
            return v

        if isinstance(v, str):
            # Check if it's a WebKit timestamp (all digits, very large number)
            if v.isdigit() and len(v) > 15:  # WebKit timestamps are 17+ digits
                # WebKit timestamp: microseconds since Jan 1, 1601
                WEBKIT_EPOCH = datetime(1601, 1, 1)
                microseconds = int(v)
                return WEBKIT_EPOCH + timedelta(microseconds=microseconds)
            else:
                # Parse as ISO datetime string
                return datetime.fromisoformat(v.replace('Z', '+00:00'))

        return v

    def get_all_bookmarks(self) -> list[Bookmark]:
        """Recursively get all bookmarks in this folder"""
        bookmarks = []
        for child in self.children:
            if isinstance(child, Bookmark):
                bookmarks.append(child)
            elif isinstance(child, Folder):
                bookmarks.extend(child.get_all_bookmarks())
        return bookmarks

    def get_bookmark_count(self) -> int:
        """Count all bookmarks recursively"""
        return len(self.get_all_bookmarks())

    def get_folder_count(self) -> int:
        """Count all subfolders recursively"""
        count = 0
        for child in self.children:
            if isinstance(child, Folder):
                count += 1 + child.get_folder_count()
        return count


class CategoryRule(BaseModel):
    """Rule for categorizing bookmarks"""
    domain: Optional[str] = None
    domain_pattern: Optional[str] = None  # e.g., "*.readthedocs.io"
    url_contains: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)

    def matches(self, bookmark: Bookmark) -> bool:
        """Check if this rule matches the bookmark"""
        url_str = str(bookmark.url)

        # Domain exact match
        if self.domain and self.domain in url_str:
            return True

        # Domain pattern match (simple wildcard)
        if self.domain_pattern:
            pattern = self.domain_pattern.replace(".", r"\.").replace("*", ".*")
            if re.search(pattern, url_str):
                return True

        # URL contains
        if self.url_contains and self.url_contains in url_str:
            return True

        # Keyword match in title
        if self.keywords:
            title_lower = bookmark.name.lower()
            if any(keyword.lower() in title_lower for keyword in self.keywords):
                return True

        return False


class Category(BaseModel):
    """Category definition with matching rules"""
    name: str
    rules: list[CategoryRule]
    ai_description: str  # Description for AI categorizer context
    priority: int = Field(default=0, ge=0)  # Higher priority checked first

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Development/GitHub",
                    "priority": 10,
                    "rules": [
                        {"domain": "github.com"},
                        {"domain": "gist.github.com"}
                    ],
                    "ai_description": "GitHub repositories, code hosting, version control"
                }
            ]
        }
    }


class CategorizationResult(BaseModel):
    """Result of categorizing a single bookmark"""
    bookmark_id: str
    category: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    method: CategorizationMethod
    reasoning: Optional[str] = None


class BookmarkMove(BaseModel):
    """Represents a planned move of a bookmark"""
    bookmark: Bookmark
    from_folder: str
    to_folder: str
    confidence: float = Field(ge=0.0, le=1.0)
    method: CategorizationMethod


class OrganizationPlan(BaseModel):
    """Plan for reorganizing bookmarks"""
    total_bookmarks: int
    bookmarks_to_move: list[BookmarkMove]
    new_folders_needed: list[str]
    estimated_changes: int
    safety_warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def has_warnings(self) -> bool:
        """Check if there are any safety warnings"""
        return len(self.safety_warnings) > 0


class BackupMetadata(BaseModel):
    """Metadata for a bookmark backup"""
    original_path: str
    backup_path: str
    timestamp: datetime = Field(default_factory=datetime.now)
    checksum_before: str
    checksum_after: Optional[str] = None
    bookmark_count: int

    def is_valid(self) -> bool:
        """Check if backup file exists and is valid"""
        return Path(self.backup_path).exists()


class BookmarkOverview(BaseModel):
    """Overview of bookmark structure and statistics"""
    total_bookmarks: int
    total_folders: int
    uncategorized_count: int
    folder_structure: dict[str, dict]
    top_domains: list[dict[str, int]]
    last_analyzed: Optional[datetime] = None


class AnalysisResult(BaseModel):
    """Result of bookmark analysis"""
    analysis_complete: bool
    total_analyzed: int
    categorization_results: dict[str, int]  # {"rule_based": 100, "ai_based": 50, ...}
    suggested_moves: list[BookmarkMove]
    new_folders_needed: list[str]
    estimated_time_seconds: float


class OrganizationResult(BaseModel):
    """Result of bookmark organization operation"""
    success: bool
    backup_created: Optional[str] = None
    bookmarks_moved: int
    folders_created: int
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float
    rollback_available: bool = False


class SearchResult(BaseModel):
    """Search results for bookmarks"""
    query: str
    results_count: int
    results: list[Bookmark]
    search_fields: list[str]


# Enable forward references for recursive models
Folder.model_rebuild()

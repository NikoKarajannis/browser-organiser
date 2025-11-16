# Browser Organiser MCP - Development Documentation

## Project Overview

An MCP (Model Context Protocol) server that intelligently organizes Microsoft Edge browser bookmarks using a combination of AI-powered analysis and rule-based categorization.

**Status**: Development Phase
**Version**: 0.1.0
**Target Browser**: Microsoft Edge (Chromium)
**Python**: >=3.12

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Server (FastMCP)                         │
│                    Port: 9000 | stdio/http                       │
├─────────────────────────────────────────────────────────────────┤
│  MCP Tools (exposed to Claude):                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ 1. get_bookmark_overview()                             │     │
│  │    → Returns statistics and folder structure           │     │
│  │                                                         │     │
│  │ 2. analyze_bookmarks(dry_run=True)                     │     │
│  │    → Analyzes and suggests categorization              │     │
│  │                                                         │     │
│  │ 3. organize_bookmarks(dry_run=False, backup=True)      │     │
│  │    → Executes reorganization with safety checks        │     │
│  │                                                         │     │
│  │ 4. create_folder_structure(categories: list)           │     │
│  │    → Sets up recommended folder hierarchy              │     │
│  │                                                         │     │
│  │ 5. search_bookmarks(query: str)                        │     │
│  │    → Find bookmarks by title, URL, or content          │     │
│  │                                                         │     │
│  │ 6. get_uncategorized()                                 │     │
│  │    → List all bookmarks not in organized folders       │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BrowserCleanerService                         │
├─────────────────────────────────────────────────────────────────┤
│  Core Responsibilities:                                          │
│  • Locate and read Edge bookmarks JSON file                      │
│  • Parse recursive bookmark/folder structure                     │
│  • Coordinate categorization (AI + Rules)                        │
│  • Generate reorganization plan                                  │
│  • Execute moves with backup/rollback                            │
│  • Validate Edge process state (warn if running)                 │
└─────────────────────────────────────────────────────────────────┘
           ↓                                    ↓
┌──────────────────────────┐      ┌────────────────────────────────┐
│   AI Categorizer         │      │   Rule-based Categorizer       │
│  (LLM-powered)           │      │   (Pattern matching)           │
├──────────────────────────┤      ├────────────────────────────────┤
│ • Analyzes URL + title   │      │ Predefined rules:              │
│ • Context understanding  │      │ • Domain patterns              │
│ • Suggests new categories│      │   github.com → Dev/GitHub      │
│ • Handles ambiguous cases│      │   stackoverflow → Dev/Q&A      │
│ • Merges similar folders │      │ • Keyword detection            │
│                          │      │   "tutorial" → Learning        │
│ Fallback: Returns None   │      │ • URL structure analysis       │
│ if confidence low        │      │   /docs/ → Documentation       │
│                          │      │                                │
│                          │      │ Fallback: "Uncategorized"      │
└──────────────────────────┘      └────────────────────────────────┘
```

---

## Data Models

### Bookmark Structure

Edge stores bookmarks in JSON format at:
```
Windows: %LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Bookmarks
Linux: ~/.config/microsoft-edge/Default/Bookmarks
```

**Simplified Edge Bookmark JSON Structure:**
```json
{
  "checksum": "...",
  "roots": {
    "bookmark_bar": {
      "children": [...],
      "name": "Bookmarks bar",
      "type": "folder"
    },
    "other": {
      "children": [...],
      "name": "Other favorites",
      "type": "folder"
    },
    "synced": {
      "children": [...],
      "name": "Mobile favorites",
      "type": "folder"
    }
  },
  "version": 1
}
```

**Bookmark Entry:**
```json
{
  "date_added": "13370000000000000",
  "date_last_used": "13370000000000000",
  "guid": "...",
  "id": "123",
  "name": "Example Site",
  "type": "url",
  "url": "https://example.com/page"
}
```

**Folder Entry:**
```json
{
  "children": [...],
  "date_added": "13370000000000000",
  "date_modified": "13370000000000000",
  "guid": "...",
  "id": "456",
  "name": "Development",
  "type": "folder"
}
```

### Pydantic Data Models

```python
from pydantic import BaseModel, Field, HttpUrl, field_validator
from datetime import datetime
from typing import Optional, Literal
from enum import Enum

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
        """Convert WebKit timestamp to datetime"""
        if v is None:
            return None
        if isinstance(v, str):
            # WebKit timestamp: microseconds since Jan 1, 1601
            WEBKIT_EPOCH = datetime(1601, 1, 1)
            microseconds = int(v)
            return WEBKIT_EPOCH + timedelta(microseconds=microseconds)
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123",
                "name": "Python Documentation",
                "url": "https://docs.python.org",
                "date_added": "2024-03-15T10:20:00Z",
                "guid": "abc-123-def",
                "suggested_category": "Development/Documentation",
                "confidence": 0.95,
                "categorization_method": "rule"
            }
        }

class Folder(BaseModel):
    """Represents a bookmark folder (can contain bookmarks and subfolders)"""
    id: str
    name: str
    children: list['Bookmark | Folder'] = Field(default_factory=list)
    date_added: datetime
    date_modified: Optional[datetime] = None
    guid: str
    parent_path: str = ""
    type: Literal["folder"] = "folder"

    @field_validator('date_added', 'date_modified', mode='before')
    @classmethod
    def parse_webkit_timestamp(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            WEBKIT_EPOCH = datetime(1601, 1, 1)
            microseconds = int(v)
            return WEBKIT_EPOCH + timedelta(microseconds=microseconds)
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
            pattern = self.domain_pattern.replace("*", ".*")
            if re.match(pattern, url_str):
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

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Development/GitHub",
                "priority": 10,
                "rules": [
                    {"domain": "github.com"},
                    {"domain": "gist.github.com"}
                ],
                "ai_description": "GitHub repositories, code hosting, version control"
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
```

---

## Categorization Strategy

### 1. Rule-based Categorizer (Fast, Deterministic)

**Category Definitions (`config/categories.yaml`):**

```yaml
categories:
  - name: Development/GitHub
    priority: 10
    ai_description: GitHub repositories, code hosting, version control, open source projects
    rules:
      - domain: github.com
      - domain: gist.github.com

  - name: Development/Documentation
    priority: 8
    ai_description: Technical documentation, API references, programming guides
    rules:
      - url_contains: /docs/
      - url_contains: /documentation/
      - domain_pattern: "*.readthedocs.io"
      - keywords: [api docs, reference, guide]

  - name: Development/StackOverflow
    priority: 9
    ai_description: Programming Q&A, troubleshooting, code solutions
    rules:
      - domain: stackoverflow.com
      - domain: stackexchange.com
      - domain: serverfault.com

  - name: Development/Tools
    priority: 7
    ai_description: Developer tools, online utilities, formatters, validators
    rules:
      - domain: regex101.com
      - domain: jsonlint.com
      - domain: codebeautify.org
      - keywords: [converter, formatter, validator]

  - name: Learning/Tutorials
    priority: 6
    ai_description: Educational content, tutorials, courses, learning materials
    rules:
      - keywords: [tutorial, learn, course, guide, how-to]
      - domain: udemy.com
      - domain: coursera.org
      - domain: freecodecamp.org

  - name: Media/Video
    priority: 5
    ai_description: Video streaming, video content platforms
    rules:
      - domain: youtube.com
      - domain: vimeo.com
      - domain: twitch.tv

  - name: Social/Professional
    priority: 5
    ai_description: Professional networking, social media platforms
    rules:
      - domain: linkedin.com
      - domain: twitter.com
      - domain: x.com

  - name: Shopping
    priority: 4
    ai_description: E-commerce, online shopping, product pages
    rules:
      - domain: amazon.com
      - domain: ebay.com
      - keywords: [shop, store, buy]

  - name: News
    priority: 4
    ai_description: News articles, journalism, current events
    rules:
      - domain_pattern: "*.news"
      - keywords: [news, article, blog]
      - domain: bbc.com
      - domain: reuters.com
```

**Matching Algorithm:**
```python
class RuleCategorizer:
    def __init__(self, categories: list[Category]):
        # Sort by priority (highest first)
        self.categories = sorted(categories, key=lambda c: c.priority, reverse=True)

    def categorize(self, bookmark: Bookmark) -> Optional[CategorizationResult]:
        """Try to categorize using rules"""
        for category in self.categories:
            for rule in category.rules:
                if rule.matches(bookmark):
                    return CategorizationResult(
                        bookmark_id=bookmark.id,
                        category=category.name,
                        confidence=1.0,
                        method=CategorizationMethod.RULE
                    )
        return None
```

### 2. AI Categorizer (Smart, Contextual)

**Input to LLM:**
```python
class AICategorizer:
    def categorize(self, bookmark: Bookmark, available_categories: list[Category]) -> Optional[CategorizationResult]:
        prompt = f"""
        Analyze this bookmark and suggest the best category:

        Title: "{bookmark.name}"
        URL: "{bookmark.url}"

        Available categories:
        {self._format_categories(available_categories)}

        Return JSON with this structure:
        {{
          "category": "category/subcategory",
          "confidence": 0.0-1.0,
          "reasoning": "brief explanation"
        }}

        If confidence < 0.7, return null for category.
        """

        # Use MCP context or API call to LLM
        response = self._call_llm(prompt)
        return self._parse_response(response, bookmark.id)
```

**Fallback Chain:**
```
Rule Match (instant)
    ↓ (no match)
AI Analysis (2-3s, batch processing)
    ↓ (low confidence)
"Uncategorized" folder
```

### 3. Hybrid Strategy

```python
class HybridCategorizer:
    def __init__(self, rule_categorizer: RuleCategorizer, ai_categorizer: AICategorizer):
        self.rule_cat = rule_categorizer
        self.ai_cat = ai_categorizer

    def categorize(self, bookmark: Bookmark, use_ai: bool = True) -> CategorizationResult:
        # Try rule-based first (fast)
        result = self.rule_cat.categorize(bookmark)
        if result:
            return result

        # Fallback to AI (slower but smarter)
        if use_ai:
            result = self.ai_cat.categorize(bookmark, self.rule_cat.categories)
            if result and result.confidence >= 0.7:
                return result

        # Last resort
        return CategorizationResult(
            bookmark_id=bookmark.id,
            category="Uncategorized",
            confidence=0.0,
            method=CategorizationMethod.NONE
        )
```

---

## Safety & Backup System

### Pre-flight Checks

```python
class SafetyChecker:
    @staticmethod
    def is_edge_running() -> bool:
        """Check if Edge is running (file may be locked)"""
        import psutil
        for proc in psutil.process_iter(['name']):
            if 'msedge' in proc.info['name'].lower():
                return True
        return False

    @staticmethod
    def validate_bookmarks_file(path: Path) -> tuple[bool, Optional[str]]:
        """Validate bookmark file integrity"""
        if not path.exists():
            return False, f"File not found: {path}"

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check expected structure
            if 'roots' not in data or 'version' not in data:
                return False, "Invalid bookmark file structure"

            return True, None
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"

    @staticmethod
    def create_backup(bookmarks_path: Path) -> BackupMetadata:
        """Create timestamped backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = bookmarks_path.parent / f"Bookmarks.backup.{timestamp}"

        # Calculate checksum
        checksum = hashlib.md5(bookmarks_path.read_bytes()).hexdigest()

        # Copy file
        shutil.copy2(bookmarks_path, backup_path)

        # Count bookmarks
        with open(bookmarks_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        bookmark_count = _count_bookmarks_recursive(data['roots'])

        return BackupMetadata(
            original_path=str(bookmarks_path),
            backup_path=str(backup_path),
            checksum_before=checksum,
            bookmark_count=bookmark_count
        )

    @staticmethod
    def rollback(metadata: BackupMetadata) -> bool:
        """Restore from backup"""
        if not metadata.is_valid():
            return False

        shutil.copy2(metadata.backup_path, metadata.original_path)
        return True
```

---

## Implementation Plan

### Phase 1: Core Infrastructure

- [ ] Install dependencies (pydantic, psutil for process checking)
- [ ] Create `src/models.py` with all Pydantic models
- [ ] Create `src/utils.py` with:
  - [ ] Edge bookmarks path detection (Windows/Linux)
  - [ ] WebKit timestamp conversion
  - [ ] JSON parser (raw JSON → Pydantic models)
  - [ ] Checksum calculator

### Phase 2: Categorization Engine

- [ ] Create `config/categories.yaml`
- [ ] Create `src/categorizers/rule_categorizer.py`:
  - [ ] YAML loader
  - [ ] Pattern matching logic
  - [ ] Priority-based selection
- [ ] Create `src/categorizers/ai_categorizer.py`:
  - [ ] LLM integration (MCP context)
  - [ ] Batch processing
  - [ ] Confidence scoring
- [ ] Create `src/categorizers/hybrid_categorizer.py`:
  - [ ] Combine rule + AI
  - [ ] Fallback logic

### Phase 3: Service Layer

- [ ] Create `src/service.py` - `BrowserCleanerService`:
  - [ ] `get_overview() -> BookmarkOverview`
  - [ ] `analyze(use_ai=True) -> AnalysisResult`
  - [ ] `create_plan(results) -> OrganizationPlan`
  - [ ] `execute_plan(plan, backup=True) -> OrganizationResult`
  - [ ] `search(query, fields) -> SearchResult`
  - [ ] Integration with SafetyChecker

### Phase 4: MCP Integration (server.py)

- [ ] Tool: `get_bookmark_overview() -> str`
- [ ] Tool: `analyze_bookmarks(dry_run, use_ai) -> str`
- [ ] Tool: `organize_bookmarks(dry_run, backup) -> str`
- [ ] Tool: `create_folder_structure(categories) -> str`
- [ ] Tool: `search_bookmarks(query) -> str`
- [ ] Tool: `get_uncategorized(limit) -> str`

### Phase 5: Testing

- [ ] Unit tests for models (validation, serialization)
- [ ] Unit tests for categorizers
- [ ] Integration tests with sample bookmark files
- [ ] Manual testing with real Edge bookmarks

---

## File Structure

```
browser-organiser/
├── server.py                      # MCP server entry point
├── pyproject.toml                 # Dependencies
├── .env                           # Environment variables
├── DEVELOPMENT.md                 # This file
├── README.md                      # User documentation
├── config/
│   └── categories.yaml            # Category definitions
├── src/
│   ├── __init__.py
│   ├── models.py                  # All Pydantic models
│   ├── utils.py                   # Helper functions
│   ├── service.py                 # BrowserCleanerService
│   ├── safety.py                  # SafetyChecker class
│   └── categorizers/
│       ├── __init__.py
│       ├── rule_categorizer.py    # Rule-based matching
│       ├── ai_categorizer.py      # LLM-based analysis
│       └── hybrid_categorizer.py  # Combined approach
├── tests/
│   ├── test_models.py
│   ├── test_categorizers.py
│   ├── test_service.py
│   └── fixtures/
│       └── sample_bookmarks.json
└── backups/                       # Auto-created backup directory
```

---

**Last Updated**: 2025-11-15
**Status**: Phase 1 - Core Infrastructure (Ready to start)
**Next Step**: Create Pydantic models in `src/models.py`

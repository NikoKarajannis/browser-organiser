"""
Browser Organiser MCP Server

This script initializes and runs the Browser Organiser MCP server.

The server uses the FastMCP framework to provide tools for organizing
Microsoft Edge browser bookmarks using AI and rule-based categorization.

Tools:

Organization Tools:
- get_bookmark_overview: Get statistics and overview of bookmarks
- analyze_bookmarks: Analyze bookmarks and suggest categorization
- organize_bookmarks: Execute bookmark organization with safety checks
- search_bookmarks: Search bookmarks by query
- get_uncategorized: List uncategorized bookmarks

Knowledge Base Tools (NEW):
- get_all_bookmarks: Access all bookmarks for semantic analysis
- get_bookmarks_by_category: Filter bookmarks by category
- get_bookmarks_by_folder: Get bookmarks from specific folder

The knowledge base tools allow Claude to use your bookmarks as a
queryable knowledge base during your work. Claude can semantically
search and recommend relevant resources based on your current context.

Usage:
    python server.py [stdio|sse|http]
"""

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "mcp[cli]>=1.21.1",
#     "pydantic>=2.11.7",
#     "python-dotenv>=1.2.1",
#     "psutil>=6.1.1",
#     "pyyaml>=6.0.2",
# ]
# ///

from mcp.server.fastmcp import FastMCP
from src.service import BrowserCleanerService
import json

# Initialize FastMCP server
mcp = FastMCP(
    name="Browser Organiser",
    stateless_http=True,
    host="0.0.0.0",  # Listen on all interfaces for tunneling/remote access
    port=9000,  # Using 9000 to avoid common conflicts
)

# Initialize service (will auto-detect Edge bookmarks path)
try:
    _service = BrowserCleanerService()
except Exception as e:
    print(f"Warning: Could not initialize BrowserCleanerService: {e}")
    print("Service will be initialized on first tool call.")
    _service = None


def _get_service() -> BrowserCleanerService:
    """Get or initialize the service instance."""
    global _service
    if _service is None:
        _service = BrowserCleanerService()
    return _service


@mcp.tool()
def get_bookmark_overview() -> str:
    """
    Get overview of bookmark structure and statistics.

    Returns:
        JSON string with bookmark statistics including:
        - Total bookmarks and folders
        - Uncategorized count
        - Folder structure
        - Top domains

    Example:
        {
          "total_bookmarks": 1523,
          "total_folders": 47,
          "uncategorized_count": 342,
          "folder_structure": {...},
          "top_domains": [...]
        }
    """
    service = _get_service()
    overview = service.get_overview()
    return overview.model_dump_json(indent=2)


@mcp.tool()
def analyze_bookmarks(use_ai: bool = False) -> str:
    """
    Analyze all bookmarks and suggest categorization.

    Args:
        use_ai: If True, use AI categorizer for unmatched bookmarks (not yet implemented)

    Returns:
        JSON string with analysis results including:
        - Total bookmarks analyzed
        - Categorization results breakdown
        - Suggested moves
        - New folders needed

    Example:
        {
          "analysis_complete": true,
          "total_analyzed": 1523,
          "categorization_results": {
            "rule_based": 1181,
            "ai_based": 0,
            "uncategorized": 342
          },
          "suggested_moves": [...],
          "new_folders_needed": ["Development/GitHub", ...]
        }
    """
    service = _get_service()
    analysis = service.analyze(use_ai=use_ai)
    return analysis.model_dump_json(indent=2)


@mcp.tool()
def organize_bookmarks(dry_run: bool = False, backup: bool = True) -> str:
    """
    Execute bookmark organization based on analysis.

    IMPORTANT: This modifies your browser bookmarks!
    Always run with dry_run=True first to preview changes.

    Args:
        dry_run: If True, only preview changes without modifying files (default: False)
        backup: If True, create backup before modifying (default: True, highly recommended)

    Returns:
        JSON string with organization results including:
        - Success status
        - Backup path (if created)
        - Number of bookmarks moved
        - Number of folders created
        - Any errors encountered

    Example:
        {
          "success": true,
          "backup_created": "/path/to/backup",
          "bookmarks_moved": 342,
          "folders_created": 12,
          "errors": [],
          "duration_seconds": 1.23
        }

    Safety Features:
        - Warns if Edge is running
        - Creates backup before modification
        - Validates file structure
        - Provides rollback capability
    """
    service = _get_service()

    # First analyze
    analysis = service.analyze(use_ai=False)

    # Create plan
    plan = service.create_organization_plan(analysis)

    # Execute plan
    result = service.execute_plan(plan, dry_run=dry_run, backup=backup)

    return result.model_dump_json(indent=2)


@mcp.tool()
def search_bookmarks(query: str, search_in: str = "title,url") -> str:
    """
    Search bookmarks by query string.

    Args:
        query: Search string to find in bookmarks
        search_in: Comma-separated fields to search (title, url, folder)

    Returns:
        JSON string with search results including:
        - Query string
        - Number of results
        - List of matching bookmarks

    Example:
        {
          "query": "python",
          "results_count": 45,
          "results": [
            {
              "name": "Python Documentation",
              "url": "https://docs.python.org",
              "current_folder": "Development/Documentation"
            },
            ...
          ]
        }
    """
    service = _get_service()

    # Parse search_in parameter
    search_fields = [field.strip() for field in search_in.split(',')]

    result = service.search(query, search_fields=search_fields)
    return result.model_dump_json(indent=2)


@mcp.tool()
def get_uncategorized(limit: int = 100) -> str:
    """
    Get list of bookmarks that don't match any category rules.

    Args:
        limit: Maximum number of bookmarks to return (default: 100)

    Returns:
        JSON string with uncategorized bookmarks

    Example:
        [
          {
            "name": "Random Article",
            "url": "https://example.com/article",
            "current_folder": "Other favorites"
          },
          ...
        ]
    """
    service = _get_service()
    bookmarks = service.get_uncategorized(limit=limit)

    # Convert to simple dict format
    result = [
        {
            "name": bm.name,
            "url": str(bm.url),
            "current_folder": bm.current_folder or "Unknown",
            "date_added": bm.date_added.isoformat() if bm.date_added else None,
        }
        for bm in bookmarks
    ]

    import json
    return json.dumps(result, indent=2)


# ============================================================================
# Knowledge Base Tools - Access bookmarks as a queryable knowledge base
# ============================================================================

@mcp.tool()
def get_all_bookmarks() -> str:
    """
    Get ALL bookmarks with full metadata for semantic analysis.

    This tool provides complete access to the user's bookmark collection.
    Use this when the user asks you to find relevant resources, research
    a topic, or reference bookmarks related to their current work.

    Claude can then use its semantic understanding to find relevant bookmarks
    based on the user's context, without needing keyword matching.

    Returns:
        JSON string with array of all bookmarks, each containing:
        - name: Bookmark title
        - url: Full URL
        - current_folder: Current location in bookmark structure
        - suggested_category: Auto-detected category (if matched)
        - date_added: When bookmark was created

    Example Usage:
        User: "I'm working on Docker networking. Check my bookmarks."
        Claude: Calls get_all_bookmarks(), analyzes them semantically,
                returns relevant Docker/networking resources.

    Example Response:
        [
          {
            "name": "Docker Networking Deep Dive",
            "url": "https://docs.docker.com/network/",
            "current_folder": "Other favorites",
            "suggested_category": "Development/Documentation",
            "date_added": "2024-03-15T10:20:00"
          },
          ...
        ]
    """
    service = _get_service()
    bookmarks = service.get_all_bookmarks()

    # Convert to simple dict format for Claude
    result = [
        {
            "name": bm.name,
            "url": str(bm.url),
            "current_folder": bm.current_folder or "Root",
            "suggested_category": bm.suggested_category,
            "date_added": bm.date_added.isoformat() if bm.date_added else None,
        }
        for bm in bookmarks
    ]

    import json
    return json.dumps(result, indent=2)


@mcp.tool()
def get_bookmarks_by_category(category: str) -> str:
    """
    Get bookmarks matching a specific category.

    Use this to narrow down bookmarks to a relevant domain before
    semantic analysis. More efficient than get_all_bookmarks() when
    you know the general topic area.

    Args:
        category: Category name or prefix
                 Examples:
                 - "Development" (matches all Development/* categories)
                 - "Development/GitHub" (exact match)
                 - "Learning" (matches Learning/Tutorials, Learning/Blog-Articles, etc.)
                 - "Media" (matches Media/Video, Media/Music, etc.)

    Available top-level categories:
        - Development (GitHub, Docs, Tools, NPM, PyPI, StackOverflow)
        - Learning (Tutorials, Blog-Articles)
        - Media (Video, Music)
        - Social (Professional, Twitter, Reddit, Facebook)
        - Shopping (Amazon, General)
        - News (Tech-News, General)
        - Productivity (Cloud-Storage, Note-Taking, Project-Management)
        - Design (Design-Tools, Stock-Resources)
        - Reference (Wikipedia, General)

    Returns:
        JSON array of matching bookmarks with metadata

    Example Usage:
        User: "Find resources about Python in my bookmarks"
        Claude: Calls get_bookmarks_by_category("Development"),
                then semantically filters for Python-related content
    """
    service = _get_service()
    bookmarks = service.get_bookmarks_by_category(category)

    result = [
        {
            "name": bm.name,
            "url": str(bm.url),
            "current_folder": bm.current_folder or "Root",
            "suggested_category": bm.suggested_category,
            "confidence": bm.confidence,
            "date_added": bm.date_added.isoformat() if bm.date_added else None,
        }
        for bm in bookmarks
    ]

    return json.dumps({"category": category, "count": len(result), "bookmarks": result}, indent=2)


@mcp.tool()
def get_bookmarks_by_folder(folder_path: str) -> str:
    """
    Get bookmarks from a specific folder in the bookmark structure.

    Use this when you want to access bookmarks from the user's actual
    folder organization (as opposed to auto-detected categories).

    Args:
        folder_path: Folder path or partial name
                    Examples:
                    - "Bookmarks bar" (top-level folder)
                    - "Development" (partial match)
                    - "Other favorites" (Edge's default folder)

    Returns:
        JSON array of bookmarks in that folder

    Example Usage:
        User: "Show me what's in my Development folder"
        Claude: Calls get_bookmarks_by_folder("Development")
    """
    service = _get_service()
    bookmarks = service.get_bookmarks_by_folder(folder_path)

    result = [
        {
            "name": bm.name,
            "url": str(bm.url),
            "current_folder": bm.current_folder,
            "date_added": bm.date_added.isoformat() if bm.date_added else None,
        }
        for bm in bookmarks
    ]

    import json
    return json.dumps({"folder": folder_path, "count": len(result), "bookmarks": result}, indent=2)


if __name__ == "__main__":
    import sys

    # Support both stdio (for Claude Desktop) and SSE (for Claude Web/tunneling)
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if transport == "sse":
        # SSE mode for web-based clients (deprecated, use streamable-http for new projects)
        print(f"Starting MCP server with SSE transport on http://0.0.0.0:9000")
        mcp.run(transport="sse")
    elif transport == "streamable-http" or transport == "http":
        # Streamable HTTP mode (recommended for web-based clients)
        print(f"Starting MCP server with streamable-http transport on http://0.0.0.0:9000/mcp")
        mcp.run(transport="streamable-http")
    else:
        # stdio mode for Claude Desktop
        mcp.run(transport="stdio")

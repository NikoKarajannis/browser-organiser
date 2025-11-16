"""
Utility functions for Browser Organiser MCP.

This module provides helper functions for:
- Locating Edge bookmarks file
- Parsing bookmark JSON files
- Checksum calculation
- Domain extraction
"""

import json
import hashlib
import platform
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlparse

from .models import Bookmark, Folder


def get_edge_bookmarks_path() -> Optional[Path]:
    """
    Automatically detect the Edge bookmarks file path based on the operating system.

    Returns:
        Path to the Edge Bookmarks file, or None if not found
    """
    system = platform.system()

    if system == "Windows":
        # Windows path: %LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Bookmarks
        local_app_data = Path.home() / "AppData" / "Local"
        bookmarks_path = local_app_data / "Microsoft" / "Edge" / "User Data" / "Default" / "Bookmarks"

    elif system == "Linux":
        # Linux path: ~/.config/microsoft-edge/Default/Bookmarks
        bookmarks_path = Path.home() / ".config" / "microsoft-edge" / "Default" / "Bookmarks"

    elif system == "Darwin":  # macOS
        # macOS path: ~/Library/Application Support/Microsoft Edge/Default/Bookmarks
        bookmarks_path = Path.home() / "Library" / "Application Support" / "Microsoft Edge" / "Default" / "Bookmarks"

    else:
        return None

    # Check if file exists
    if bookmarks_path.exists():
        return bookmarks_path

    return None


def calculate_checksum(file_path: Path) -> str:
    """
    Calculate MD5 checksum of a file.

    Args:
        file_path: Path to the file

    Returns:
        MD5 checksum as hex string
    """
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def extract_domain(url: str) -> str:
    """
    Extract domain from a URL.

    Args:
        url: Full URL string

    Returns:
        Domain name (e.g., "github.com")
    """
    parsed = urlparse(url)
    domain = parsed.netloc

    # Remove 'www.' prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]

    return domain


def parse_bookmark_node(node: dict, parent_path: str = "") -> Union[Bookmark, Folder]:
    """
    Parse a single bookmark node from Edge JSON format.

    Args:
        node: Dictionary representing a bookmark or folder
        parent_path: Path of parent folder (for nested structure)

    Returns:
        Either a Bookmark or Folder object
    """
    node_type = node.get("type")

    if node_type == "url":
        # It's a bookmark
        return Bookmark(
            id=node.get("id"),
            name=node.get("name", "Untitled"),
            url=node.get("url"),
            date_added=node.get("date_added"),
            date_last_used=node.get("date_last_used"),
            guid=node.get("guid"),
            current_folder=parent_path,
        )

    elif node_type == "folder":
        # It's a folder - recursively parse children
        folder_name = node.get("name", "Untitled Folder")
        current_path = f"{parent_path}/{folder_name}" if parent_path else folder_name

        children = []
        for child_node in node.get("children", []):
            child = parse_bookmark_node(child_node, current_path)
            children.append(child)

        return Folder(
            id=node.get("id"),
            name=folder_name,
            children=children,
            date_added=node.get("date_added"),
            date_modified=node.get("date_modified"),
            guid=node.get("guid"),
            parent_path=parent_path,
        )

    else:
        raise ValueError(f"Unknown node type: {node_type}")


def load_bookmarks_file(file_path: Path) -> dict:
    """
    Load and parse the Edge bookmarks JSON file.

    Args:
        file_path: Path to the Bookmarks file

    Returns:
        Dictionary with raw bookmark data

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Bookmarks file not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Validate structure
    if 'roots' not in data or 'version' not in data:
        raise ValueError("Invalid bookmarks file structure")

    return data


def parse_bookmarks_file(file_path: Path) -> dict[str, Folder]:
    """
    Parse the entire Edge bookmarks file into Folder objects.

    Args:
        file_path: Path to the Bookmarks file

    Returns:
        Dictionary mapping root folder names to Folder objects
        Example: {"bookmark_bar": Folder(...), "other": Folder(...)}
    """
    data = load_bookmarks_file(file_path)

    roots = {}
    for root_name, root_data in data.get("roots", {}).items():
        if isinstance(root_data, dict) and root_data.get("type") == "folder":
            folder = parse_bookmark_node(root_data, parent_path="")
            roots[root_name] = folder

    return roots


def get_all_bookmarks_flat(roots: dict[str, Folder]) -> list[Bookmark]:
    """
    Get all bookmarks from all root folders as a flat list.

    Args:
        roots: Dictionary of root folders

    Returns:
        Flat list of all bookmarks
    """
    all_bookmarks = []
    for folder in roots.values():
        all_bookmarks.extend(folder.get_all_bookmarks())
    return all_bookmarks


def count_bookmarks_recursive(node: dict) -> int:
    """
    Count bookmarks recursively in raw JSON data.

    Args:
        node: Dictionary node from bookmarks JSON

    Returns:
        Total number of bookmarks
    """
    count = 0

    if isinstance(node, dict):
        if node.get("type") == "url":
            count = 1
        elif node.get("type") == "folder":
            for child in node.get("children", []):
                count += count_bookmarks_recursive(child)

    return count


def save_bookmarks_file(file_path: Path, data: dict) -> None:
    """
    Save bookmarks data back to JSON file.

    Args:
        file_path: Path to save the Bookmarks file
        data: Dictionary with bookmark data
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=3, ensure_ascii=False)


def bookmark_to_dict(bookmark: Bookmark) -> dict:
    """
    Convert a Bookmark object back to Edge JSON format.

    Args:
        bookmark: Bookmark object

    Returns:
        Dictionary in Edge bookmark format
    """
    # Convert datetime to WebKit timestamp
    def datetime_to_webkit(dt):
        if dt is None:
            return "0"
        from datetime import datetime
        WEBKIT_EPOCH = datetime(1601, 1, 1)
        delta = dt - WEBKIT_EPOCH
        microseconds = int(delta.total_seconds() * 1_000_000)
        return str(microseconds)

    return {
        "date_added": datetime_to_webkit(bookmark.date_added),
        "date_last_used": datetime_to_webkit(bookmark.date_last_used) if bookmark.date_last_used else "0",
        "guid": bookmark.guid,
        "id": bookmark.id,
        "name": bookmark.name,
        "type": "url",
        "url": str(bookmark.url),
    }


def folder_to_dict(folder: Folder) -> dict:
    """
    Convert a Folder object back to Edge JSON format.

    Args:
        folder: Folder object

    Returns:
        Dictionary in Edge folder format
    """
    from datetime import datetime

    def datetime_to_webkit(dt):
        if dt is None:
            return "0"
        WEBKIT_EPOCH = datetime(1601, 1, 1)
        delta = dt - WEBKIT_EPOCH
        microseconds = int(delta.total_seconds() * 1_000_000)
        return str(microseconds)

    children = []
    for child in folder.children:
        if isinstance(child, Bookmark):
            children.append(bookmark_to_dict(child))
        elif isinstance(child, Folder):
            children.append(folder_to_dict(child))

    return {
        "children": children,
        "date_added": datetime_to_webkit(folder.date_added),
        "date_modified": datetime_to_webkit(folder.date_modified) if folder.date_modified else "0",
        "guid": folder.guid,
        "id": folder.id,
        "name": folder.name,
        "type": "folder",
    }


def recalculate_bookmarks_checksum(data: dict) -> str:
    """
    Recalculate the checksum for bookmarks data.
    Edge uses MD5 checksum of the roots section.

    Args:
        data: Bookmark data dictionary

    Returns:
        MD5 checksum as hex string
    """
    # Edge calculates checksum from the roots section only
    roots_json = json.dumps(data.get("roots", {}), separators=(',', ':'), sort_keys=True)
    return hashlib.md5(roots_json.encode('utf-8')).hexdigest()


def get_domain_statistics(bookmarks: list[Bookmark]) -> list[dict[str, Union[str, int]]]:
    """
    Get statistics about domains in bookmarks.

    Args:
        bookmarks: List of Bookmark objects

    Returns:
        List of dictionaries with domain and count, sorted by count descending
    """
    domain_counts = {}

    for bookmark in bookmarks:
        domain = extract_domain(str(bookmark.url))
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    # Sort by count descending
    sorted_domains = sorted(
        [{"domain": domain, "count": count} for domain, count in domain_counts.items()],
        key=lambda x: x["count"],
        reverse=True
    )

    return sorted_domains

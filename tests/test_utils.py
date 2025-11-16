#!/usr/bin/env python3
"""
Test script for utility functions.
"""

from datetime import datetime
from src.utils import (
    get_edge_bookmarks_path,
    extract_domain,
    bookmark_to_dict,
    folder_to_dict,
    get_domain_statistics,
)
from src.models import Bookmark, Folder


def test_edge_path_detection():
    """Test automatic Edge bookmarks path detection"""
    print("Testing Edge bookmarks path detection...")
    path = get_edge_bookmarks_path()
    if path:
        print(f"✓ Edge bookmarks path found: {path}")
        print(f"  Exists: {path.exists()}")
    else:
        print("✗ Edge bookmarks path not found (may not have Edge installed)")
    print()


def test_domain_extraction():
    """Test domain extraction from URLs"""
    print("Testing domain extraction...")

    test_cases = [
        ("https://github.com/user/repo", "github.com"),
        ("https://www.google.com/search", "google.com"),
        ("https://docs.python.org/3/library/", "docs.python.org"),
        ("http://stackoverflow.com/questions/123", "stackoverflow.com"),
    ]

    all_passed = True
    for url, expected in test_cases:
        result = extract_domain(url)
        if result == expected:
            print(f"✓ {url} -> {result}")
        else:
            print(f"✗ {url} -> {result} (expected {expected})")
            all_passed = False

    print()
    return all_passed


def test_bookmark_to_dict():
    """Test converting Bookmark to Edge JSON format"""
    print("Testing Bookmark to dict conversion...")

    bookmark = Bookmark(
        id="123",
        name="Test Bookmark",
        url="https://example.com",
        date_added=datetime.now(),
        guid="test-guid",
    )

    result = bookmark_to_dict(bookmark)

    print(f"✓ Bookmark converted to dict:")
    print(f"  name: {result['name']}")
    print(f"  url: {result['url']}")
    print(f"  type: {result['type']}")
    print(f"  date_added: {result['date_added']}")
    print()


def test_folder_to_dict():
    """Test converting Folder to Edge JSON format"""
    print("Testing Folder to dict conversion...")

    bookmark1 = Bookmark(
        id="1",
        name="Bookmark 1",
        url="https://example.com",
        date_added=datetime.now(),
        guid="guid-1",
    )

    bookmark2 = Bookmark(
        id="2",
        name="Bookmark 2",
        url="https://test.com",
        date_added=datetime.now(),
        guid="guid-2",
    )

    folder = Folder(
        id="f1",
        name="Test Folder",
        children=[bookmark1, bookmark2],
        date_added=datetime.now(),
        guid="folder-guid",
    )

    result = folder_to_dict(folder)

    print(f"✓ Folder converted to dict:")
    print(f"  name: {result['name']}")
    print(f"  type: {result['type']}")
    print(f"  children count: {len(result['children'])}")
    print()


def test_domain_statistics():
    """Test domain statistics calculation"""
    print("Testing domain statistics...")

    bookmarks = [
        Bookmark(id="1", name="GitHub 1", url="https://github.com/repo1", date_added=datetime.now(), guid="g1"),
        Bookmark(id="2", name="GitHub 2", url="https://github.com/repo2", date_added=datetime.now(), guid="g2"),
        Bookmark(id="3", name="Python Docs", url="https://docs.python.org", date_added=datetime.now(), guid="g3"),
        Bookmark(id="4", name="GitHub 3", url="https://github.com/repo3", date_added=datetime.now(), guid="g4"),
        Bookmark(id="5", name="Stack Overflow", url="https://stackoverflow.com", date_added=datetime.now(), guid="g5"),
    ]

    stats = get_domain_statistics(bookmarks)

    print(f"✓ Domain statistics calculated:")
    for stat in stats:
        print(f"  {stat['domain']}: {stat['count']}")
    print()


def main():
    print("=" * 60)
    print("Testing Utility Functions for Browser Organiser")
    print("=" * 60)
    print()

    try:
        test_edge_path_detection()
        test_domain_extraction()
        test_bookmark_to_dict()
        test_folder_to_dict()
        test_domain_statistics()

        print("=" * 60)
        print("✓ All utility tests completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

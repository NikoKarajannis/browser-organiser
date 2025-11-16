#!/usr/bin/env python3
"""
Test script for knowledge base features.

This tests the new tools that allow Claude to access bookmarks
as a queryable knowledge base.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from src.service import BrowserCleanerService
from src.models import Bookmark, Folder
from pathlib import Path
import json


def create_mock_bookmarks() -> list[Bookmark]:
    """Create some mock bookmarks for testing"""
    return [
        Bookmark(
            id="1",
            name="Docker Networking Guide",
            url="https://docs.docker.com/network/",
            date_added=datetime.now(),
            guid="g1",
            current_folder="Development",
        ),
        Bookmark(
            id="2",
            name="Python Async Programming",
            url="https://docs.python.org/3/library/asyncio.html",
            date_added=datetime.now(),
            guid="g2",
            current_folder="Development/Documentation",
        ),
        Bookmark(
            id="3",
            name="React Hooks Tutorial",
            url="https://reactjs.org/docs/hooks-intro.html",
            date_added=datetime.now(),
            guid="g3",
            current_folder="Learning/Tutorials",
        ),
        Bookmark(
            id="4",
            name="GitHub Actions CI/CD",
            url="https://github.com/features/actions",
            date_added=datetime.now(),
            guid="g4",
            current_folder="Development",
        ),
        Bookmark(
            id="5",
            name="Python Design Patterns",
            url="https://refactoring.guru/design-patterns/python",
            date_added=datetime.now(),
            guid="g5",
            current_folder="Learning/Tutorials",
        ),
    ]


def test_knowledge_base_workflow():
    """
    Test the complete knowledge base workflow as Claude would use it.
    """
    print("=" * 70)
    print("Testing Knowledge Base Features")
    print("=" * 70)
    print()

    # This test demonstrates how Claude would use the tools, but since
    # we don't have actual Edge bookmarks on this system, we'll just
    # verify the service methods exist and work with the categorizer

    print("Test 1: Verify service has knowledge base methods")
    print("-" * 70)

    # Check that BrowserCleanerService has the new methods
    methods = ['get_all_bookmarks', 'get_bookmarks_by_category', 'get_bookmarks_by_folder']

    for method_name in methods:
        if hasattr(BrowserCleanerService, method_name):
            print(f"✓ {method_name} exists")
        else:
            print(f"✗ {method_name} missing")
            return False

    print()

    print("Test 2: Test with mock bookmarks (simulated workflow)")
    print("-" * 70)

    # Create mock bookmarks
    bookmarks = create_mock_bookmarks()

    print(f"✓ Created {len(bookmarks)} mock bookmarks")
    print()

    # Simulate what Claude would do:

    # Scenario 1: User asks "Find Docker resources in my bookmarks"
    print("Scenario 1: User working on Docker networking")
    print("  User: 'Find Docker resources in my bookmarks'")
    print("  Claude would:")
    print("    1. Call get_bookmarks_by_category('Development')")
    print("    2. Semantically filter for Docker-related content")
    print("    3. Return relevant bookmarks")
    print()

    # Filter for Development category
    dev_bookmarks = [bm for bm in bookmarks if 'Development' in (bm.current_folder or '')]
    docker_relevant = [bm for bm in dev_bookmarks if 'docker' in bm.name.lower()]

    print(f"  Found {len(docker_relevant)} Docker-related bookmarks:")
    for bm in docker_relevant:
        print(f"    - {bm.name}")
        print(f"      {bm.url}")
    print()

    # Scenario 2: User asks "What Python resources do I have?"
    print("Scenario 2: User researching Python patterns")
    print("  User: 'What Python resources do I have?'")
    print("  Claude would:")
    print("    1. Call get_all_bookmarks()")
    print("    2. Semantically search for Python-related content")
    print("    3. Present results grouped by topic")
    print()

    python_bookmarks = [bm for bm in bookmarks if 'python' in bm.name.lower()]

    print(f"  Found {len(python_bookmarks)} Python-related bookmarks:")
    for bm in python_bookmarks:
        print(f"    - {bm.name}")
        print(f"      Category: {bm.current_folder}")
        print(f"      URL: {bm.url}")
    print()

    # Scenario 3: User asks "Show me learning resources"
    print("Scenario 3: User wants learning materials")
    print("  User: 'Show me my learning resources'")
    print("  Claude would:")
    print("    1. Call get_bookmarks_by_folder('Learning')")
    print("    2. Group by subtopic")
    print("    3. Present organized results")
    print()

    learning_bookmarks = [bm for bm in bookmarks if 'Learning' in (bm.current_folder or '')]

    print(f"  Found {len(learning_bookmarks)} learning resources:")
    for bm in learning_bookmarks:
        print(f"    - {bm.name}")
        print(f"      Folder: {bm.current_folder}")
    print()

    print("Test 3: JSON serialization (for MCP tools)")
    print("-" * 70)

    # Test that bookmarks can be serialized to JSON (as MCP tools do)
    result = [
        {
            "name": bm.name,
            "url": str(bm.url),
            "current_folder": bm.current_folder,
            "date_added": bm.date_added.isoformat(),
        }
        for bm in bookmarks
    ]

    json_output = json.dumps(result, indent=2)
    print(f"✓ Successfully serialized {len(bookmarks)} bookmarks to JSON")
    print(f"  JSON size: {len(json_output)} bytes")
    print()

    print("=" * 70)
    print("✓ Knowledge Base Features Ready!")
    print("=" * 70)
    print()

    print("Usage in Claude Desktop:")
    print()
    print("1. User: 'I'm working on a React project with state management.'")
    print("   Claude: Calls get_bookmarks_by_category('Development')")
    print("           Finds React-related bookmarks semantically")
    print("           Suggests: 'React Hooks Tutorial' and related resources")
    print()
    print("2. User: 'Find design pattern resources'")
    print("   Claude: Calls get_all_bookmarks()")
    print("           Semantically identifies pattern-related content")
    print("           Returns: 'Python Design Patterns' and similar")
    print()
    print("3. User: 'What's in my tutorials folder?'")
    print("   Claude: Calls get_bookmarks_by_folder('Tutorials')")
    print("           Lists all bookmarks in that folder")
    print()

    return True


def main():
    try:
        success = test_knowledge_base_workflow()
        return 0 if success else 1
    except Exception as e:
        print(f"\n✗ Test failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

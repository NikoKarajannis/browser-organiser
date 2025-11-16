#!/usr/bin/env python3
"""
Quick test script to verify Pydantic models are working correctly.
"""

from datetime import datetime
from src.models import (
    Bookmark,
    Folder,
    Category,
    CategoryRule,
    CategorizationMethod,
    CategorizationResult,
)


def test_bookmark_creation():
    """Test creating a Bookmark instance"""
    print("Testing Bookmark creation...")
    bookmark = Bookmark(
        id="1",
        name="Python Documentation",
        url="https://docs.python.org/3/",
        date_added=datetime.now(),
        guid="test-guid-123",
        suggested_category="Development/Documentation",
        confidence=0.95,
        categorization_method=CategorizationMethod.RULE,
    )
    print(f"✓ Bookmark created: {bookmark.name}")
    print(f"  URL: {bookmark.url}")
    print(f"  Category: {bookmark.suggested_category}")
    print(f"  Confidence: {bookmark.confidence}")
    print()


def test_folder_creation():
    """Test creating a Folder with nested bookmarks"""
    print("Testing Folder creation...")

    bookmark1 = Bookmark(
        id="1",
        name="GitHub",
        url="https://github.com",
        date_added=datetime.now(),
        guid="guid-1",
    )

    bookmark2 = Bookmark(
        id="2",
        name="Stack Overflow",
        url="https://stackoverflow.com",
        date_added=datetime.now(),
        guid="guid-2",
    )

    folder = Folder(
        id="f1",
        name="Development",
        children=[bookmark1, bookmark2],
        date_added=datetime.now(),
        guid="folder-guid-1",
    )

    print(f"✓ Folder created: {folder.name}")
    print(f"  Bookmark count: {folder.get_bookmark_count()}")
    print(f"  Children: {[child.name for child in folder.children]}")
    print()


def test_category_rule_matching():
    """Test CategoryRule matching logic"""
    print("Testing CategoryRule matching...")

    # Create a rule for GitHub
    rule = CategoryRule(
        domain="github.com",
    )

    # Create bookmarks
    github_bookmark = Bookmark(
        id="1",
        name="My Repo",
        url="https://github.com/user/repo",
        date_added=datetime.now(),
        guid="guid-1",
    )

    other_bookmark = Bookmark(
        id="2",
        name="Google",
        url="https://google.com",
        date_added=datetime.now(),
        guid="guid-2",
    )

    print(f"  Rule matches GitHub bookmark: {rule.matches(github_bookmark)}")
    print(f"  Rule matches other bookmark: {rule.matches(other_bookmark)}")
    print()


def test_category_with_multiple_rules():
    """Test Category with multiple rules"""
    print("Testing Category with multiple rules...")

    category = Category(
        name="Development/GitHub",
        priority=10,
        ai_description="GitHub repositories and code hosting",
        rules=[
            CategoryRule(domain="github.com"),
            CategoryRule(domain="gist.github.com"),
        ]
    )

    print(f"✓ Category created: {category.name}")
    print(f"  Priority: {category.priority}")
    print(f"  Number of rules: {len(category.rules)}")
    print()


def test_categorization_result():
    """Test CategorizationResult"""
    print("Testing CategorizationResult...")

    result = CategorizationResult(
        bookmark_id="123",
        category="Development/Documentation",
        confidence=0.92,
        method=CategorizationMethod.AI,
        reasoning="URL contains /docs/ and title mentions documentation",
    )

    print(f"✓ Result created for bookmark: {result.bookmark_id}")
    print(f"  Category: {result.category}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Method: {result.method.value}")
    print(f"  Reasoning: {result.reasoning}")
    print()


def test_json_serialization():
    """Test JSON serialization/deserialization"""
    print("Testing JSON serialization...")

    bookmark = Bookmark(
        id="1",
        name="Test Bookmark",
        url="https://example.com",
        date_added=datetime.now(),
        guid="guid-1",
    )

    # Serialize to JSON
    json_data = bookmark.model_dump_json(indent=2)
    print("✓ Serialized to JSON:")
    print(json_data)

    # Deserialize from JSON
    bookmark_restored = Bookmark.model_validate_json(json_data)
    print(f"\n✓ Deserialized from JSON: {bookmark_restored.name}")
    print()


def main():
    print("=" * 60)
    print("Testing Pydantic Models for Browser Organiser")
    print("=" * 60)
    print()

    try:
        test_bookmark_creation()
        test_folder_creation()
        test_category_rule_matching()
        test_category_with_multiple_rules()
        test_categorization_result()
        test_json_serialization()

        print("=" * 60)
        print("✓ All tests passed!")
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

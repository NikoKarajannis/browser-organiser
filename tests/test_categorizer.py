#!/usr/bin/env python3
"""
Test script for rule-based categorizer.
"""

from datetime import datetime
from src.categorizers.rule_categorizer import RuleCategorizer
from src.models import Bookmark


def test_load_categories():
    """Test loading categories from YAML"""
    print("Testing category loading...")

    categorizer = RuleCategorizer()
    categories = categorizer.get_categories()

    print(f"✓ Loaded {len(categories)} categories")
    print(f"  Top 5 by priority:")
    for cat in categories[:5]:
        print(f"    - {cat.name} (priority: {cat.priority}, rules: {len(cat.rules)})")
    print()


def test_categorize_bookmarks():
    """Test categorizing various bookmarks"""
    print("Testing bookmark categorization...")

    categorizer = RuleCategorizer()

    test_cases = [
        ("GitHub Repo", "https://github.com/user/repo", "Development/GitHub"),
        ("Stack Overflow", "https://stackoverflow.com/questions/123", "Development/StackOverflow"),
        ("Python Docs", "https://docs.python.org/3/library/", "Development/Documentation"),
        ("YouTube Video", "https://youtube.com/watch?v=123", "Media/Video"),
        ("Twitter", "https://twitter.com/user/status/123", "Social/Twitter"),
        ("Reddit", "https://reddit.com/r/programming", "Social/Reddit"),
        ("NPM Package", "https://www.npmjs.com/package/react", "Development/NPM-Packages"),
        ("Medium Article", "https://medium.com/article", "Learning/Blog-Articles"),
        ("Unknown Site", "https://randomsite.com", None),
    ]

    passed = 0
    failed = 0

    for name, url, expected_category in test_cases:
        bookmark = Bookmark(
            id=str(passed + failed),
            name=name,
            url=url,
            date_added=datetime.now(),
            guid=f"guid-{passed + failed}",
        )

        result = categorizer.categorize(bookmark)

        if expected_category is None:
            # Expect no match
            if result is None:
                print(f"✓ {name} -> No match (as expected)")
                passed += 1
            else:
                print(f"✗ {name} -> {result.category} (expected no match)")
                failed += 1
        else:
            # Expect specific match
            if result and result.category == expected_category:
                print(f"✓ {name} -> {result.category}")
                print(f"    Reasoning: {result.reasoning}")
                passed += 1
            elif result:
                print(f"✗ {name} -> {result.category} (expected {expected_category})")
                failed += 1
            else:
                print(f"✗ {name} -> No match (expected {expected_category})")
                failed += 1

    print()
    print(f"Results: {passed} passed, {failed} failed")
    print()

    return failed == 0


def test_batch_categorization():
    """Test batch categorization"""
    print("Testing batch categorization...")

    categorizer = RuleCategorizer()

    bookmarks = [
        Bookmark(id="1", name="GitHub", url="https://github.com", date_added=datetime.now(), guid="g1"),
        Bookmark(id="2", name="Stack Overflow", url="https://stackoverflow.com", date_added=datetime.now(), guid="g2"),
        Bookmark(id="3", name="YouTube", url="https://youtube.com", date_added=datetime.now(), guid="g3"),
        Bookmark(id="4", name="Unknown", url="https://unknown.com", date_added=datetime.now(), guid="g4"),
    ]

    results = categorizer.categorize_batch(bookmarks)

    print(f"✓ Categorized {len(results)}/{len(bookmarks)} bookmarks")
    for result in results:
        print(f"    - Bookmark {result.bookmark_id}: {result.category}")
    print()


def test_statistics():
    """Test categorizer statistics"""
    print("Testing categorizer statistics...")

    categorizer = RuleCategorizer()
    stats = categorizer.get_statistics()

    print(f"✓ Statistics:")
    print(f"  Total categories: {stats['total_categories']}")
    print(f"  Total rules: {stats['total_rules']}")
    print(f"  Avg rules per category: {stats['total_rules'] / stats['total_categories']:.1f}")
    print()


def main():
    print("=" * 60)
    print("Testing Rule-based Categorizer")
    print("=" * 60)
    print()

    try:
        test_load_categories()
        success = test_categorize_bookmarks()
        test_batch_categorization()
        test_statistics()

        print("=" * 60)
        if success:
            print("✓ All categorizer tests passed!")
        else:
            print("✗ Some categorizer tests failed")
        print("=" * 60)

        return 0 if success else 1

    except Exception as e:
        print(f"\n✗ Test failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

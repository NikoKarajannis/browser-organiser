#!/usr/bin/env python3
"""
Example usage of the Browser Organiser service.

This script demonstrates how to use the BrowserCleanerService directly
(without MCP) for testing or standalone usage.
"""

from src.service import BrowserCleanerService
from pathlib import Path


def main():
    print("=" * 70)
    print("Browser Organiser - Example Usage")
    print("=" * 70)
    print()

    # Initialize service (auto-detects Edge bookmarks path)
    try:
        service = BrowserCleanerService()
        print(f"✓ Service initialized")
        print(f"  Bookmarks path: {service.bookmarks_path}")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize service: {e}")
        print()
        print("Make sure Microsoft Edge is installed and has bookmarks.")
        return 1

    # Step 1: Get overview
    print("Step 1: Getting bookmark overview...")
    print("-" * 70)
    try:
        overview = service.get_overview()
        print(f"✓ Total bookmarks: {overview.total_bookmarks}")
        print(f"  Total folders: {overview.total_folders}")
        print(f"  Uncategorized: {overview.uncategorized_count}")
        print()
        print(f"  Top 5 domains:")
        for domain_stat in overview.top_domains[:5]:
            print(f"    - {domain_stat['domain']}: {domain_stat['count']}")
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

    # Step 2: Analyze bookmarks
    print("Step 2: Analyzing bookmarks...")
    print("-" * 70)
    try:
        analysis = service.analyze(use_ai=False)
        print(f"✓ Analysis complete")
        print(f"  Total analyzed: {analysis.total_analyzed}")
        print(f"  Rule-based matches: {analysis.categorization_results.get('rule_based', 0)}")
        print(f"  Uncategorized: {analysis.categorization_results.get('uncategorized', 0)}")
        print(f"  Suggested moves: {len(analysis.suggested_moves)}")
        print(f"  New folders needed: {len(analysis.new_folders_needed)}")
        print()

        if analysis.new_folders_needed:
            print(f"  Folders to create:")
            for folder in analysis.new_folders_needed[:10]:  # Show first 10
                print(f"    - {folder}")
            if len(analysis.new_folders_needed) > 10:
                print(f"    ... and {len(analysis.new_folders_needed) - 10} more")
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

    # Step 3: Create organization plan
    print("Step 3: Creating organization plan...")
    print("-" * 70)
    try:
        plan = service.create_organization_plan(analysis)
        print(f"✓ Plan created")
        print(f"  Estimated changes: {plan.estimated_changes}")

        if plan.has_warnings:
            print(f"  ⚠️  Safety warnings:")
            for warning in plan.safety_warnings:
                print(f"    - {warning}")
        else:
            print(f"  ✓ No safety warnings")
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

    # Step 4: Preview changes (dry run)
    print("Step 4: Previewing changes (DRY RUN)...")
    print("-" * 70)
    try:
        result = service.execute_plan(plan, dry_run=True, backup=False)
        print(f"✓ Dry run complete")
        print(f"  This is a preview - no changes were made")
        print()
        print(f"  Would move: {len(plan.bookmarks_to_move)} bookmarks")
        print(f"  Would create: {len(plan.new_folders_needed)} folders")
        print()
    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

    # Step 5: Ask if user wants to execute
    print("Step 5: Ready to organize")
    print("-" * 70)
    print()
    print("⚠️  WARNING: The next step will modify your browser bookmarks!")
    print()
    print("To execute organization:")
    print("  1. Close Microsoft Edge")
    print("  2. Run this script with --execute flag")
    print("  3. A backup will be created automatically")
    print()
    print("Example:")
    print("  python example_usage.py --execute")
    print()

    # Check if --execute flag was provided
    import sys
    if "--execute" in sys.argv:
        print("Executing organization...")
        print("-" * 70)
        try:
            result = service.execute_plan(plan, dry_run=False, backup=True)
            print()
            if result.success:
                print(f"✓ Organization successful!")
                print(f"  Backup created: {result.backup_created}")
                print(f"  Bookmarks moved: {result.bookmarks_moved}")
                print(f"  Folders created: {result.folders_created}")
                print(f"  Duration: {result.duration_seconds:.2f}s")
                print()
                print("  Your bookmarks have been organized!")
                print("  Open Microsoft Edge to see the results.")
            else:
                print(f"✗ Organization failed")
                for error in result.errors:
                    print(f"  - {error}")
                if result.rollback_available:
                    print()
                    print(f"  Rollback available from: {result.backup_created}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            return 1
    else:
        print("Run with --execute to organize bookmarks (after closing Edge)")
        print()

    # Step 6: Search example
    print("Step 6: Search example")
    print("-" * 70)
    try:
        search_result = service.search("python", search_fields=["title", "url"])
        print(f"✓ Search for 'python': {search_result.results_count} results")
        if search_result.results_count > 0:
            print(f"  First 3 results:")
            for bookmark in search_result.results[:3]:
                print(f"    - {bookmark.name}")
                print(f"      {bookmark.url}")
        print()
    except Exception as e:
        print(f"✗ Error: {e}")

    print("=" * 70)
    print("Example complete!")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())

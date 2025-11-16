"""
Browser Cleaner Service - Main service layer for bookmark organization.

This module provides the core service that orchestrates bookmark analysis,
categorization, and organization with safety features.
"""

import json
import time
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional
from collections import defaultdict

from .models import (
    Bookmark,
    Folder,
    BookmarkOverview,
    AnalysisResult,
    OrganizationPlan,
    OrganizationResult,
    BookmarkMove,
    SearchResult,
    CategorizationMethod,
)
from .utils import (
    get_edge_bookmarks_path,
    parse_bookmarks_file,
    load_bookmarks_file,
    get_all_bookmarks_flat,
    get_domain_statistics,
    save_bookmarks_file,
    folder_to_dict,
    recalculate_bookmarks_checksum,
)
from .categorizers.rule_categorizer import RuleCategorizer
from .safety import SafetyChecker


class BrowserCleanerService:
    """
    Main service for organizing browser bookmarks.

    Coordinates categorization, analysis, and organization operations
    with comprehensive safety checks and backup functionality.
    """

    def __init__(
        self,
        bookmarks_path: Optional[Path] = None,
        use_proxy: bool = False,  # For compatibility with existing code
    ):
        """
        Initialize the Browser Cleaner Service.

        Args:
            bookmarks_path: Path to Edge bookmarks file. Auto-detected if None.
            use_proxy: Compatibility parameter (not used in this implementation)
        """
        # Auto-detect bookmarks path if not provided
        if bookmarks_path is None:
            bookmarks_path = get_edge_bookmarks_path()
            if bookmarks_path is None:
                raise FileNotFoundError(
                    "Could not auto-detect Edge bookmarks file. "
                    "Please provide the path explicitly."
                )

        self.bookmarks_path = bookmarks_path
        self.categorizer = RuleCategorizer()
        self.safety_checker = SafetyChecker()

        # Validate bookmarks file on initialization
        is_valid, error = self.safety_checker.validate_bookmarks_file(self.bookmarks_path)
        if not is_valid:
            raise ValueError(f"Invalid bookmarks file: {error}")

    def get_overview(self) -> BookmarkOverview:
        """
        Get overview of bookmark structure and statistics.

        Returns:
            BookmarkOverview with statistics and folder structure
        """
        # Parse bookmarks
        roots = parse_bookmarks_file(self.bookmarks_path)
        all_bookmarks = get_all_bookmarks_flat(roots)

        # Count folders recursively
        total_folders = sum(folder.get_folder_count() for folder in roots.values())

        # Build folder structure dict
        folder_structure = {}
        for root_name, root_folder in roots.items():
            folder_structure[root_folder.name] = {
                "count": root_folder.get_bookmark_count(),
                "children": [child.name for child in root_folder.children if isinstance(child, Folder)],
            }

        # Count uncategorized (bookmarks not in organized folders)
        # For now, consider all bookmarks in "Other favorites" as uncategorized
        uncategorized_count = 0
        if "other" in roots:
            uncategorized_count = roots["other"].get_bookmark_count()

        # Get domain statistics
        domain_stats = get_domain_statistics(all_bookmarks)

        return BookmarkOverview(
            total_bookmarks=len(all_bookmarks),
            total_folders=total_folders,
            uncategorized_count=uncategorized_count,
            folder_structure=folder_structure,
            top_domains=domain_stats[:10],  # Top 10 domains
            last_analyzed=datetime.now(),
        )

    def analyze(self, use_ai: bool = False) -> AnalysisResult:
        """
        Analyze all bookmarks and suggest categorization.

        Args:
            use_ai: If True, use AI categorizer (not yet implemented)

        Returns:
            AnalysisResult with analysis details and suggestions
        """
        start_time = time.time()

        # Parse bookmarks
        roots = parse_bookmarks_file(self.bookmarks_path)
        all_bookmarks = get_all_bookmarks_flat(roots)

        # Categorize bookmarks
        categorization_counts = {
            "rule_based": 0,
            "ai_based": 0,
            "uncategorized": 0,
        }

        suggested_moves = []
        new_folders_needed = set()

        for bookmark in all_bookmarks:
            # Try rule-based categorization
            result = self.categorizer.categorize(bookmark)

            if result:
                categorization_counts["rule_based"] += 1

                # Only suggest move if different from current folder
                suggested_folder = result.category
                current_folder = bookmark.current_folder or "Other favorites"

                if suggested_folder != current_folder:
                    move = BookmarkMove(
                        bookmark=bookmark,
                        from_folder=current_folder,
                        to_folder=suggested_folder,
                        confidence=result.confidence,
                        method=result.method,
                    )
                    suggested_moves.append(move)
                    new_folders_needed.add(suggested_folder)
            else:
                categorization_counts["uncategorized"] += 1

        # TODO: Add AI categorization when implemented
        if use_ai:
            pass  # AI categorization not yet implemented

        elapsed_time = time.time() - start_time

        return AnalysisResult(
            analysis_complete=True,
            total_analyzed=len(all_bookmarks),
            categorization_results=categorization_counts,
            suggested_moves=suggested_moves,
            new_folders_needed=sorted(new_folders_needed),
            estimated_time_seconds=elapsed_time,
        )

    def create_organization_plan(self, analysis: AnalysisResult) -> OrganizationPlan:
        """
        Create a detailed organization plan from analysis results.

        Args:
            analysis: AnalysisResult from analyze()

        Returns:
            OrganizationPlan with all planned changes and warnings
        """
        # Get safety warnings
        warnings = self.safety_checker.get_safety_warnings(self.bookmarks_path)

        return OrganizationPlan(
            total_bookmarks=analysis.total_analyzed,
            bookmarks_to_move=analysis.suggested_moves,
            new_folders_needed=analysis.new_folders_needed,
            estimated_changes=len(analysis.suggested_moves),
            safety_warnings=warnings,
        )

    def execute_plan(
        self,
        plan: OrganizationPlan,
        dry_run: bool = False,
        backup: bool = True,
    ) -> OrganizationResult:
        """
        Execute the organization plan.

        Args:
            plan: OrganizationPlan to execute
            dry_run: If True, don't actually modify files
            backup: If True, create backup before modifying

        Returns:
            OrganizationResult with execution details
        """
        start_time = time.time()
        errors = []
        backup_path = None

        if dry_run:
            # Dry run - just return preview
            return OrganizationResult(
                success=True,
                backup_created=None,
                bookmarks_moved=0,
                folders_created=0,
                errors=["DRY RUN - No changes made"],
                duration_seconds=time.time() - start_time,
                rollback_available=False,
            )

        try:
            # Create backup if requested
            if backup:
                backup_metadata = self.safety_checker.create_backup(self.bookmarks_path)
                backup_path = backup_metadata.backup_path

            # Load raw bookmark data
            data = load_bookmarks_file(self.bookmarks_path)

            # Create folder structure
            folders_created = self._create_folder_structure(data, plan.new_folders_needed)

            # Move bookmarks
            bookmarks_moved = self._move_bookmarks(data, plan.bookmarks_to_move)

            # Recalculate checksum
            data['checksum'] = recalculate_bookmarks_checksum(data)

            # Save modified data
            save_bookmarks_file(self.bookmarks_path, data)

            elapsed_time = time.time() - start_time

            return OrganizationResult(
                success=True,
                backup_created=backup_path,
                bookmarks_moved=bookmarks_moved,
                folders_created=folders_created,
                errors=errors,
                duration_seconds=elapsed_time,
                rollback_available=backup_path is not None,
            )

        except Exception as e:
            errors.append(f"Execution failed: {str(e)}")

            return OrganizationResult(
                success=False,
                backup_created=backup_path,
                bookmarks_moved=0,
                folders_created=0,
                errors=errors,
                duration_seconds=time.time() - start_time,
                rollback_available=backup_path is not None,
            )

    def search(self, query: str, search_fields: list[str] = ["title", "url"]) -> SearchResult:
        """
        Search bookmarks by query.

        Args:
            query: Search string
            search_fields: Fields to search in (title, url, folder)

        Returns:
            SearchResult with matching bookmarks
        """
        roots = parse_bookmarks_file(self.bookmarks_path)
        all_bookmarks = get_all_bookmarks_flat(roots)

        query_lower = query.lower()
        results = []

        for bookmark in all_bookmarks:
            match = False

            if "title" in search_fields and query_lower in bookmark.name.lower():
                match = True
            if "url" in search_fields and query_lower in str(bookmark.url).lower():
                match = True
            if "folder" in search_fields and bookmark.current_folder:
                if query_lower in bookmark.current_folder.lower():
                    match = True

            if match:
                results.append(bookmark)

        return SearchResult(
            query=query,
            results_count=len(results),
            results=results,
            search_fields=search_fields,
        )

    def get_uncategorized(self, limit: int = 100) -> list[Bookmark]:
        """
        Get list of uncategorized bookmarks.

        Args:
            limit: Maximum number of bookmarks to return

        Returns:
            List of uncategorized bookmarks
        """
        roots = parse_bookmarks_file(self.bookmarks_path)
        all_bookmarks = get_all_bookmarks_flat(roots)

        # Try to categorize each bookmark
        uncategorized = []
        for bookmark in all_bookmarks:
            result = self.categorizer.categorize(bookmark)
            if result is None:
                uncategorized.append(bookmark)
                if len(uncategorized) >= limit:
                    break

        return uncategorized

    # Knowledge Base Methods - for Claude to access bookmark data

    def get_all_bookmarks(self) -> list[Bookmark]:
        """
        Get all bookmarks with full metadata.

        This provides complete access to all bookmarks for Claude to analyze
        and find relevant resources based on the user's current context.

        Returns:
            List of all Bookmark objects with title, URL, folder, and dates
        """
        roots = parse_bookmarks_file(self.bookmarks_path)
        all_bookmarks = get_all_bookmarks_flat(roots)

        # Optionally categorize them for additional context
        for bookmark in all_bookmarks:
            result = self.categorizer.categorize(bookmark)
            if result:
                bookmark.suggested_category = result.category
                bookmark.confidence = result.confidence
                bookmark.categorization_method = result.method

        return all_bookmarks

    def get_bookmarks_by_category(self, category: str) -> list[Bookmark]:
        """
        Get all bookmarks matching a specific category.

        Args:
            category: Category name (e.g., "Development/GitHub", "Development")
                     If no slash, matches all categories starting with that prefix

        Returns:
            List of Bookmark objects in that category
        """
        roots = parse_bookmarks_file(self.bookmarks_path)
        all_bookmarks = get_all_bookmarks_flat(roots)

        matching_bookmarks = []

        for bookmark in all_bookmarks:
            # First check if already in a folder matching the category
            if bookmark.current_folder:
                if category in bookmark.current_folder:
                    matching_bookmarks.append(bookmark)
                    continue

            # Otherwise categorize and check
            result = self.categorizer.categorize(bookmark)
            if result:
                # Handle both exact match and prefix match
                if '/' in category:
                    # Exact match (e.g., "Development/GitHub")
                    if result.category == category:
                        bookmark.suggested_category = result.category
                        bookmark.confidence = result.confidence
                        bookmark.categorization_method = result.method
                        matching_bookmarks.append(bookmark)
                else:
                    # Prefix match (e.g., "Development" matches "Development/*")
                    if result.category.startswith(category):
                        bookmark.suggested_category = result.category
                        bookmark.confidence = result.confidence
                        bookmark.categorization_method = result.method
                        matching_bookmarks.append(bookmark)

        return matching_bookmarks

    def get_bookmarks_by_folder(self, folder_path: str) -> list[Bookmark]:
        """
        Get bookmarks from a specific folder in the bookmark structure.

        Args:
            folder_path: Folder path (e.g., "Bookmarks bar/Development")
                        or partial match (e.g., "Development")

        Returns:
            List of Bookmark objects in that folder
        """
        roots = parse_bookmarks_file(self.bookmarks_path)
        all_bookmarks = get_all_bookmarks_flat(roots)

        matching_bookmarks = []

        for bookmark in all_bookmarks:
            if bookmark.current_folder:
                # Support both exact match and partial match
                if folder_path.lower() in bookmark.current_folder.lower():
                    matching_bookmarks.append(bookmark)

        return matching_bookmarks

    def _create_folder_structure(self, data: dict, folder_paths: list[str]) -> int:
        """
        Create folder structure in bookmarks data.

        Args:
            data: Raw bookmark data dictionary
            folder_paths: List of folder paths to create (e.g., ["Development/GitHub"])

        Returns:
            Number of folders created
        """
        created_count = 0

        # Organize folders by hierarchy
        for folder_path in folder_paths:
            parts = folder_path.split('/')
            current_root = data['roots'].get('bookmark_bar')

            if not current_root:
                continue

            # Navigate/create folder hierarchy
            current_container = current_root
            current_path = ""

            for part in parts:
                current_path = f"{current_path}/{part}" if current_path else part

                # Check if folder exists
                existing_folder = None
                for child in current_container.get('children', []):
                    if child.get('type') == 'folder' and child.get('name') == part:
                        existing_folder = child
                        break

                if existing_folder:
                    current_container = existing_folder
                else:
                    # Create new folder
                    new_folder = {
                        'children': [],
                        'date_added': str(int(datetime.now().timestamp() * 1_000_000)),
                        'date_modified': str(int(datetime.now().timestamp() * 1_000_000)),
                        'guid': str(uuid.uuid4()),
                        'id': str(self._get_next_id(data)),
                        'name': part,
                        'type': 'folder',
                    }

                    if 'children' not in current_container:
                        current_container['children'] = []

                    current_container['children'].append(new_folder)
                    current_container = new_folder
                    created_count += 1

        return created_count

    def _move_bookmarks(self, data: dict, moves: list[BookmarkMove]) -> int:
        """
        Move bookmarks according to the plan.

        Args:
            data: Raw bookmark data dictionary
            moves: List of BookmarkMove objects

        Returns:
            Number of bookmarks actually moved
        """
        moved_count = 0

        # Build a map of bookmark IDs to moves
        move_map = {move.bookmark.id: move for move in moves}

        # Find and move bookmarks
        for root_name, root_data in data['roots'].items():
            moved_count += self._move_bookmarks_recursive(root_data, move_map, data)

        return moved_count

    def _move_bookmarks_recursive(
        self,
        container: dict,
        move_map: dict,
        root_data: dict,
    ) -> int:
        """
        Recursively find and move bookmarks.

        Args:
            container: Current container (folder)
            move_map: Map of bookmark IDs to moves
            root_data: Root bookmark data

        Returns:
            Number of bookmarks moved
        """
        moved_count = 0
        children = container.get('children', [])
        remaining_children = []

        for child in children:
            if child.get('type') == 'url' and child.get('id') in move_map:
                # This bookmark should be moved
                move = move_map[child['id']]

                # Find target folder
                target_folder = self._find_or_create_folder(
                    root_data,
                    move.to_folder
                )

                if target_folder:
                    # Add to target folder
                    if 'children' not in target_folder:
                        target_folder['children'] = []
                    target_folder['children'].append(child)
                    moved_count += 1
                else:
                    # Couldn't find target, keep in place
                    remaining_children.append(child)

            elif child.get('type') == 'folder':
                # Recursively process folder
                moved_count += self._move_bookmarks_recursive(child, move_map, root_data)
                remaining_children.append(child)
            else:
                # Keep other bookmarks
                remaining_children.append(child)

        container['children'] = remaining_children
        return moved_count

    def _find_or_create_folder(self, root_data: dict, folder_path: str) -> Optional[dict]:
        """
        Find or create a folder by path.

        Args:
            root_data: Root bookmark data
            folder_path: Path like "Development/GitHub"

        Returns:
            Folder dictionary or None if not found
        """
        parts = folder_path.split('/')
        current = root_data['roots'].get('bookmark_bar')

        if not current:
            return None

        for part in parts:
            # Find child folder
            found = None
            for child in current.get('children', []):
                if child.get('type') == 'folder' and child.get('name') == part:
                    found = child
                    break

            if found:
                current = found
            else:
                return None

        return current

    def _get_next_id(self, data: dict) -> int:
        """
        Get next available ID for new folders/bookmarks.

        Args:
            data: Bookmark data dictionary

        Returns:
            Next available ID
        """
        max_id = 0

        def find_max_id(node):
            nonlocal max_id
            if isinstance(node, dict):
                if 'id' in node:
                    try:
                        node_id = int(node['id'])
                        max_id = max(max_id, node_id)
                    except ValueError:
                        pass

                for value in node.values():
                    if isinstance(value, (dict, list)):
                        find_max_id(value)
            elif isinstance(node, list):
                for item in node:
                    find_max_id(item)

        find_max_id(data)
        return max_id + 1

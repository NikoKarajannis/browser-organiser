"""
Rule-based categorizer for bookmarks.

This module provides fast, deterministic categorization based on
predefined rules from the categories.yaml configuration file.
"""

import yaml
from pathlib import Path
from typing import Optional

from ..models import (
    Bookmark,
    Category,
    CategoryRule,
    CategorizationResult,
    CategorizationMethod,
)


class RuleCategorizer:
    """
    Rule-based bookmark categorizer.

    Uses predefined rules from YAML configuration to categorize bookmarks
    based on domain patterns, URL patterns, and keywords.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the rule categorizer.

        Args:
            config_path: Path to categories.yaml file.
                        If None, uses default config/categories.yaml
        """
        if config_path is None:
            # Default to config/categories.yaml relative to project root
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            config_path = project_root / "config" / "categories.yaml"

        self.config_path = config_path
        self.categories = self._load_categories()

    def _load_categories(self) -> list[Category]:
        """
        Load categories from YAML configuration file.

        Returns:
            List of Category objects sorted by priority (highest first)

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Categories config not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        categories = []
        for cat_data in data.get('categories', []):
            # Parse rules
            rules = []
            for rule_data in cat_data.get('rules', []):
                rule = CategoryRule(**rule_data)
                rules.append(rule)

            # Create category
            category = Category(
                name=cat_data['name'],
                rules=rules,
                ai_description=cat_data.get('ai_description', ''),
                priority=cat_data.get('priority', 0),
            )
            categories.append(category)

        # Sort by priority (highest first)
        categories.sort(key=lambda c: c.priority, reverse=True)

        return categories

    def categorize(self, bookmark: Bookmark) -> Optional[CategorizationResult]:
        """
        Categorize a bookmark using rule-based matching.

        Args:
            bookmark: Bookmark to categorize

        Returns:
            CategorizationResult if a match is found, None otherwise
        """
        for category in self.categories:
            for rule in category.rules:
                if rule.matches(bookmark):
                    return CategorizationResult(
                        bookmark_id=bookmark.id,
                        category=category.name,
                        confidence=1.0,  # Rule-based matches are 100% confident
                        method=CategorizationMethod.RULE,
                        reasoning=f"Matched rule: {self._explain_rule(rule)}",
                    )

        return None

    def categorize_batch(self, bookmarks: list[Bookmark]) -> list[CategorizationResult]:
        """
        Categorize multiple bookmarks in batch.

        Args:
            bookmarks: List of bookmarks to categorize

        Returns:
            List of CategorizationResult objects (may be shorter than input
            if some bookmarks don't match any rules)
        """
        results = []
        for bookmark in bookmarks:
            result = self.categorize(bookmark)
            if result:
                results.append(result)

        return results

    def get_categories(self) -> list[Category]:
        """
        Get all loaded categories.

        Returns:
            List of Category objects
        """
        return self.categories

    def get_category_names(self) -> list[str]:
        """
        Get names of all categories.

        Returns:
            List of category names
        """
        return [cat.name for cat in self.categories]

    def reload_config(self) -> None:
        """
        Reload categories from configuration file.

        Useful if the config file has been modified.
        """
        self.categories = self._load_categories()

    def _explain_rule(self, rule: CategoryRule) -> str:
        """
        Generate human-readable explanation of a rule.

        Args:
            rule: CategoryRule to explain

        Returns:
            String explanation
        """
        parts = []

        if rule.domain:
            parts.append(f"domain={rule.domain}")
        if rule.domain_pattern:
            parts.append(f"domain_pattern={rule.domain_pattern}")
        if rule.url_contains:
            parts.append(f"url_contains={rule.url_contains}")
        if rule.keywords:
            parts.append(f"keywords={rule.keywords}")

        return ", ".join(parts) if parts else "no specific rule"

    def get_statistics(self) -> dict:
        """
        Get statistics about loaded categories and rules.

        Returns:
            Dictionary with statistics
        """
        total_rules = sum(len(cat.rules) for cat in self.categories)

        return {
            "total_categories": len(self.categories),
            "total_rules": total_rules,
            "categories_by_priority": [
                {
                    "name": cat.name,
                    "priority": cat.priority,
                    "rules_count": len(cat.rules)
                }
                for cat in self.categories
            ]
        }

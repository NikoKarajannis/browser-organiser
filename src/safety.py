"""
Safety checker and backup system for Browser Organiser.

This module provides safety checks and backup functionality to ensure
bookmark modifications are safe and reversible.
"""

import json
import shutil
import hashlib
import psutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

from .models import BackupMetadata
from .utils import count_bookmarks_recursive


class SafetyChecker:
    """
    Safety checker for bookmark operations.

    Provides pre-flight checks, backup creation, and rollback functionality
    to ensure bookmark modifications are safe.
    """

    @staticmethod
    def is_edge_running() -> bool:
        """
        Check if Microsoft Edge is currently running.

        Returns:
            True if Edge process is detected, False otherwise
        """
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower() if proc.info['name'] else ''
                if 'msedge' in proc_name or 'microsoft edge' in proc_name:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        return False

    @staticmethod
    def validate_bookmarks_file(path: Path) -> Tuple[bool, Optional[str]]:
        """
        Validate bookmark file integrity and structure.

        Args:
            path: Path to the Bookmarks file

        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is None
        """
        if not path.exists():
            return False, f"File not found: {path}"

        if not path.is_file():
            return False, f"Not a file: {path}"

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check expected structure
            if 'roots' not in data:
                return False, "Missing 'roots' key in bookmark file"

            if 'version' not in data:
                return False, "Missing 'version' key in bookmark file"

            # Check that roots is a dictionary
            if not isinstance(data['roots'], dict):
                return False, "'roots' should be a dictionary"

            # Check for common root folders
            expected_roots = ['bookmark_bar', 'other', 'synced']
            found_roots = [r for r in expected_roots if r in data['roots']]

            if not found_roots:
                return False, f"No standard root folders found. Expected one of: {expected_roots}"

            return True, None

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"

    @staticmethod
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
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    @staticmethod
    def create_backup(bookmarks_path: Path, backup_dir: Optional[Path] = None) -> BackupMetadata:
        """
        Create timestamped backup of bookmarks file.

        Args:
            bookmarks_path: Path to the Bookmarks file
            backup_dir: Optional directory for backups. If None, uses parent directory

        Returns:
            BackupMetadata with backup information

        Raises:
            FileNotFoundError: If bookmarks_path doesn't exist
        """
        if not bookmarks_path.exists():
            raise FileNotFoundError(f"Bookmarks file not found: {bookmarks_path}")

        # Determine backup directory
        if backup_dir is None:
            backup_dir = bookmarks_path.parent / "backups"

        # Create backup directory if it doesn't exist
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"Bookmarks.backup.{timestamp}"
        backup_path = backup_dir / backup_filename

        # Calculate checksum before backup
        checksum = SafetyChecker.calculate_checksum(bookmarks_path)

        # Copy file
        shutil.copy2(bookmarks_path, backup_path)

        # Count bookmarks
        with open(bookmarks_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        bookmark_count = 0
        for root_data in data.get('roots', {}).values():
            bookmark_count += count_bookmarks_recursive(root_data)

        return BackupMetadata(
            original_path=str(bookmarks_path),
            backup_path=str(backup_path),
            checksum_before=checksum,
            bookmark_count=bookmark_count,
        )

    @staticmethod
    def rollback(metadata: BackupMetadata) -> bool:
        """
        Restore bookmarks from backup.

        Args:
            metadata: BackupMetadata with backup information

        Returns:
            True if rollback successful, False otherwise
        """
        if not metadata.is_valid():
            return False

        try:
            # Copy backup back to original location
            shutil.copy2(metadata.backup_path, metadata.original_path)

            # Verify restoration
            restored_checksum = SafetyChecker.calculate_checksum(Path(metadata.original_path))

            if restored_checksum == metadata.checksum_before:
                return True
            else:
                # Checksum mismatch - something went wrong
                return False

        except Exception:
            return False

    @staticmethod
    def cleanup_old_backups(backup_dir: Path, keep_count: int = 10) -> int:
        """
        Remove old backup files, keeping only the most recent ones.

        Args:
            backup_dir: Directory containing backup files
            keep_count: Number of most recent backups to keep

        Returns:
            Number of backups deleted
        """
        if not backup_dir.exists():
            return 0

        # Find all backup files
        backup_files = sorted(
            backup_dir.glob("Bookmarks.backup.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True  # Most recent first
        )

        # Delete old backups
        deleted = 0
        for backup_file in backup_files[keep_count:]:
            try:
                backup_file.unlink()
                deleted += 1
            except Exception:
                pass

        return deleted

    @staticmethod
    def get_safety_warnings(bookmarks_path: Path) -> list[str]:
        """
        Get list of safety warnings before modifying bookmarks.

        Args:
            bookmarks_path: Path to the Bookmarks file

        Returns:
            List of warning messages (empty if all safe)
        """
        warnings = []

        # Check if Edge is running
        if SafetyChecker.is_edge_running():
            warnings.append(
                "Microsoft Edge is currently running. "
                "The bookmarks file may be locked. "
                "Consider closing Edge before modifying bookmarks."
            )

        # Check file permissions
        if not bookmarks_path.exists():
            warnings.append(f"Bookmarks file not found: {bookmarks_path}")
        elif not bookmarks_path.is_file():
            warnings.append(f"Path is not a file: {bookmarks_path}")
        elif not os.access(bookmarks_path, os.W_OK):
            warnings.append(
                f"No write permission for bookmarks file: {bookmarks_path}"
            )

        # Validate file structure
        is_valid, error = SafetyChecker.validate_bookmarks_file(bookmarks_path)
        if not is_valid:
            warnings.append(f"Invalid bookmarks file: {error}")

        return warnings


# Import os for file permission check
import os

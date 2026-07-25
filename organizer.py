"""
Smart File Organizer - Core Organization Engine Module
Provides multi-threaded directory scanning, category and rule sorting, duplicate handling, and progress tracking.
"""

import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Callable
from settings import SettingsManager
from duplicate_detector import DuplicateDetector
from undo_manager import UndoManager
from logger import logger


class FileOrganizerEngine:
    """Core file organization engine supporting multi-threaded execution and custom rules."""

    def __init__(self, settings_mgr: Optional[SettingsManager] = None, undo_mgr: Optional[UndoManager] = None):
        self.settings_mgr = settings_mgr or SettingsManager()
        self.undo_mgr = undo_mgr or UndoManager()
        self.cancel_requested = False

    def scan_directory(self, target_folder: str, recursive: bool = False) -> List[str]:
        """
        Scans target directory using fast os.scandir generator.
        
        Args:
            target_folder: Absolute directory path.
            recursive: If True, scans subdirectories recursively.
            
        Returns:
            List of absolute file paths to organize.
        """
        file_paths: List[str] = []
        if not os.path.exists(target_folder) or not os.path.isdir(target_folder):
            logger.error(f"Scan target folder invalid: {target_folder}")
            return file_paths

        # System / reserved folder names to skip
        skip_dirs = {"_Duplicates", ".organizer_undo", ".git", ".idea", "__pycache__", "node_modules", "logs"}

        try:
            if recursive:
                for root, dirs, files in os.walk(target_folder):
                    # Exclude skipped directory names in place
                    dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
                    for f in files:
                        if not f.startswith("~$") and f != "app.log" and f != "settings.json":
                            file_paths.append(os.path.join(root, f))
            else:
                with os.scandir(target_folder) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False):
                            filename = entry.name
                            if not filename.startswith("~$") and filename != "app.log" and filename != "settings.json":
                                file_paths.append(entry.path)
        except Exception as e:
            logger.error(f"Error scanning directory {target_folder}: {e}")

        logger.info(f"Directory scan completed for '{target_folder}'. Found {len(file_paths)} files.")
        return file_paths

    def match_custom_rules(self, file_path: str, filename: str, file_size: int) -> Optional[str]:
        """
        Evaluates user-defined custom rules (e.g. pattern match, size threshold).
        
        Returns:
            Target category/subfolder path string if matched, else None.
        """
        rules = self.settings_mgr.get("custom_rules", [])
        for rule in rules:
            field = rule.get("field")
            pattern = rule.get("pattern", "").strip()
            target_folder = rule.get("target_folder", "").strip()

            if not target_folder:
                continue

            if field == "name_contains" and pattern.lower() in filename.lower():
                return target_folder
            elif field == "name_regex":
                try:
                    if re.search(pattern, filename, re.IGNORECASE):
                        return target_folder
                except Exception:
                    pass
            elif field == "size_greater_mb":
                try:
                    threshold_bytes = float(pattern) * 1024 * 1024
                    if file_size > threshold_bytes:
                        return target_folder
                except Exception:
                    pass
            elif field == "extension" and filename.lower().endswith(pattern.lower() if pattern.startswith(".") else f".{pattern.lower()}"):
                return target_folder

        return None

    def determine_file_category(self, file_path: str) -> str:
        """Determines target category folder name based on custom rules and extension mapping."""
        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        try:
            size = os.path.getsize(file_path)
        except Exception:
            size = 0

        # Check custom rules first
        custom_target = self.match_custom_rules(file_path, filename, size)
        if custom_target:
            return custom_target

        # Fallback to extension mapping
        return self.settings_mgr.get_extension_category(ext)

    def organize_directory(
        self,
        target_folder: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for multi-threaded file organization.
        
        Args:
            target_folder: Path of folder to organize.
            progress_callback: Callback function receiving live status metrics dict.
            
        Returns:
            Dict containing summary statistics and activity log.
        """
        self.cancel_requested = False
        start_time = time.time()
        batch_id = f"batch_{uuid.uuid4().hex[:8]}"

        recursive = self.settings_mgr.get("recursive_scan", False)
        dup_mode = self.settings_mgr.get("duplicate_handling", "move")
        clean_empty = self.settings_mgr.get("clean_empty_folders", True)

        # Step 1: Scan Directory
        if progress_callback:
            progress_callback({"status_text": "Scanning files in target directory..."})

        all_files = self.scan_directory(target_folder, recursive=recursive)
        total_files = len(all_files)

        if total_files == 0:
            logger.info("No files to organize in target folder.")
            return {
                "batch_id": batch_id,
                "target_folder": target_folder,
                "total_files": 0,
                "moved_files": 0,
                "duplicate_files": 0,
                "folders_created": 0,
                "total_size_bytes": 0,
                "time_taken": 0.0,
                "activity": []
            }

        # Step 2: Duplicate Detection
        if progress_callback:
            progress_callback({"status_text": "Scanning for duplicate files (SHA-256)..."})

        dup_detector = DuplicateDetector(mode=dup_mode)
        confirmed_dup_groups, files_to_organize = dup_detector.find_duplicates(
            all_files,
            progress_callback=lambda idx, tot, msg: progress_callback({"status_text": msg}) if progress_callback else None
        )

        moved_count = 0
        duplicate_count = 0
        total_size_processed = 0
        created_folders: Set[str] = set()
        file_moves_record: List[Dict[str, Any]] = []
        activity_log: List[Dict[str, Any]] = []

        # Step 3: Action Duplicates
        for f_hash, dup_paths in confirmed_dup_groups.items():
            original_file = dup_paths[0]
            for dup_path in dup_paths[1:]:
                if self.cancel_requested:
                    break
                dup_result = dup_detector.handle_duplicate_file(
                    duplicate_path=dup_path,
                    original_path=original_file,
                    target_folder=target_folder,
                    mode=dup_mode
                )
                duplicate_count += 1
                if dup_result.get("success") and dup_result.get("dest_path"):
                    dest_dir = os.path.dirname(dup_result["dest_path"])
                    created_folders.add(dest_dir)
                    file_moves_record.append({
                        "src_path": dup_path,
                        "dest_path": dup_result["dest_path"],
                        "filename": dup_result["filename"]
                    })
                activity_log.append({
                    "filename": os.path.basename(dup_path),
                    "category": "_Duplicates",
                    "src_path": dup_path,
                    "dest_path": dup_result.get("dest_path", ""),
                    "size": os.path.getsize(dup_path) if os.path.exists(dup_path) else 0,
                    "status": f"Duplicate ({dup_mode})",
                    "timestamp": time.strftime("%H:%M:%S")
                })

        # Step 4: Organize Non-Duplicate Files
        processed_count = 0
        files_count = len(files_to_organize)

        for idx, src_path in enumerate(files_to_organize, start=1):
            if self.cancel_requested:
                logger.info("Organization process cancelled by user.")
                break

            filename = os.path.basename(src_path)
            try:
                file_size = os.path.getsize(src_path)
            except Exception:
                file_size = 0

            category = self.determine_file_category(src_path)
            category_dir = os.path.join(target_folder, category)

            # Skip moving if file is already in the correct category folder
            current_parent = os.path.normpath(os.path.dirname(src_path))
            target_parent = os.path.normpath(category_dir)
            if current_parent == target_parent:
                processed_count += 1
                continue

            os.makedirs(category_dir, exist_ok=True)
            created_folders.add(category_dir)

            dest_path = os.path.join(category_dir, filename)

            # Handle existing filename collision in target category
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(category_dir, f"{base}_{counter}{ext}")
                    counter += 1

            status_msg = "Moved"
            try:
                shutil.move(src_path, dest_path)
                moved_count += 1
                total_size_processed += file_size
                file_moves_record.append({
                    "src_path": src_path,
                    "dest_path": dest_path,
                    "filename": filename
                })
            except PermissionError:
                status_msg = "Permission Error"
                logger.error(f"Permission denied when moving {src_path}")
            except Exception as e:
                status_msg = f"Error: {e}"
                logger.error(f"Failed to move {src_path}: {e}")

            processed_count += 1
            now = time.time()
            elapsed = now - start_time
            rate = processed_count / elapsed if elapsed > 0 else 1.0
            remaining_files = files_count - processed_count
            eta_seconds = remaining_files / rate if rate > 0 else 0.0

            activity_log.append({
                "filename": filename,
                "category": category,
                "src_path": src_path,
                "dest_path": dest_path if status_msg == "Moved" else "",
                "size": file_size,
                "status": status_msg,
                "timestamp": time.strftime("%H:%M:%S")
            })

            if progress_callback:
                progress_callback({
                    "processed": processed_count,
                    "total": files_count,
                    "percentage": (processed_count / files_count) * 100.0 if files_count else 100.0,
                    "current_file": filename,
                    "elapsed_seconds": elapsed,
                    "remaining_seconds": eta_seconds,
                    "moved_count": moved_count,
                    "duplicate_count": duplicate_count,
                    "status_text": f"Organizing: {filename}"
                })

        # Step 5: Clean Empty Folders if enabled
        if clean_empty and not self.cancel_requested:
            self.clean_empty_folders(target_folder)

        # Step 6: Record Undo Transaction Batch
        if file_moves_record:
            self.undo_mgr.record_batch(
                batch_id=batch_id,
                target_folder=target_folder,
                moves=file_moves_record,
                created_folders=list(created_folders)
            )

        elapsed_total = time.time() - start_time
        summary = {
            "batch_id": batch_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_folder": target_folder,
            "total_files": total_files,
            "moved_files": moved_count,
            "duplicate_files": duplicate_count,
            "folders_created": len(created_folders),
            "total_size_bytes": total_size_processed,
            "time_taken": elapsed_total,
            "activity": activity_log
        }
        logger.info(f"Organization completed: {moved_count} moved, {duplicate_count} duplicates in {elapsed_total:.2f}s.")
        return summary

    def clean_empty_folders(self, target_folder: str) -> int:
        """Recursively removes empty directories in target folder."""
        removed_count = 0
        skip_dirs = {"_Duplicates", ".organizer_undo"}
        for root, dirs, files in os.walk(target_folder, topdown=False):
            for d in dirs:
                if d in skip_dirs:
                    continue
                dir_path = os.path.join(root, d)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        removed_count += 1
                        logger.info(f"Removed empty folder: {dir_path}")
                except Exception:
                    pass
        return removed_count

    def batch_rename_files(
        self,
        folder_path: str,
        prefix: str = "",
        suffix: str = "",
        find_str: str = "",
        replace_str: str = "",
        number_digits: int = 0
    ) -> List[Dict[str, str]]:
        """
        Batch renames files matching criteria in a target folder.
        
        Returns:
            List of dict results (old_name, new_name, success).
        """
        results: List[Dict[str, str]] = []
        if not os.path.exists(folder_path):
            return results

        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
        files.sort()

        for idx, filename in enumerate(files, start=1):
            base, ext = os.path.splitext(filename)
            new_base = base

            if find_str:
                new_base = new_base.replace(find_str, replace_str)

            if prefix:
                new_base = f"{prefix}{new_base}"

            if suffix:
                new_base = f"{new_base}{suffix}"

            if number_digits > 0:
                num_str = str(idx).zfill(number_digits)
                new_base = f"{new_base}_{num_str}"

            new_filename = f"{new_base}{ext}"
            if new_filename == filename:
                continue

            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, new_filename)

            try:
                os.rename(old_path, new_path)
                results.append({"old_name": filename, "new_name": new_filename, "status": "Success"})
                logger.info(f"Batch renamed: {filename} -> {new_filename}")
            except Exception as e:
                results.append({"old_name": filename, "new_name": new_filename, "status": f"Error: {e}"})
                logger.error(f"Failed to rename {filename}: {e}")

        return results

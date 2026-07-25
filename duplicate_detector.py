"""
Smart File Organizer - Multi-Tier SHA-256 Duplicate Detector Module
Efficiently identifies exact binary duplicate files using file size grouping, partial hashing, and full SHA-256 hashing.
"""

import hashlib
import os
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Callable, Any
from logger import logger


def calculate_file_hash(file_path: str, chunk_size: int = 65536, max_bytes: Optional[int] = None) -> Optional[str]:
    """
    Computes SHA-256 hash of a file using chunked reading.
    
    Args:
        file_path: Absolute path to the file.
        chunk_size: Read buffer chunk size (default 64KB).
        max_bytes: If specified, only reads up to max_bytes (useful for fast partial hashing).
        
    Returns:
        Hexadecimal SHA-256 hash string or None if unreadable.
    """
    hasher = hashlib.sha256()
    bytes_read = 0
    try:
        with open(file_path, "rb") as f:
            while True:
                to_read = chunk_size
                if max_bytes is not None:
                    remaining = max_bytes - bytes_read
                    if remaining <= 0:
                        break
                    to_read = min(chunk_size, remaining)

                chunk = f.read(to_read)
                if not chunk:
                    break
                hasher.update(chunk)
                bytes_read += len(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.warning(f"Unable to compute hash for file {file_path}: {e}")
        return None


class DuplicateDetector:
    """Provides high-performance duplicate file scanning and handling actions."""

    def __init__(self, mode: str = "move"):
        """
        Args:
            mode: Handling mode for duplicates - "skip", "delete", or "move".
        """
        self.mode = mode.lower()

    def find_duplicates(
        self,
        file_paths: List[str],
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[Dict[str, List[str]], List[str]]:
        """
        Scans list of file paths and returns duplicate groups and unique original files.
        Uses 3-stage optimization (Size grouping -> Partial 64KB Hash -> Full Hash).
        
        Returns:
            Tuple of (hash_to_paths_dict containing duplicate sets, list_of_original_unique_paths).
        """
        total_files = len(file_paths)
        if total_files == 0:
            return {}, []

        # Stage 1: Group files by file size
        size_groups: Dict[int, List[str]] = {}
        for idx, path in enumerate(file_paths, start=1):
            if progress_callback and idx % 100 == 0:
                progress_callback(idx, total_files, f"Grouping file sizes ({idx}/{total_files})...")
            try:
                sz = os.path.getsize(path)
                size_groups.setdefault(sz, []).append(path)
            except Exception:
                continue

        # Files with unique sizes are guaranteed non-duplicates
        potential_duplicates: List[str] = []
        unique_originals: List[str] = []
        for sz, paths in size_groups.items():
            if len(paths) == 1:
                unique_originals.append(paths[0])
            else:
                potential_duplicates.extend(paths)

        # Stage 2: Partial Hash (first 64KB) for potential duplicates
        partial_hash_groups: Dict[str, List[str]] = {}
        for idx, path in enumerate(potential_duplicates, start=1):
            if progress_callback and idx % 50 == 0:
                progress_callback(idx, len(potential_duplicates), f"Partial hash check ({idx}/{len(potential_duplicates)})...")
            p_hash = calculate_file_hash(path, max_bytes=65536)
            if p_hash:
                partial_hash_groups.setdefault(p_hash, []).append(path)

        # Stage 3: Full SHA-256 Hash for candidates sharing partial hashes
        full_hash_groups: Dict[str, List[str]] = {}
        candidate_paths: List[str] = []
        for p_hash, paths in partial_hash_groups.items():
            if len(paths) == 1:
                unique_originals.append(paths[0])
            else:
                candidate_paths.extend(paths)

        for idx, path in enumerate(candidate_paths, start=1):
            if progress_callback:
                progress_callback(idx, len(candidate_paths), f"Full SHA-256 verification ({idx}/{len(candidate_paths)})...")
            f_hash = calculate_file_hash(path)
            if f_hash:
                full_hash_groups.setdefault(f_hash, []).append(path)

        # Separate confirmed duplicates from primary originals
        confirmed_duplicates: Dict[str, List[str]] = {}
        for f_hash, paths in full_hash_groups.items():
            if len(paths) > 1:
                confirmed_duplicates[f_hash] = paths
                # The first file is kept as original, subsequent files are duplicates
                unique_originals.append(paths[0])
            else:
                unique_originals.extend(paths)

        logger.info(f"Duplicate scan complete. Found {len(confirmed_duplicates)} duplicate sets across {total_files} files.")
        return confirmed_duplicates, unique_originals

    def handle_duplicate_file(
        self,
        duplicate_path: str,
        original_path: str,
        target_folder: str,
        mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes action on a duplicate file based on mode (skip, delete, move).
        
        Returns:
            Dict details of operation result.
        """
        action_mode = (mode or self.mode).lower()
        filename = os.path.basename(duplicate_path)
        
        result = {
            "filename": filename,
            "src_path": duplicate_path,
            "dest_path": "",
            "action": action_mode,
            "success": False,
            "message": ""
        }

        if action_mode == "skip":
            result["success"] = True
            result["message"] = "Skipped duplicate file."
            logger.info(f"Skipped duplicate: {duplicate_path}")
            return result

        elif action_mode == "delete":
            try:
                os.remove(duplicate_path)
                result["success"] = True
                result["message"] = "Deleted duplicate file."
                logger.info(f"Deleted duplicate file: {duplicate_path}")
                return result
            except Exception as e:
                result["message"] = f"Failed to delete duplicate: {e}"
                logger.error(result["message"])
                return result

        elif action_mode == "move":
            # Move into _Duplicates directory inside target_folder
            dup_dir = os.path.join(target_folder, "_Duplicates")
            os.makedirs(dup_dir, exist_ok=True)

            dest_path = os.path.join(dup_dir, filename)
            # Prevent collision in _Duplicates folder
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                timestamp = int(os.path.getmtime(duplicate_path))
                dest_path = os.path.join(dup_dir, f"{base}_dup_{timestamp}{ext}")

            try:
                shutil.move(duplicate_path, dest_path)
                result["dest_path"] = dest_path
                result["success"] = True
                result["message"] = f"Moved to {dup_dir}"
                logger.info(f"Moved duplicate: {duplicate_path} -> {dest_path}")
                return result
            except Exception as e:
                result["message"] = f"Failed to move duplicate: {e}"
                logger.error(result["message"])
                return result

        return result

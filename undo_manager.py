"""
Smart File Organizer - Undo Manager Module
Manages transactional recording of file movements and provides complete safe single and batch restoration.
"""

import json
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from logger import logger


class UndoManager:
    """Manages transactional history for file movement operations and handles restoration."""

    def __init__(self, history_file: Optional[str] = None):
        if history_file is None:
            base_dir = Path(__file__).resolve().parent
            history_file = str(base_dir / "logs" / "undo_history.json")

        self.history_file = history_file
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        self.history: List[Dict[str, Any]] = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        """Loads undo transaction records from JSON history file."""
        if not os.path.exists(self.history_file):
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading undo history JSON: {e}")
            return []

    def _save_history(self) -> bool:
        """Saves undo history back to JSON file."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving undo history JSON: {e}")
            return False

    def record_batch(self, batch_id: str, target_folder: str, moves: List[Dict[str, Any]], created_folders: List[str]) -> None:
        """
        Records a completed organization transaction batch.
        
        Args:
            batch_id: Unique string identifier for the operation batch.
            target_folder: Base directory organized.
            moves: List of dicts containing 'src_path', 'dest_path', 'filename', etc.
            created_folders: List of relative/absolute folder paths created during organization.
        """
        record = {
            "batch_id": batch_id,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_folder": target_folder,
            "moves": moves,
            "created_folders": created_folders
        }
        self.history.insert(0, record)  # Newest first
        # Keep maximum 50 undo transactions
        self.history = self.history[:50]
        self._save_history()
        logger.info(f"Recorded undo transaction batch '{batch_id}' with {len(moves)} file operations.")

    def get_latest_transaction(self, target_folder: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent undo transaction, optionally filtered by target folder."""
        if not self.history:
            return None
        if target_folder:
            target_norm = os.path.normpath(target_folder).lower()
            for record in self.history:
                if os.path.normpath(record.get("target_folder", "")).lower() == target_norm:
                    return record
            return None
        return self.history[0]

    def undo_last_transaction(
        self,
        target_folder: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Restores files moved in the latest transaction batch back to their original locations.
        
        Returns:
            Dict summary of results (restored_count, failed_count, errors).
        """
        transaction = self.get_latest_transaction(target_folder)
        if not transaction:
            logger.warning("No undo transaction record found to restore.")
            return {"restored_count": 0, "failed_count": 0, "errors": ["No transaction record found."]}

        moves = transaction.get("moves", [])
        created_folders = transaction.get("created_folders", [])
        batch_id = transaction.get("batch_id")

        restored_count = 0
        failed_count = 0
        errors = []

        total = len(moves)
        for idx, item in enumerate(moves, start=1):
            src_path = item.get("src_path")    # Original position
            dest_path = item.get("dest_path")  # Organized location

            if progress_callback:
                progress_callback(idx, total, f"Restoring: {item.get('filename', '')}")

            if not dest_path or not os.path.exists(dest_path):
                failed_count += 1
                msg = f"File to restore missing at current location: {dest_path}"
                logger.warning(msg)
                errors.append(msg)
                continue

            try:
                # Ensure original directory exists
                os.makedirs(os.path.dirname(src_path), exist_ok=True)
                
                # If destination file exists, handle potential conflict
                if os.path.exists(src_path):
                    # Rename or overwrite
                    base, ext = os.path.splitext(src_path)
                    src_path = f"{base}_restored{ext}"

                shutil.move(dest_path, src_path)
                restored_count += 1
                logger.info(f"Restored: {dest_path} -> {src_path}")
            except Exception as e:
                failed_count += 1
                err_msg = f"Failed to restore {dest_path}: {e}"
                logger.error(err_msg)
                errors.append(err_msg)

        # Cleanup created empty directories if possible
        for folder in reversed(created_folders):
            if os.path.exists(folder) and os.path.isdir(folder):
                try:
                    if not os.listdir(folder):  # Directory is empty
                        os.rmdir(folder)
                        logger.info(f"Cleaned up empty organized folder: {folder}")
                except Exception:
                    pass

        # Remove transaction record from history
        if transaction in self.history:
            self.history.remove(transaction)
            self._save_history()

        logger.info(f"Undo completed: {restored_count} restored, {failed_count} failed.")
        return {
            "batch_id": batch_id,
            "restored_count": restored_count,
            "failed_count": failed_count,
            "errors": errors
        }

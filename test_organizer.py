"""
Smart File Organizer - Automated Test Suite
Verifies scanning, smart categorization, SHA-256 duplicate handling, undo transaction restoration, and empty folder cleanup.
"""

import os
import sys
import shutil
import time
from pathlib import Path
from organizer import FileOrganizerEngine
from settings import SettingsManager
from undo_manager import UndoManager
from utils import export_statistics_to_csv

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run_automated_tests():
    print("=== STARTING AUTOMATED INTEGRATION TESTS ===")
    base_dir = Path(__file__).resolve().parent
    test_dir = base_dir / "test_sandbox"

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

    os.makedirs(test_dir, exist_ok=True)

    # 1. Create sample files of various categories
    sample_files = [
        ("photo1.jpg", b"fake_image_content_1"),
        ("photo2.png", b"fake_image_content_2"),
        ("document1.docx", b"fake_doc_content"),
        ("report.pdf", b"fake_pdf_content"),
        ("song.mp3", b"fake_audio_content"),
        ("script.py", b"print('Hello World')"),
        ("data.csv", b"id,name\n1,test"),
        ("archive.zip", b"fake_zip_content"),
        ("duplicate_a.txt", b"EXACT_SAME_BINARY_CONTENT_12345"),
        ("duplicate_b.txt", b"EXACT_SAME_BINARY_CONTENT_12345"),  # Duplicate of duplicate_a.txt
    ]

    for fname, content in sample_files:
        with open(test_dir / fname, "wb") as f:
            f.write(content)

    # Create an empty subfolder to test cleanup
    os.makedirs(test_dir / "empty_subfolder", exist_ok=True)

    print(f"Created {len(sample_files)} test files in: {test_dir}")

    # 2. Run Organizer Engine
    settings_mgr = SettingsManager()
    undo_mgr = UndoManager()
    engine = FileOrganizerEngine(settings_mgr, undo_mgr)

    print("\n--- Running Organization Engine ---")
    summary = engine.organize_directory(str(test_dir))

    print(f"Moved files: {summary['moved_files']}")
    print(f"Duplicate files: {summary['duplicate_files']}")
    print(f"Folders created: {summary['folders_created']}")
    print(f"Time taken: {summary['time_taken']:.4f}s")

    # Assertions
    assert summary['moved_files'] > 0, "Error: No files moved."
    assert summary['duplicate_files'] == 1, f"Error: Expected 1 duplicate, got {summary['duplicate_files']}."
    assert not os.path.exists(test_dir / "empty_subfolder"), "Error: Empty folder was not cleaned up."
    assert os.path.exists(test_dir / "Images" / "photo1.jpg"), "Error: photo1.jpg not found in Images folder."
    assert os.path.exists(test_dir / "PDFs" / "report.pdf"), "Error: report.pdf not found in PDFs folder."
    assert os.path.exists(test_dir / "Code Files" / "script.py"), "Error: script.py not found in Code Files folder."
    assert os.path.exists(test_dir / "_Duplicates"), "Error: _Duplicates folder missing."

    print("[OK] Organization & Duplicate Detection Passed!")

    # 3. Test CSV Export
    csv_path = test_dir / "report_test.csv"
    export_statistics_to_csv(summary, summary['activity'], str(csv_path))
    assert os.path.exists(csv_path), "Error: CSV export file not created."
    print("[OK] CSV Statistics Export Passed!")

    # 4. Test Undo Restoration
    print("\n--- Testing Undo Transaction Restoration ---")
    undo_res = undo_mgr.undo_last_transaction(target_folder=str(test_dir))
    print(f"Restored files: {undo_res['restored_count']}")
    assert undo_res['restored_count'] > 0, "Error: Undo failed to restore files."
    assert os.path.exists(test_dir / "photo1.jpg"), "Error: photo1.jpg not restored to root test folder."
    print("[OK] Undo Engine Restoration Passed!")

    # Clean up test sandbox
    shutil.rmtree(test_dir)
    print("\n=== ALL INTEGRATION TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    run_automated_tests()

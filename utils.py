"""
Smart File Organizer - System Utilities & Helper Module
Provides cross-platform OS folder opening, file size/time formatting, CSV exports, desktop notifications, and file previews.
"""

import os
import sys
import csv
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Any, Optional
from logger import logger

# Try importing plyer for cross-platform desktop notifications
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False


def format_bytes(size_bytes: int) -> str:
    """Converts bytes to human-readable size string (e.g. 1.5 MB, 2.3 GB)."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"


def format_time(seconds: float) -> str:
    """Formats time duration in seconds to MM:SS or HH:MM:SS format."""
    if seconds <= 0:
        return "00:00"
    secs = int(seconds)
    hours = secs // 3600
    minutes = (secs % 3600) // 60
    remaining_secs = secs % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{remaining_secs:02d}"
    return f"{minutes:02d}:{remaining_secs:02d}"


def open_folder_in_explorer(path: str) -> bool:
    """Opens directory in system's default file manager (Explorer, Finder, or File Manager)."""
    if not os.path.exists(path):
        logger.error(f"Cannot open folder; path does not exist: {path}")
        return False

    system_name = platform.system()
    try:
        if system_name == "Windows":
            os.startfile(os.path.normpath(path))
        elif system_name == "Darwin":  # macOS
            subprocess.run(["open", path], check=True)
        else:  # Linux / Unix
            subprocess.run(["xdg-open", path], check=True)
        logger.info(f"Opened folder in file manager: {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to open folder {path}: {e}")
        return False


def show_desktop_notification(title: str, message: str) -> None:
    """Triggers system desktop notification."""
    try:
        if PLYER_AVAILABLE:
            notification.notify(
                title=title,
                message=message,
                app_name="Smart File Organizer",
                timeout=5
            )
            return
    except Exception as e:
        logger.debug(f"Plyer notification error: {e}")

    # Fallback for Windows if plyer fails or isn't installed
    if platform.system() == "Windows":
        try:
            # Fallback using Windows PowerShell Toast notification script
            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName('text')
            $textNodes.Item(0).AppendChild($template.CreateTextNode('{title}')) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode('{message}')) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::$template
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Smart File Organizer').Show($toast)
            """
            # Run PowerShell command non-blockingly
            subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
                             creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
        except Exception:
            pass


def export_statistics_to_csv(summary_stats: Dict[str, Any], file_activity: List[Dict[str, Any]], output_path: str) -> str:
    """Exports activity details and summary metrics to a CSV file."""
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["=== SMART FILE ORGANIZER REPORT ==="])
            writer.writerow(["Generated At", summary_stats.get("timestamp", "")])
            writer.writerow(["Target Directory", summary_stats.get("target_folder", "")])
            writer.writerow(["Total Files Processed", summary_stats.get("total_files", 0)])
            writer.writerow(["Moved Files", summary_stats.get("moved_files", 0)])
            writer.writerow(["Duplicates Actioned", summary_stats.get("duplicate_files", 0)])
            writer.writerow(["Folders Created", summary_stats.get("folders_created", 0)])
            writer.writerow(["Total Reclaimed Space", format_bytes(summary_stats.get("total_size_bytes", 0))])
            writer.writerow(["Time Taken (s)", f"{summary_stats.get('time_taken', 0):.2f}"])
            writer.writerow([])
            writer.writerow(["=== FILE ACTIVITY LOG ==="])
            writer.writerow(["Filename", "Category", "Original Path", "New Path", "Size", "Status", "Timestamp"])
            for row in file_activity:
                writer.writerow([
                    row.get("filename", ""),
                    row.get("category", ""),
                    row.get("src_path", ""),
                    row.get("dest_path", ""),
                    format_bytes(row.get("size", 0)),
                    row.get("status", ""),
                    row.get("timestamp", "")
                ])
        logger.info(f"Exported statistics to CSV: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")
        raise e


def get_file_preview(file_path: str, max_chars: int = 500) -> Dict[str, Any]:
    """Generates preview metadata and text/image summary for a given file."""
    if not os.path.exists(file_path):
        return {"error": "File does not exist."}

    path = Path(file_path)
    stat = path.stat()
    size_str = format_bytes(stat.st_size)
    ext = path.suffix.lower()

    info = {
        "filename": path.name,
        "extension": ext,
        "size": size_str,
        "modified": str(stat.st_mtime),
        "type": "binary",
        "preview_text": ""
    }

    # Text / Code / JSON preview
    text_extensions = {".txt", ".md", ".json", ".py", ".js", ".html", ".css", ".xml", ".csv", ".log", ".yaml", ".yml"}
    if ext in text_extensions and stat.st_size < 2 * 1024 * 1024:  # Under 2MB
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(max_chars)
                info["type"] = "text"
                info["preview_text"] = content
        except Exception:
            pass

    return info

"""
Smart File Organizer - Settings & Configuration Manager Module
Handles settings persistence, JSON serialization, custom category rules, and multi-language support.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from logger import logger


DEFAULT_SETTINGS: Dict[str, Any] = {
    "theme_mode": "Dark",
    "language": "English",
    "remember_last_folder": True,
    "last_folder": "",
    "auto_organize_on_startup": False,
    "clean_empty_folders": True,
    "duplicate_handling": "move",  # Options: "skip", "delete", "move"
    "recursive_scan": False,
    "desktop_notifications": True,
    "recent_folders": [],
    "categories": {
        "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico", ".heic"],
        "Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp"],
        "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".alac"],
        "Documents": [".doc", ".docx", ".txt", ".rtf", ".odt", ".md", ".tex", ".wpd"],
        "PDFs": [".pdf"],
        "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"],
        "Executables": [".exe", ".msi", ".bat", ".cmd", ".sh", ".app", ".dmg", ".bin"],
        "Code Files": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".cs", ".php", ".rb", ".go", ".rs", ".ts", ".json", ".xml", ".yaml", ".yml", ".sql"],
        "Spreadsheets": [".xls", ".xlsx", ".csv", ".ods", ".tsv"],
        "Presentations": [".ppt", ".pptx", ".key", ".odp"]
    },
    "custom_rules": [
        {
            "name": "Financial Invoices",
            "field": "name_contains",
            "pattern": "invoice",
            "target_folder": "Documents/Invoices"
        },
        {
            "name": "Large Files (>100MB)",
            "field": "size_greater_mb",
            "pattern": "100",
            "target_folder": "Large_Files"
        }
    ],
    "schedule_interval_minutes": 0
}

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "English": {
        "app_title": "Smart File Organizer",
        "nav_organize": "Organize",
        "nav_statistics": "Statistics",
        "nav_settings": "Settings",
        "nav_logs": "Logs",
        "nav_search_batch": "Search & Batch",
        "select_folder": "Select Folder to Organize",
        "browse": "Browse",
        "recent_folders": "Recent Folders",
        "start_organize": "Start Organizing",
        "undo": "Undo Last Move",
        "cancel": "Cancel",
        "total_files": "Total Files",
        "moved_files": "Moved Files",
        "duplicates_found": "Duplicates",
        "space_saved": "Space Reclaimed",
        "time_elapsed": "Time Elapsed",
        "time_remaining": "Estimated Remaining",
        "ready_status": "Ready to organize target directory.",
        "organizing_status": "Organizing files...",
        "complete_status": "Organization complete!",
        "open_folder": "Open Directory",
        "export_csv": "Export Statistics CSV",
        "theme": "Theme",
        "language": "Language",
        "duplicate_mode": "Duplicate Action",
        "clean_empty": "Clean Empty Folders",
        "notifications": "Enable Notifications",
        "save_settings": "Save Settings",
        "batch_rename": "Batch Rename Tool",
        "search_placeholder": "Search moved or scanned files...",
    },
    "Spanish": {
        "app_title": "Organizador Inteligente de Archivos",
        "nav_organize": "Organizar",
        "nav_statistics": "Estadísticas",
        "nav_settings": "Configuración",
        "nav_logs": "Registros",
        "nav_search_batch": "Buscar y Lote",
        "select_folder": "Seleccionar carpeta para organizar",
        "browse": "Examinar",
        "recent_folders": "Carpetas Recientes",
        "start_organize": "Iniciar Organización",
        "undo": "Deshacer Movimiento",
        "cancel": "Cancelar",
        "total_files": "Archivos Totales",
        "moved_files": "Archivos Movidos",
        "duplicates_found": "Duplicados",
        "space_saved": "Espacio Recuperado",
        "time_elapsed": "Tiempo Transcurrido",
        "time_remaining": "Tiempo Restante Estimado",
        "ready_status": "Listo para organizar el directorio.",
        "organizing_status": "Organizando archivos...",
        "complete_status": "¡Organización completada!",
        "open_folder": "Abrir Directorio",
        "export_csv": "Exportar CSV",
        "theme": "Tema",
        "language": "Idioma",
        "duplicate_mode": "Acción para Duplicados",
        "clean_empty": "Limpiar Carpetas Vacías",
        "notifications": "Habilitar Notificaciones",
        "save_settings": "Guardar Configuración",
        "batch_rename": "Renombrado Masivo",
        "search_placeholder": "Buscar archivos movidos...",
    },
    "French": {
        "app_title": "Organisateur Intelligent de Fichiers",
        "nav_organize": "Organiser",
        "nav_statistics": "Statistiques",
        "nav_settings": "Paramètres",
        "nav_logs": "Journaux",
        "nav_search_batch": "Recherche & Lot",
        "select_folder": "Sélectionner le dossier à organiser",
        "browse": "Parcourir",
        "recent_folders": "Dossiers Récents",
        "start_organize": "Démarrer l'organisation",
        "undo": "Annuler",
        "cancel": "Annuler l'action",
        "total_files": "Fichiers Totaux",
        "moved_files": "Fichiers Déplacés",
        "duplicates_found": "Doublons",
        "space_saved": "Espace Libéré",
        "time_elapsed": "Temps Écoule",
        "time_remaining": "Temps Restant Estimé",
        "ready_status": "Prêt à organiser le dossier.",
        "organizing_status": "Organisation en cours...",
        "complete_status": "Organisation terminée !",
        "open_folder": "Ouvrir le dossier",
        "export_csv": "Exporter CSV",
        "theme": "Thème",
        "language": "Langue",
        "duplicate_mode": "Gestion des Doublons",
        "clean_empty": "Nettoyer les Dossiers Vides",
        "notifications": "Activer les Notifications",
        "save_settings": "Enregistrer les Paramètres",
        "batch_rename": "Renommage en Lot",
        "search_placeholder": "Rechercher des fichiers...",
    },
    "German": {
        "app_title": "Intelligenter Datei-Organizer",
        "nav_organize": "Organisieren",
        "nav_statistics": "Statistiken",
        "nav_settings": "Einstellungen",
        "nav_logs": "Protokolle",
        "nav_search_batch": "Suche & Stapel",
        "select_folder": "Ordner zum Organisieren auswählen",
        "browse": "Durchsuchen",
        "recent_folders": "Kürzliche Ordner",
        "start_organize": "Starten",
        "undo": "Rückgängig machen",
        "cancel": "Abbrechen",
        "total_files": "Dateien Gesamt",
        "moved_files": "Verschobene Dateien",
        "duplicates_found": "Duplikate",
        "space_saved": "Gespeicherter Speicherplatz",
        "time_elapsed": "Verstrichene Zeit",
        "time_remaining": "Geschätzte Restzeit",
        "ready_status": "Bereit zum Organisieren.",
        "organizing_status": "Dateien werden organisiert...",
        "complete_status": "Organisation abgeschlossen!",
        "open_folder": "Ordner Öffnen",
        "export_csv": "CSV Exportieren",
        "theme": "Design",
        "language": "Sprache",
        "duplicate_mode": "Duplikat-Aktion",
        "clean_empty": "Leere Ordner Löschen",
        "notifications": "Benachrichtigungen Aktivieren",
        "save_settings": "Einstellungen Speichern",
        "batch_rename": "Stapelumbenennung",
        "search_placeholder": "Dateien suchen...",
    },
    "Chinese": {
        "app_title": "智能文件整理器",
        "nav_organize": "整理文件",
        "nav_statistics": "数据统计",
        "nav_settings": "软件设置",
        "nav_logs": "运行日志",
        "nav_search_batch": "搜索与重命名",
        "select_folder": "选择要整理的文件夹",
        "browse": "浏览",
        "recent_folders": "最近使用文件夹",
        "start_organize": "开始整理",
        "undo": "撤销上一次移动",
        "cancel": "取消",
        "total_files": "文件总数",
        "moved_files": "已移动文件",
        "duplicates_found": "重复文件",
        "space_saved": "释放空间",
        "time_elapsed": "已用时间",
        "time_remaining": "预计剩余时间",
        "ready_status": "准备就绪，可以整理目标文件夹。",
        "organizing_status": "正在整理文件...",
        "complete_status": "文件整理完成！",
        "open_folder": "打开文件夹",
        "export_csv": "导出 CSV 统计表",
        "theme": "外观主题",
        "language": "界面语言",
        "duplicate_mode": "重复文件处理",
        "clean_empty": "清理空文件夹",
        "notifications": "开启系统通知",
        "save_settings": "保存设置",
        "batch_rename": "批量重命名",
        "search_placeholder": "搜索文件...",
    }
}


class SettingsManager:
    """Manages reading, writing, and updating application settings stored in JSON format."""

    def __init__(self, settings_file: Optional[str] = None):
        if settings_file is None:
            base_dir = Path(__file__).resolve().parent
            settings_file = str(base_dir / "settings.json")
        
        self.settings_file = settings_file
        self.settings: Dict[str, Any] = self.load_settings()

    def load_settings(self) -> Dict[str, Any]:
        """Loads settings from JSON file or returns defaults if file missing or corrupted."""
        if not os.path.exists(self.settings_file):
            logger.info("settings.json not found. Initializing with default settings.")
            self.save_settings(DEFAULT_SETTINGS)
            return DEFAULT_SETTINGS.copy()

        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Merge loaded settings with default keys to handle missing options safely
                merged = DEFAULT_SETTINGS.copy()
                merged.update(loaded)
                return merged
        except Exception as e:
            logger.error(f"Error loading settings.json: {e}. Falling back to default settings.")
            return DEFAULT_SETTINGS.copy()

    def save_settings(self, new_settings: Optional[Dict[str, Any]] = None) -> bool:
        """Saves current or updated settings dict to JSON file."""
        if new_settings is not None:
            self.settings = new_settings

        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            logger.info("Settings successfully saved to settings.json.")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieves a single setting key value."""
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Updates a setting key and saves changes."""
        self.settings[key] = value
        self.save_settings()

    def add_recent_folder(self, folder_path: str) -> None:
        """Appends folder path to recent_folders list up to max 10 entries."""
        if not folder_path or not os.path.exists(folder_path):
            return
        recent = self.settings.get("recent_folders", [])
        if folder_path in recent:
            recent.remove(folder_path)
        recent.insert(0, folder_path)
        self.settings["recent_folders"] = recent[:10]
        self.save_settings()

    def get_extension_category(self, ext: str) -> str:
        """Finds category corresponding to a file extension (e.g. '.png' -> 'Images')."""
        ext = ext.lower()
        categories = self.settings.get("categories", {})
        for cat_name, ext_list in categories.items():
            if ext in [e.lower() for e in ext_list]:
                return cat_name
        return "Others"

    def get_translation(self, key: str) -> str:
        """Retrieves localized UI text string for current selected language."""
        lang = self.settings.get("language", "English")
        lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["English"])
        return lang_dict.get(key, TRANSLATIONS["English"].get(key, key))

"""
Smart File Organizer - Main Desktop Application GUI
Built with CustomTkinter, supporting multi-threading, custom rules, live charts, and full portfolio-grade UX.
"""

import os
import sys
import time
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Dict, List, Any, Optional

import customtkinter as ctk

# Import matplotlib safely for integrated GUI charts
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Import PIL for image previews & icons
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Import core app modules
from settings import SettingsManager
from logger import setup_logger, logger
from undo_manager import UndoManager
from organizer import FileOrganizerEngine
from utils import (
    format_bytes,
    format_time,
    open_folder_in_explorer,
    export_statistics_to_csv,
    show_desktop_notification,
    get_file_preview,
)

# Configure CustomTkinter Appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class SmartFileOrganizerApp(ctk.CTk):
    """Main Application Window for Smart File Organizer."""

    def __init__(self):
        super().__init__()

        # Managers & Engines
        self.settings_mgr = SettingsManager()
        self.undo_mgr = UndoManager()
        self.engine = FileOrganizerEngine(self.settings_mgr, self.undo_mgr)

        # Threading Queue for Log Stream & Progress Updates
        self.ui_queue = queue.Queue()

        # Logger Setup with UI Handler
        setup_logger(ui_callback=self.on_log_emitted)

        # UI State Variables
        self.target_folder_var = ctk.StringVar(value=self.settings_mgr.get("last_folder", ""))
        self.status_var = ctk.StringVar(value=self.settings_mgr.get_translation("ready_status"))
        self.progress_percent_var = ctk.StringVar(value="0%")
        self.file_counter_var = ctk.StringVar(value="0 / 0 Files")
        self.elapsed_time_var = ctk.StringVar(value="00:00")
        self.remaining_time_var = ctk.StringVar(value="00:00")
        self.search_filter_var = ctk.StringVar()
        self.search_filter_var.trace_add("write", self.filter_activity_table)

        # Metric Card Variables
        self.metric_total_var = ctk.StringVar(value="0")
        self.metric_moved_var = ctk.StringVar(value="0")
        self.metric_dup_var = ctk.StringVar(value="0")
        self.metric_space_var = ctk.StringVar(value="0 B")

        # Current summary stats
        self.last_summary_stats: Dict[str, Any] = {}
        self.last_activity_log: List[Dict[str, Any]] = []

        # Configure Window
        self.title(self.settings_mgr.get_translation("app_title"))
        self.geometry("1100x700")
        self.minsize(950, 600)

        # Apply saved theme mode
        theme = self.settings_mgr.get("theme_mode", "Dark")
        ctk.set_appearance_mode(theme)

        # Build UI Layout
        self.setup_ui_layout()

        # Keyboard Shortcuts
        self.bind("<Control-o>", lambda event: self.browse_folder())
        self.bind("<Control-O>", lambda event: self.browse_folder())
        self.bind("<Control-r>", lambda event: self.start_organizing())
        self.bind("<Control-R>", lambda event: self.start_organizing())
        self.bind("<Control-z>", lambda event: self.undo_last_move())
        self.bind("<Control-Z>", lambda event: self.undo_last_move())

        # Start UI Queue Poller
        self.poll_ui_queue()

        # Auto-organize on startup if configured
        if self.settings_mgr.get("auto_organize_on_startup") and self.target_folder_var.get():
            self.after(1000, self.start_organizing)

    def setup_ui_layout(self):
        """Constructs sidebar and main content panels."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ------------------ SIDEBAR ------------------
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)

        # App Logo & Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="📁 Smart Organizer",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 20), sticky="w")

        # Sidebar Buttons
        self.btn_nav_organize = ctk.CTkButton(
            self.sidebar_frame,
            text=f"📁  {self.settings_mgr.get_translation('nav_organize')}",
            anchor="w",
            font=ctk.CTkFont(size=14),
            command=lambda: self.show_tab("organize")
        )
        self.btn_nav_organize.grid(row=1, column=0, padx=15, pady=8, sticky="ew")

        self.btn_nav_stats = ctk.CTkButton(
            self.sidebar_frame,
            text=f"📊  {self.settings_mgr.get_translation('nav_statistics')}",
            anchor="w",
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            command=lambda: self.show_tab("statistics")
        )
        self.btn_nav_stats.grid(row=2, column=0, padx=15, pady=8, sticky="ew")

        self.btn_nav_search = ctk.CTkButton(
            self.sidebar_frame,
            text=f"🔍  {self.settings_mgr.get_translation('nav_search_batch')}",
            anchor="w",
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            command=lambda: self.show_tab("search_batch")
        )
        self.btn_nav_search.grid(row=3, column=0, padx=15, pady=8, sticky="ew")

        self.btn_nav_settings = ctk.CTkButton(
            self.sidebar_frame,
            text=f"⚙️  {self.settings_mgr.get_translation('nav_settings')}",
            anchor="w",
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            command=lambda: self.show_tab("settings")
        )
        self.btn_nav_settings.grid(row=4, column=0, padx=15, pady=8, sticky="ew")

        self.btn_nav_logs = ctk.CTkButton(
            self.sidebar_frame,
            text=f"📜  {self.settings_mgr.get_translation('nav_logs')}",
            anchor="w",
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            command=lambda: self.show_tab("logs")
        )
        self.btn_nav_logs.grid(row=5, column=0, padx=15, pady=8, sticky="ew")

        # Sidebar Footer: Quick Theme Toggle
        self.theme_label = ctk.CTkLabel(self.sidebar_frame, text="Theme Mode:", font=ctk.CTkFont(size=12))
        self.theme_label.grid(row=7, column=0, padx=20, pady=(10, 2), sticky="w")
        self.theme_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["Dark", "Light", "System"],
            command=self.change_theme
        )
        self.theme_menu.set(self.settings_mgr.get("theme_mode", "Dark"))
        self.theme_menu.grid(row=8, column=0, padx=15, pady=(0, 20), sticky="ew")

        # ------------------ MAIN CONTAINER ------------------
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Tabs Frames
        self.tab_organize = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.tab_stats = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.tab_search_batch = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.tab_settings = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.tab_logs = ctk.CTkFrame(self.main_container, fg_color="transparent")

        # Build Individual Tabs
        self.setup_organize_tab()
        self.setup_statistics_tab()
        self.setup_search_batch_tab()
        self.setup_settings_tab()
        self.setup_logs_tab()

        # Show default tab
        self.show_tab("organize")

    def show_tab(self, name: str):
        """Switches active main panel view and updates sidebar button highlights."""
        tabs = {
            "organize": (self.tab_organize, self.btn_nav_organize),
            "statistics": (self.tab_stats, self.btn_nav_stats),
            "search_batch": (self.tab_search_batch, self.btn_nav_search),
            "settings": (self.tab_settings, self.btn_nav_settings),
            "logs": (self.tab_logs, self.btn_nav_logs),
        }

        for tab_key, (tab_frame, btn) in tabs.items():
            if tab_key == name:
                tab_frame.grid(row=0, column=0, sticky="nsew")
                btn.configure(fg_color=("#3B8ED0", "#1F6AA5"), text_color="white")
            else:
                tab_frame.grid_forget()
                btn.configure(fg_color="transparent", text_color=("gray10", "gray90"))

        if name == "statistics":
            self.refresh_statistics_charts()

    # ------------------------------------------------------------------
    # 1. ORGANIZE TAB
    # ------------------------------------------------------------------
    def setup_organize_tab(self):
        self.tab_organize.grid_rowconfigure(3, weight=1)
        self.tab_organize.grid_columnconfigure(0, weight=1)

        # Folder Picker Bar
        folder_frame = ctk.CTkFrame(self.tab_organize)
        folder_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        folder_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(folder_frame, text="Target Folder:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=15)
        
        self.entry_folder = ctk.CTkEntry(folder_frame, textvariable=self.target_folder_var, font=ctk.CTkFont(size=13))
        self.entry_folder.grid(row=0, column=1, padx=10, pady=15, sticky="ew")

        self.btn_browse = ctk.CTkButton(
            folder_frame,
            text=self.settings_mgr.get_translation("browse"),
            width=100,
            command=self.browse_folder
        )
        self.btn_browse.grid(row=0, column=2, padx=10, pady=15)

        self.btn_open_folder = ctk.CTkButton(
            folder_frame,
            text="📂 " + self.settings_mgr.get_translation("open_folder"),
            width=130,
            fg_color="#2B2B2B",
            hover_color="#3A3A3A",
            command=self.open_current_folder
        )
        self.btn_open_folder.grid(row=0, column=3, padx=(0, 15), pady=15)

        # Recent Folders Dropdown
        recent = self.settings_mgr.get("recent_folders", [])
        if recent:
            self.recent_menu = ctk.CTkOptionMenu(
                folder_frame,
                values=["Recent Folders..."] + recent,
                command=self.on_recent_selected,
                width=160
            )
            self.recent_menu.grid(row=0, column=4, padx=(0, 15), pady=15)

        # Action Buttons & Controls
        controls_frame = ctk.CTkFrame(self.tab_organize, fg_color="transparent")
        controls_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        self.btn_start = ctk.CTkButton(
            controls_frame,
            text="🚀  " + self.settings_mgr.get_translation("start_organize"),
            font=ctk.CTkFont(size=15, weight="bold"),
            height=40,
            fg_color="#2CC985",
            hover_color="#25A26B",
            command=self.start_organizing
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_undo = ctk.CTkButton(
            controls_frame,
            text="↩️  " + self.settings_mgr.get_translation("undo"),
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color="#E5A93C",
            hover_color="#C48D2E",
            command=self.undo_last_move
        )
        self.btn_undo.pack(side="left", padx=10)

        self.btn_cancel = ctk.CTkButton(
            controls_frame,
            text="🛑  " + self.settings_mgr.get_translation("cancel"),
            font=ctk.CTkFont(size=14),
            height=40,
            fg_color="#EB5757",
            hover_color="#C74343",
            state="disabled",
            command=self.cancel_organization
        )
        self.btn_cancel.pack(side="left", padx=10)

        # Progress Section
        progress_frame = ctk.CTkFrame(self.tab_organize)
        progress_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        progress_frame.grid_columnconfigure(0, weight=1)

        status_bar = ctk.CTkFrame(progress_frame, fg_color="transparent")
        status_bar.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        status_bar.grid_columnconfigure(0, weight=1)

        self.lbl_status = ctk.CTkLabel(status_bar, textvariable=self.status_var, font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_status.grid(row=0, column=0, sticky="w")

        self.lbl_counter = ctk.CTkLabel(status_bar, textvariable=self.file_counter_var, font=ctk.CTkFont(size=12))
        self.lbl_counter.grid(row=0, column=1, sticky="e", padx=10)

        self.lbl_percent = ctk.CTkLabel(status_bar, textvariable=self.progress_percent_var, font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_percent.grid(row=0, column=2, sticky="e")

        self.progressbar = ctk.CTkProgressBar(progress_frame, height=12)
        self.progressbar.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.progressbar.set(0.0)

        meta_bar = ctk.CTkFrame(progress_frame, fg_color="transparent")
        meta_bar.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(meta_bar, text="Elapsed: ", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
        ctk.CTkLabel(meta_bar, textvariable=self.elapsed_time_var, font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 20))
        
        ctk.CTkLabel(meta_bar, text="Remaining: ", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left")
        ctk.CTkLabel(meta_bar, textvariable=self.remaining_time_var, font=ctk.CTkFont(size=11)).pack(side="left")

        # Metric Cards Container
        cards_frame = ctk.CTkFrame(self.tab_organize, fg_color="transparent")
        cards_frame.grid(row=3, column=0, sticky="ew", pady=(0, 15))
        for i in range(4):
            cards_frame.grid_columnconfigure(i, weight=1)

        self.create_metric_card(cards_frame, 0, "📄 Total Files", self.metric_total_var, "#1F6AA5")
        self.create_metric_card(cards_frame, 1, "📦 Moved Files", self.metric_moved_var, "#2CC985")
        self.create_metric_card(cards_frame, 2, "⚠️ Duplicates", self.metric_dup_var, "#E5A93C")
        self.create_metric_card(cards_frame, 3, "💾 Space Saved", self.metric_space_var, "#9B51E0")

        # Activity Table & Filter
        table_container = ctk.CTkFrame(self.tab_organize)
        table_container.grid(row=4, column=0, sticky="nsew")
        table_container.grid_rowconfigure(1, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        filter_bar = ctk.CTkFrame(table_container, fg_color="transparent")
        filter_bar.grid(row=0, column=0, sticky="ew", padx=15, pady=10)
        filter_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(filter_bar, text="Activity Log:", font=ctk.CTkFont(size=13, weight="bold")).grid(row=0, column=0, padx=(0, 10))
        
        self.entry_search = ctk.CTkEntry(
            filter_bar,
            textvariable=self.search_filter_var,
            placeholder_text=self.settings_mgr.get_translation("search_placeholder"),
            height=30
        )
        self.entry_search.grid(row=0, column=1, sticky="ew", padx=10)

        # Styled Treeview for File Activity
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background="#242424",
            foreground="#FFFFFF",
            fieldbackground="#242424",
            rowheight=26,
            font=("Segoe UI", 10)
        )
        style.configure("Treeview.Heading", background="#1F1F1F", foreground="#FFFFFF", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#1F6AA5")])

        columns = ("filename", "category", "size", "status", "src_path", "dest_path", "time")
        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", height=8)

        self.tree.heading("filename", text="Filename")
        self.tree.heading("category", text="Category")
        self.tree.heading("size", text="Size")
        self.tree.heading("status", text="Status")
        self.tree.heading("src_path", text="Original Path")
        self.tree.heading("dest_path", text="Destination Path")
        self.tree.heading("time", text="Time")

        self.tree.column("filename", width=180)
        self.tree.column("category", width=110)
        self.tree.column("size", width=80)
        self.tree.column("status", width=120)
        self.tree.column("src_path", width=220)
        self.tree.column("dest_path", width=220)
        self.tree.column("time", width=80)

        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=1, column=0, sticky="nsew", padx=(15, 0), pady=(0, 15))
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 15), pady=(0, 15))

        self.tree.bind("<Double-1>", self.on_activity_double_click)

    def create_metric_card(self, parent, col, title, text_var, color):
        card = ctk.CTkFrame(parent, fg_color="#242424", border_width=1, border_color=color)
        card.grid(row=0, column=col, padx=5, sticky="ew")
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="gray70").pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(card, textvariable=text_var, font=ctk.CTkFont(size=18, weight="bold"), text_color=color).pack(anchor="w", padx=12, pady=(0, 10))

    # ------------------------------------------------------------------
    # 2. STATISTICS TAB
    # ------------------------------------------------------------------
    def setup_statistics_tab(self):
        self.tab_stats.grid_rowconfigure(1, weight=1)
        self.tab_stats.grid_columnconfigure(0, weight=1)

        # Header Bar
        hdr_frame = ctk.CTkFrame(self.tab_stats, fg_color="transparent")
        hdr_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        hdr_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr_frame, text="📊 Organization Analytics & Distribution", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, sticky="w")

        self.btn_export_csv = ctk.CTkButton(
            hdr_frame,
            text="📥 " + self.settings_mgr.get_translation("export_csv"),
            command=self.export_csv_report
        )
        self.btn_export_csv.grid(row=0, column=1, sticky="e")

        # Matplotlib Charts Container
        self.chart_container = ctk.CTkFrame(self.tab_stats)
        self.chart_container.grid(row=1, column=0, sticky="nsew")
        self.chart_container.grid_rowconfigure(0, weight=1)
        self.chart_container.grid_columnconfigure(0, weight=1)

    def refresh_statistics_charts(self):
        """Renders dynamic Matplotlib charts based on last organization summary."""
        for widget in self.chart_container.winfo_children():
            widget.destroy()

        if not MATPLOTLIB_AVAILABLE:
            ctk.CTkLabel(
                self.chart_container,
                text="Matplotlib not installed. Charts unavailable.\nRun: pip install matplotlib",
                font=ctk.CTkFont(size=14)
            ).pack(expand=True)
            return

        if not self.last_activity_log:
            ctk.CTkLabel(
                self.chart_container,
                text="No statistics data available yet.\nOrganize a folder to view charts!",
                font=ctk.CTkFont(size=15, weight="bold"),
                text_color="gray60"
            ).pack(expand=True)
            return

        # Calculate category distribution
        cat_counts: Dict[str, int] = {}
        cat_sizes: Dict[str, int] = {}
        for item in self.last_activity_log:
            cat = item.get("category", "Others")
            size = item.get("size", 0)
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            cat_sizes[cat] = cat_sizes.get(cat, 0) + size

        fig = Figure(figsize=(9, 4.5), facecolor="#242424")
        
        # Pie Chart - File Counts
        ax1 = fig.add_subplot(121)
        ax1.set_facecolor("#242424")
        labels = list(cat_counts.keys())
        counts = list(cat_counts.values())
        colors = ["#3B8ED0", "#2CC985", "#E5A93C", "#9B51E0", "#EB5757", "#2D9CDB", "#F2994A", "#6FCF97"]
        
        ax1.pie(
            counts,
            labels=labels,
            autopct="%1.1f%%",
            startangle=140,
            textprops={"color": "white", "fontsize": 9},
            colors=colors[:len(labels)]
        )
        ax1.set_title("Files by Category", color="white", fontsize=12, fontweight="bold")

        # Bar Chart - Size Distribution (MB)
        ax2 = fig.add_subplot(122)
        ax2.set_facecolor("#242424")
        sizes_mb = [s / (1024 * 1024) for s in cat_sizes.values()]
        bars = ax2.bar(labels, sizes_mb, color="#3B8ED0")
        ax2.set_title("Storage Usage (MB)", color="white", fontsize=12, fontweight="bold")
        ax2.tick_params(colors="white", labelsize=8)
        for spine in ax2.spines.values():
            spine.set_color("#444444")
        ax2.set_xticklabels(labels, rotation=45, ha="right", color="white")

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    # ------------------------------------------------------------------
    # 3. SEARCH & BATCH TAB
    # ------------------------------------------------------------------
    def setup_search_batch_tab(self):
        self.tab_search_batch.grid_rowconfigure(1, weight=1)
        self.tab_search_batch.grid_columnconfigure(0, weight=1)

        # Batch Rename Section Frame
        batch_frame = ctk.CTkFrame(self.tab_search_batch)
        batch_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        batch_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(batch_frame, text="🏷️ Batch File Renamer", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=4, padx=15, pady=(15, 10), sticky="w")

        ctk.CTkLabel(batch_frame, text="Prefix:").grid(row=1, column=0, padx=15, pady=5, sticky="e")
        self.entry_prefix = ctk.CTkEntry(batch_frame, placeholder_text="e.g. Doc_")
        self.entry_prefix.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(batch_frame, text="Suffix:").grid(row=1, column=2, padx=10, pady=5, sticky="e")
        self.entry_suffix = ctk.CTkEntry(batch_frame, placeholder_text="e.g. _2026")
        self.entry_suffix.grid(row=1, column=3, padx=(0, 15), pady=5, sticky="ew")

        ctk.CTkLabel(batch_frame, text="Find String:").grid(row=2, column=0, padx=15, pady=5, sticky="e")
        self.entry_find = ctk.CTkEntry(batch_frame, placeholder_text="String to replace...")
        self.entry_find.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(batch_frame, text="Replace With:").grid(row=2, column=2, padx=10, pady=5, sticky="e")
        self.entry_replace = ctk.CTkEntry(batch_frame, placeholder_text="New replacement...")
        self.entry_replace.grid(row=2, column=3, padx=(0, 15), pady=5, sticky="ew")

        ctk.CTkLabel(batch_frame, text="Number Digits:").grid(row=3, column=0, padx=15, pady=5, sticky="e")
        self.spin_digits = ctk.CTkOptionMenu(batch_frame, values=["0", "2", "3", "4"])
        self.spin_digits.set("3")
        self.spin_digits.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        self.btn_run_batch_rename = ctk.CTkButton(
            batch_frame,
            text="Execute Batch Rename",
            fg_color="#1F6AA5",
            command=self.run_batch_rename
        )
        self.btn_run_batch_rename.grid(row=3, column=3, padx=(0, 15), pady=15, sticky="e")

        # Results Console Frame
        res_frame = ctk.CTkFrame(self.tab_search_batch)
        res_frame.grid(row=1, column=0, sticky="nsew")
        res_frame.grid_rowconfigure(1, weight=1)
        res_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(res_frame, text="Batch Action Results:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=10, sticky="w")

        self.txt_batch_results = ctk.CTkTextbox(res_frame, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_batch_results.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

    # ------------------------------------------------------------------
    # 4. SETTINGS TAB
    # ------------------------------------------------------------------
    def setup_settings_tab(self):
        self.tab_settings.grid_rowconfigure(0, weight=1)
        self.tab_settings.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self.tab_settings)
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(1, weight=1)

        # General Options Section
        ctk.CTkLabel(scroll, text="⚙️ General Preferences", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 10), sticky="w")

        ctk.CTkLabel(scroll, text="Interface Language:").grid(row=1, column=0, padx=20, pady=8, sticky="w")
        self.opt_lang = ctk.CTkOptionMenu(
            scroll,
            values=list(self.settings_mgr.get("categories", {}).keys()) if False else ["English", "Spanish", "French", "German", "Chinese"],
            command=self.change_language
        )
        self.opt_lang.set(self.settings_mgr.get("language", "English"))
        self.opt_lang.grid(row=1, column=1, padx=20, pady=8, sticky="w")

        ctk.CTkLabel(scroll, text="Duplicate Handling Mode:").grid(row=2, column=0, padx=20, pady=8, sticky="w")
        self.opt_dup = ctk.CTkOptionMenu(scroll, values=["move", "skip", "delete"])
        self.opt_dup.set(self.settings_mgr.get("duplicate_handling", "move"))
        self.opt_dup.grid(row=2, column=1, padx=20, pady=8, sticky="w")

        self.chk_remember = ctk.CTkCheckBox(scroll, text="Remember Last Opened Directory")
        if self.settings_mgr.get("remember_last_folder"): self.chk_remember.select()
        self.chk_remember.grid(row=3, column=0, columnspan=2, padx=20, pady=8, sticky="w")

        self.chk_auto = ctk.CTkCheckBox(scroll, text="Auto Organize Target Directory on Application Launch")
        if self.settings_mgr.get("auto_organize_on_startup"): self.chk_auto.select()
        self.chk_auto.grid(row=4, column=0, columnspan=2, padx=20, pady=8, sticky="w")

        self.chk_clean = ctk.CTkCheckBox(scroll, text="Clean Empty Subfolders After Organization")
        if self.settings_mgr.get("clean_empty_folders"): self.chk_clean.select()
        self.chk_clean.grid(row=5, column=0, columnspan=2, padx=20, pady=8, sticky="w")

        self.chk_notify = ctk.CTkCheckBox(scroll, text="Enable Desktop Completion Notifications")
        if self.settings_mgr.get("desktop_notifications"): self.chk_notify.select()
        self.chk_notify.grid(row=6, column=0, columnspan=2, padx=20, pady=8, sticky="w")

        self.chk_recursive = ctk.CTkCheckBox(scroll, text="Scan Subdirectories Recursively")
        if self.settings_mgr.get("recursive_scan"): self.chk_recursive.select()
        self.chk_recursive.grid(row=7, column=0, columnspan=2, padx=20, pady=8, sticky="w")

        # Save Settings Button
        self.btn_save_cfg = ctk.CTkButton(
            scroll,
            text="💾 Save Settings",
            fg_color="#2CC985",
            hover_color="#25A26B",
            command=self.save_settings_from_gui
        )
        self.btn_save_cfg.grid(row=8, column=0, padx=20, pady=20, sticky="w")

    # ------------------------------------------------------------------
    # 5. LOGS TAB
    # ------------------------------------------------------------------
    def setup_logs_tab(self):
        self.tab_logs.grid_rowconfigure(1, weight=1)
        self.tab_logs.grid_columnconfigure(0, weight=1)

        # Header with Clear & Filter
        hdr = ctk.CTkFrame(self.tab_logs, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text="📜 Real-time System Logs (app.log)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")

        self.btn_clear_log = ctk.CTkButton(hdr, text="Clear Console", width=110, fg_color="#2B2B2B", command=self.clear_logs)
        self.btn_clear_log.grid(row=0, column=1, sticky="e")

        # Console Textbox
        self.txt_log_console = ctk.CTkTextbox(self.tab_logs, font=ctk.CTkFont(family="Consolas", size=11))
        self.txt_log_console.grid(row=1, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    # EVENT HANDLERS & THREAD WORKERS
    # ------------------------------------------------------------------
    def on_log_emitted(self, msg: str, level: str):
        """Callback from Logger placing log messages into thread queue."""
        self.ui_queue.put(("log", msg, level))

    def poll_ui_queue(self):
        """Periodically polls thread-safe queue for UI updates."""
        try:
            while True:
                item = self.ui_queue.get_nowait()
                msg_type = item[0]
                if msg_type == "log":
                    _, msg, level = item
                    self.txt_log_console.insert("end", msg + "\n")
                    self.txt_log_console.see("end")
                elif msg_type == "progress":
                    _, metrics = item
                    self.update_progress_ui(metrics)
                elif msg_type == "complete":
                    _, summary = item
                    self.on_organization_finished(summary)
                elif msg_type == "undo_complete":
                    _, res = item
                    self.on_undo_finished(res)
        except queue.Empty:
            pass
        finally:
            self.after(50, self.poll_ui_queue)

    def browse_folder(self):
        chosen = filedialog.askdirectory()
        if chosen:
            self.target_folder_var.set(chosen)
            self.settings_mgr.set("last_folder", chosen)
            self.settings_mgr.add_recent_folder(chosen)

    def open_current_folder(self):
        folder = self.target_folder_var.get().strip()
        if folder and os.path.exists(folder):
            open_folder_in_explorer(folder)
        else:
            messagebox.showwarning("Warning", "Target folder invalid or does not exist.")

    def on_recent_selected(self, chosen: str):
        if chosen and chosen != "Recent Folders..." and os.path.exists(chosen):
            self.target_folder_var.set(chosen)

    def start_organizing(self):
        folder = self.target_folder_var.get().strip()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Error", "Please select a valid folder to organize.")
            return

        self.btn_start.configure(state="disabled")
        self.btn_cancel.configure(state="normal")
        self.status_var.set(self.settings_mgr.get_translation("organizing_status"))

        # Run organization engine in background thread to keep GUI responsive
        threading.Thread(
            target=self._worker_organize,
            args=(folder,),
            daemon=True
        ).start()

    def _worker_organize(self, folder: str):
        def progress_cb(metrics: Dict[str, Any]):
            self.ui_queue.put(("progress", metrics))

        summary = self.engine.organize_directory(folder, progress_callback=progress_cb)
        self.ui_queue.put(("complete", summary))

    def update_progress_ui(self, metrics: Dict[str, Any]):
        if "percentage" in metrics:
            pct = metrics["percentage"]
            self.progressbar.set(pct / 100.0)
            self.progress_percent_var.set(f"{pct:.1f}%")

        if "processed" in metrics and "total" in metrics:
            self.file_counter_var.set(f"{metrics['processed']} / {metrics['total']} Files")

        if "elapsed_seconds" in metrics:
            self.elapsed_time_var.set(format_time(metrics["elapsed_seconds"]))

        if "remaining_seconds" in metrics:
            self.remaining_time_var.set(format_time(metrics["remaining_seconds"]))

        if "status_text" in metrics:
            self.status_var.set(metrics["status_text"])

    def on_organization_finished(self, summary: Dict[str, Any]):
        self.btn_start.configure(state="normal")
        self.btn_cancel.configure(state="disabled")
        self.progressbar.set(1.0)
        self.progress_percent_var.set("100%")
        self.status_var.set(self.settings_mgr.get_translation("complete_status"))

        self.last_summary_stats = summary
        self.last_activity_log = summary.get("activity", [])

        # Update Metric Cards
        self.metric_total_var.set(str(summary.get("total_files", 0)))
        self.metric_moved_var.set(str(summary.get("moved_files", 0)))
        self.metric_dup_var.set(str(summary.get("duplicate_files", 0)))
        self.metric_space_var.set(format_bytes(summary.get("total_size_bytes", 0)))

        # Update Activity Treeview
        self.populate_activity_table(self.last_activity_log)

        # Trigger notification if enabled
        if self.settings_mgr.get("desktop_notifications"):
            msg = f"Organized {summary.get('moved_files', 0)} files into categories."
            show_desktop_notification("Smart File Organizer", msg)

    def populate_activity_table(self, items: List[Dict[str, Any]]):
        for row in self.tree.get_children():
            self.tree.delete(row)

        for item in items:
            self.tree.insert(
                "",
                "end",
                values=(
                    item.get("filename", ""),
                    item.get("category", ""),
                    format_bytes(item.get("size", 0)),
                    item.get("status", ""),
                    item.get("src_path", ""),
                    item.get("dest_path", ""),
                    item.get("timestamp", "")
                )
            )

    def filter_activity_table(self, *args):
        query = self.search_filter_var.get().lower().strip()
        if not query or not self.last_activity_log:
            self.populate_activity_table(self.last_activity_log)
            return

        filtered = [
            item for item in self.last_activity_log
            if query in item.get("filename", "").lower() or query in item.get("category", "").lower()
        ]
        self.populate_activity_table(filtered)

    def on_activity_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item_vals = self.tree.item(selected[0], "values")
        if not item_vals:
            return

        # Show file preview popup
        file_path = item_vals[5] or item_vals[4]
        preview_data = get_file_preview(file_path)
        
        popup = ctk.CTkToplevel(self)
        popup.title("File Preview & Properties")
        popup.geometry("550x400")

        ctk.CTkLabel(popup, text=f"File: {preview_data.get('filename')}", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(popup, text=f"Size: {preview_data.get('size')} | Type: {preview_data.get('extension')}").pack(anchor="w", padx=20, pady=(0, 10))

        if preview_data.get("preview_text"):
            tb = ctk.CTkTextbox(popup, font=ctk.CTkFont(family="Consolas", size=11))
            tb.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            tb.insert("1.0", preview_data["preview_text"])
        else:
            ctk.CTkLabel(popup, text="[Binary or Non-Text File - Preview Unavailable]", text_color="gray60").pack(expand=True)

    def undo_last_move(self):
        folder = self.target_folder_var.get().strip()
        if not messagebox.askyesno("Confirm Undo", "Are you sure you want to restore moved files from the last session?"):
            return

        threading.Thread(
            target=self._worker_undo,
            args=(folder,),
            daemon=True
        ).start()

    def _worker_undo(self, folder: str):
        res = self.undo_mgr.undo_last_transaction(target_folder=folder)
        self.ui_queue.put(("undo_complete", res))

    def on_undo_finished(self, res: Dict[str, Any]):
        restored = res.get("restored_count", 0)
        messagebox.showinfo("Undo Complete", f"Successfully restored {restored} files back to original paths.")
        self.status_var.set(f"Undo Complete: Restored {restored} files.")

    def cancel_organization(self):
        self.engine.cancel_requested = True
        self.status_var.set("Cancelling organization process...")

    def run_batch_rename(self):
        folder = self.target_folder_var.get().strip()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Error", "Please select a valid folder for batch renaming.")
            return

        prefix = self.entry_prefix.get()
        suffix = self.entry_suffix.get()
        find_str = self.entry_find.get()
        replace_str = self.entry_replace.get()
        digits = int(self.spin_digits.get())

        results = self.engine.batch_rename_files(
            folder_path=folder,
            prefix=prefix,
            suffix=suffix,
            find_str=find_str,
            replace_str=replace_str,
            number_digits=digits
        )

        self.txt_batch_results.delete("1.0", "end")
        self.txt_batch_results.insert("end", f"=== Batch Rename Execution ({len(results)} files) ===\n")
        for r in results:
            self.txt_batch_results.insert("end", f"[{r['status']}] {r['old_name']} -> {r['new_name']}\n")

    def export_csv_report(self):
        if not self.last_summary_stats:
            messagebox.showwarning("Warning", "No statistics available to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if path:
            export_statistics_to_csv(self.last_summary_stats, self.last_activity_log, path)
            messagebox.showinfo("Export Successful", f"Statistics exported to: {path}")

    def change_theme(self, new_theme: str):
        ctk.set_appearance_mode(new_theme)
        self.settings_mgr.set("theme_mode", new_theme)

    def change_language(self, new_lang: str):
        self.settings_mgr.set("language", new_lang)
        self.title(self.settings_mgr.get_translation("app_title"))
        messagebox.showinfo("Language Updated", "Language setting updated.")

    def save_settings_from_gui(self):
        self.settings_mgr.set("duplicate_handling", self.opt_dup.get())
        self.settings_mgr.set("remember_last_folder", bool(self.chk_remember.get()))
        self.settings_mgr.set("auto_organize_on_startup", bool(self.chk_auto.get()))
        self.settings_mgr.set("clean_empty_folders", bool(self.chk_clean.get()))
        self.settings_mgr.set("desktop_notifications", bool(self.chk_notify.get()))
        self.settings_mgr.set("recursive_scan", bool(self.chk_recursive.get()))
        messagebox.showinfo("Settings Saved", "Application configuration saved successfully.")

    def clear_logs(self):
        self.txt_log_console.delete("1.0", "end")


if __name__ == "__main__":
    app = SmartFileOrganizerApp()
    app.mainloop()

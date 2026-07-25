# 📁 Smart File Organizer

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()
[![Code Style: PEP8](https://img.shields.io/badge/code%20style-PEP8-green.svg)]()

> A high-performance, cross-platform desktop application built with Python and CustomTkinter that automatically categorizes files, identifies duplicate content via SHA-256 hashing, logs transactional operations, and provides one-click atomic restoration.

---

## 🌟 Key Features

### 📁 Smart Categorization & Folder Scanning
- **One-Click Automated Sorting**: Scans directories and sorts files into clear category folders (`Images`, `Videos`, `Audio`, `Documents`, `PDFs`, `Archives`, `Executables`, `Code Files`, `Spreadsheets`, `Presentations`, `Others`).
- **Scalable Architecture**: Uses `os.scandir` generators and non-blocking multi-threading, capable of processing **50,000+ files** without freezing the GUI.
- **Custom Rules Builder**: Define custom sorting criteria based on filename patterns, regex matches, extension filters, or file size thresholds (e.g. move files >100MB to a `Large_Files` directory).

### 🔍 SHA-256 Duplicate File Detection
- **Multi-Tier Hashing**: Optimizes duplicate detection using a 3-stage process (Size Grouping $\rightarrow$ 64KB Partial Hash $\rightarrow$ Full SHA-256 Hash) to eliminate unnecessary I/O.
- **Duplicate Action Modes**: Choose whether to **Skip**, **Delete**, or **Move** duplicates to a dedicated `_Duplicates` directory.

### ↩️ Transactional Undo & Restoration
- **Atomic Operations**: All file transfers record transactional metadata in JSON logs.
- **One-Click Restore**: Easily restore moved files back to their exact original locations and remove any empty folders created during organization.

### 📊 Live Analytics & Embedded Charts
- **Interactive Visualizations**: Integrated Matplotlib pie and bar charts display real-time storage distribution and file counts per category.
- **CSV Exporting**: Export detailed activity reports and summary metrics to `.csv` format.

### ⚙️ Portfolio & Commercial UX
- **Modern Dark & Light Themes**: Powered by CustomTkinter with dynamic theme switching and responsive layouts.
- **Multi-Language Support**: Complete interface localized in English, Spanish, French, German, and Chinese.
- **Real-Time Logs Console**: Searchable, color-coded live log stream for debugging and activity auditing.
- **Batch File Renamer**: Built-in tool for applying custom prefixes, suffixes, string replacements, and zero-padded sequential numbering to file batches.
- **File Previewer**: Double-click any activity row to inspect file metadata or read text contents directly within the GUI.

---

## 🎨 UI Preview

![Smart File Organizer App Preview](assets/screenshots/app_preview.png)

---

## 🏗️ Project Architecture

```
smart-file-organizer/
│
├── app.py                  # Main CustomTkinter GUI application & tab navigation
├── organizer.py            # Core organization engine & multi-threaded file scanner
├── duplicate_detector.py   # Multi-tier SHA-256 duplicate detection engine
├── undo_manager.py         # Transactional JSON history & atomic file restoration engine
├── logger.py               # Centralized logging module with UI queue streaming
├── settings.py             # Settings manager for settings.json & translations
├── utils.py                # OS folder opener, file preview, notifications & CSV export
├── requirements.txt        # Third-party Python dependencies
├── settings.json           # Default user configuration storage
├── README.md               # Complete repository documentation
├── LICENSE                 # MIT License
├── .gitignore              # Standard Python git ignore rules
├── assets/
│   ├── icons/              # High-resolution application PNG icons
│   └── screenshots/        # UI screenshots and visual assets
└── logs/
    └── app.log             # Application log file
```

---

## ⚡ Quick Start & Installation

### Prerequisites
- Python 3.12 or higher installed.

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/smart-file-organizer.git
cd smart-file-organizer
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Application
```bash
python app.py
```

### 4. Run Automated Test Suite
```bash
python test_organizer.py
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + O` | Browse target folder |
| `Ctrl + R` | Start organizing files |
| `Ctrl + Z` | Undo last transaction |

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author & Contributions

Built as a production-quality portfolio desktop application demonstrating modern Python GUI architecture, multi-threaded worker patterns, and clean modular software design.

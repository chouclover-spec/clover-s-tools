# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**ReIcon** is a Windows desktop application (Python/tkinter) for customizing folder and shortcut icons using PNG images. It converts PNG → ICO and applies icons via Windows-specific APIs.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run
python app.py
```

No build step required. The app is a single file (`app.py`, ~503 lines).

## Dependencies

- `Pillow>=10.0.0` — PNG→ICO conversion
- `tkinterdnd2>=0.3.0` — drag-and-drop (optional; degrades gracefully if missing)
- `pywin32>=306` — Windows COM API for `.lnk` shortcut editing (optional; degrades gracefully)

## Architecture

Everything lives in `app.py`. The structure is:

**Core functions (top of file):**
- `png_to_ico(png_path, ico_path)` — converts PNG to multi-size ICO (256, 128, 64, 48, 32, 16px)
- `apply_folder_icon(folder, ico_path)` / `restore_folder_icon(folder)` — writes `desktop.ini` + sets folder attributes + calls `SHChangeNotify`
- `apply_shortcut_icon(lnk_path, ico_path)` / `restore_shortcut_icon(lnk_path)` — uses pywin32 COM to modify `.lnk` files

**`ReIconApp` class (main GUI):**
- `_setup_styles()` — dark Catppuccin-inspired theme (colors defined as module-level constants: `BG`, `SURFACE`, `ACCENT`, etc.)
- `_build_ui()` — two-panel layout: left = PNG picker/preview, right = target list (ttk.Treeview)
- `_targets` dict — `{path: "folder"|"shortcut"}` stores selected targets
- Apply/restore actions iterate `_targets` and call the core functions above

**`main()` function:** initializes `TkinterDnD` root (or plain `Tk` if unavailable), loads `ReIcon.ico`, starts event loop.

**`resource_path(relative)`** — resolves paths for both dev and PyInstaller frozen builds (`sys._MEIPASS`).

## Windows-Specific Notes

- Folder icons use `desktop.ini` (hidden/system) + folder `SYSTEM` attribute
- Shell refresh uses `ctypes.windll.shell32.SHChangeNotify(0x8000000, 0, None, None)`
- Shortcut editing requires `win32com.client` (pywin32); the feature is disabled if not installed
- Must run on Windows; Linux/macOS will fail at ctypes/pywin32 calls

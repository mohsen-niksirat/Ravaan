# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

block_cipher = None

repo_dir = Path(SPECPATH).resolve()
data_files = [
    (str(repo_dir / "ravan" / "data" / "words_en.txt"), "ravan/data"),
    (str(repo_dir / "ravan" / "data" / "words_fa.txt"), "ravan/data"),
    (str(repo_dir / "ravan" / "data" / "icon.ico"), "ravan/data"),
]

hidden_imports = [
    "comtypes",
    "comtypes.client",
    "comtypes.gen",
    "pystray",
    "pystray._win32",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
]

a = Analysis(
    ["ravan/__main__.py"],
    pathex=[str(repo_dir)],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Ravaan",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(repo_dir / "ravan" / "data" / "icon.ico"),
)

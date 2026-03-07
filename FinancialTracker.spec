# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Financial Tracker — Portable Windows build.

Build with:
    pyinstaller FinancialTracker.spec --noconfirm

Output:
    dist/FinancialTracker/
        FinancialTracker.exe   ← double-click to launch
        _internal/             ← bundled Python runtime, assets, styles
    data/                      ← created on first run, next to the .exe
"""

import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

# ── Collect ALL files for packages that use Rust/C extensions ─────────────────
# collect_all() captures: datas (fonts/styles/etc), binaries (.pyd/.dll),
# AND hidden imports (submodules that static analysis misses).

datas_mpl,    binaries_mpl,    hiddenimports_mpl    = collect_all("matplotlib")
datas_crypto, binaries_crypto, hiddenimports_crypto = collect_all("cryptography")
datas_bcrypt, binaries_bcrypt, hiddenimports_bcrypt = collect_all("bcrypt")

# ── App data files (read-only assets shipped with the app) ────────────────────
_here = SPECPATH   # directory of this .spec file (the repo root)

app_datas = [
    # Bundle the entire assets/ folder (icons + dark_theme.qss)
    (os.path.join(_here, "assets"), "assets"),
]

# Bundle templates/ only if it contains files
_templates = os.path.join(_here, "templates")
if os.path.isdir(_templates) and os.listdir(_templates):
    app_datas.append((_templates, "templates"))

# Merge all datas
all_datas    = app_datas + datas_mpl + datas_crypto + datas_bcrypt
all_binaries = binaries_mpl + binaries_crypto + binaries_bcrypt

# ── App icon (optional — silently skipped if the file is missing) ─────────────
_icon = os.path.join(_here, "assets", "icons", "app_icon.ico")
_icon = _icon if os.path.isfile(_icon) else None

# ── Hidden imports ─────────────────────────────────────────────────────────────
extra_hidden = [
    # PyQt6
    "PyQt6.QtPrintSupport",
    "PyQt6.sip",
    # matplotlib Qt backend (belt-and-suspenders alongside collect_all)
    "matplotlib.backends.backend_qtagg",
    "matplotlib.backends.backend_qt",
    "matplotlib.backends.backend_agg",
    # openpyxl internals sometimes missed by the hook
    "openpyxl.cell._writer",
    "openpyxl.styles.stylesheet",
    # pandas / numpy internals
    "pandas._libs.tslibs.timedeltas",
    "pandas._libs.tslibs.np_datetime",
    "pandas._libs.tslibs.nattype",
    "pandas._libs.missing",
    # cryptography (belt-and-suspenders alongside collect_all)
    "cryptography.hazmat.primitives.kdf.pbkdf2",
    "cryptography.hazmat.primitives.hashes",
    "cryptography.hazmat.primitives.ciphers",
    "cryptography.hazmat.primitives.ciphers.aead",
    "cryptography.hazmat.backends.openssl.backend",
    "cryptography.hazmat.bindings._rust",
    # bcrypt
    "bcrypt",
    "_cffi_backend",
]

all_hidden = hiddenimports_mpl + hiddenimports_crypto + hiddenimports_bcrypt + extra_hidden

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[_here],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "_tkinter",
        # NOTE: do NOT exclude unittest — pyparsing.testing imports it at the
        # top level, and pyparsing is pulled in by matplotlib.rcsetup.
        "email.mime",   # saves ~1 MB
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FinancialTracker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # no black console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FinancialTracker",
)

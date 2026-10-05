# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for SurveySentenceGenerator.exe, with the same options as
# build.py. build.py is the usual route (it makes a clean venv first); use this
# when you already have a venv with the packages installed:
#
#     pyinstaller --clean SurveySentenceGenerator.spec
#
# Output: dist/SurveySentenceGenerator.exe
import os

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

ROOT = SPECPATH
ICON = os.path.join(ROOT, "treez.ico")

datas = [(ICON, ".")]
binaries = []
hiddenimports = [
    "openai",
    "openai.resources",
    "openai.resources.chat",
    "openai.resources.chat.completions",
    "httpx",
    "anyio",
    "qrcode",
    "qrcode.image.base",
    "qrcode.image.pure",
]
hiddenimports += collect_submodules("qrcode")

qt_datas, qt_binaries, qt_hidden = collect_all("PySide6")
datas += qt_datas
binaries += qt_binaries
hiddenimports += qt_hidden

datas += collect_data_files("certifi")


a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SurveySentenceGenerator',
    icon=[ICON],
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
)

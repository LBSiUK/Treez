"""
Build script — compiles main.py into a standalone Windows executable.
Run with: python build.py

Output: dist/SurveySentenceGenerator.exe
(On macOS/Linux it builds a native binary instead, handy for checking the packaging.)
"""
import subprocess
import sys
import os
import venv

IS_WINDOWS = sys.platform == "win32"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(os.environ.get("TEMP", os.path.join(BASE_DIR, "_tmp")), "SurveyGenBuild")
VENV_DIR = os.path.join(TEMP_DIR, "venv")
if IS_WINDOWS:
    VENV_PY = os.path.join(VENV_DIR, "Scripts", "python.exe")
else:
    VENV_PY = os.path.join(VENV_DIR, "bin", "python")

ICON     = os.path.join(BASE_DIR, "treez.ico")
ADD_DATA = f"{ICON}{os.pathsep}."   # "icon;." on Windows

PACKAGES = [
    "pyinstaller",
    "pyside6",
    "pyautogui",
    "pyperclip",
    "openai",
    "qrcode",
]
if not IS_WINDOWS:
    PACKAGES.append("pillow")   # PyInstaller needs it to convert the .ico icon

# ── 1. Create a clean venv ────────────────────────────────────────────────────
print("Creating clean virtual environment...")
venv.create(VENV_DIR, with_pip=True, clear=True)

# ── 2. Install only what the app needs ───────────────────────────────────────
print("Installing packages:", ", ".join(PACKAGES))
subprocess.check_call([VENV_PY, "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
subprocess.check_call([VENV_PY, "-m", "pip", "install", "--quiet"] + PACKAGES)

# ── 3. Run PyInstaller from inside the venv ───────────────────────────────────
cmd = [
    VENV_PY, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--clean",
    "--name", "SurveySentenceGenerator",
    "--icon", ICON,
    "--add-data", ADD_DATA,
    "--hidden-import", "openai",
    "--hidden-import", "openai.resources",
    "--hidden-import", "openai.resources.chat",
    "--hidden-import", "openai.resources.chat.completions",
    "--hidden-import", "httpx",
    "--hidden-import", "anyio",
    "--hidden-import", "qrcode",
    "--hidden-import", "qrcode.image.base",
    "--hidden-import", "qrcode.image.pure",
    "--collect-submodules", "qrcode",
    "--collect-all", "PySide6",
    "--collect-data", "certifi",
    "--distpath", os.path.join(BASE_DIR, "dist"),
    "--workpath", os.path.join(TEMP_DIR, "build"),
    "--specpath", TEMP_DIR,
    os.path.join(BASE_DIR, "main.py"),
]

print("Building executable...")
result = subprocess.run(cmd, cwd=BASE_DIR)

if result.returncode == 0:
    exe_name = "SurveySentenceGenerator.exe" if IS_WINDOWS else "SurveySentenceGenerator"
    exe = os.path.join(BASE_DIR, "dist", exe_name)
    print(f"\nDone! Executable at:\n  {exe}")
    print("(phrases, settings, and logs are stored automatically in %APPDATA%)")
else:
    print("\nBuild failed — see output above for details.")
    sys.exit(1)

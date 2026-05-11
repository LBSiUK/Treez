"""
Build script — compiles main.py into a standalone Windows executable.
Run with: python build.py

Output: dist/SurveySentenceGenerator.exe
"""
import subprocess
import sys
import os
import venv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(os.environ.get("TEMP", os.path.join(BASE_DIR, "_tmp")), "SurveyGenBuild")
VENV_DIR = os.path.join(TEMP_DIR, "venv")
VENV_PY  = os.path.join(VENV_DIR, "Scripts", "python.exe")

ICON     = os.path.join(BASE_DIR, "treez.ico")
ADD_DATA = f"{ICON};."

PACKAGES = [
    "pyinstaller",
    "pyautogui",
    "pyperclip",
    "openai",
]

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
    "--collect-data", "certifi",
    "--distpath", os.path.join(BASE_DIR, "dist"),
    "--workpath", os.path.join(TEMP_DIR, "build"),
    "--specpath", TEMP_DIR,
    os.path.join(BASE_DIR, "main.py"),
]

print("Building executable...")
result = subprocess.run(cmd, cwd=BASE_DIR)

if result.returncode == 0:
    exe = os.path.join(BASE_DIR, "dist", "SurveySentenceGenerator.exe")
    print(f"\nDone! Executable at:\n  {exe}")
    print("(phrases, settings, and logs are stored automatically in %APPDATA%)")
else:
    print("\nBuild failed — see output above for details.")
    sys.exit(1)

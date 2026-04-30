from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent
APP_PATH = BASE_DIR / "app.py"

subprocess.run([
    sys.executable,
    "-m",
    "streamlit",
    "run",
    str(APP_PATH),
    "--server.headless=false"
])

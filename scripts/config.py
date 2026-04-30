from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"

def load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"No existe config.json en: {CONFIG_PATH}")

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

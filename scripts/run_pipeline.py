from pathlib import Path
import subprocess
import sys

BASE_DIR = Path(__file__).resolve().parent.parent

STEPS = [
    "01_transcribe.py",
    "02_detect_clips.py",
    "03_cut_clips.py",
]

def run_step(script_name: str):
    script_path = BASE_DIR / "scripts" / script_name

    print("\n" + "=" * 70)
    print(f"Ejecutando: {script_name}")
    print("=" * 70)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=BASE_DIR
    )

    if result.returncode != 0:
        raise RuntimeError(f"Falló el paso: {script_name}")

def main():
    for step in STEPS:
        run_step(step)

    print("\nPipeline completado.")
    print("Revisa los clips en:")
    print(BASE_DIR / "output" / "raw_clips")

if __name__ == "__main__":
    main()
from pathlib import Path
import subprocess
import sys
import re

from config import load_config

BASE_DIR = Path(__file__).resolve().parent.parent

def slugify(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9_-]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")

def run_step(args):
    print("\n" + "=" * 70)
    print("Ejecutando:", " ".join(str(a) for a in args))
    print("=" * 70)

    result = subprocess.run(args, cwd=BASE_DIR)

    if result.returncode != 0:
        raise RuntimeError(f"Falló el paso: {' '.join(str(a) for a in args)}")

def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("python scripts/run_pipeline.py input/streams/video.mp4")
        sys.exit(1)

    video_path = (BASE_DIR / sys.argv[1]).resolve()

    if not video_path.exists():
        raise FileNotFoundError(f"No existe el video: {video_path}")

    video_name = slugify(video_path.stem)
    output_dir = BASE_DIR / "output" / video_name
    output_dir.mkdir(parents=True, exist_ok=True)

    python = sys.executable
    config = load_config()
    audio_config = config.get("audio", {})

    run_step([
        python,
        "scripts/transcribe.py",
        str(video_path),
        str(output_dir)
    ])

    if audio_config.get("enabled", True):
        run_step([
            python,
            "scripts/analyze_audio.py",
            str(video_path),
            str(output_dir)
        ])

    run_step([
        python,
        "scripts/detect_clips.py",
        str(output_dir)
    ])

    run_step([
        python,
        "scripts/cut_clips.py",
        str(video_path),
        str(output_dir)
    ])

    print("\nPipeline completado.")
    print("Output:")
    print(output_dir)

if __name__ == "__main__":
    main()

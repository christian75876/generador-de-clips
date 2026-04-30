from pathlib import Path
import json
import subprocess

BASE_DIR = Path(__file__).resolve().parent.parent

VIDEO_PATH = BASE_DIR / "input" / "streams" / "video.mp4"
CANDIDATES_PATH = BASE_DIR / "output" / "candidates" / "video_candidates.json"
OUTPUT_DIR = BASE_DIR / "output" / "raw_clips"

PADDING_START = 0
PADDING_END = 0
MAX_CLIPS = 10

def run_command(command):
    print(" ".join(command))
    subprocess.run(command, check=True)

def main():
    if not VIDEO_PATH.exists():
        raise FileNotFoundError(f"No existe el video: {VIDEO_PATH}")

    if not CANDIDATES_PATH.exists():
        raise FileNotFoundError(f"No existe candidates: {CANDIDATES_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:MAX_CLIPS]

    for index, clip in enumerate(candidates, start=1):
        start = max(0, float(clip["start"]) - PADDING_START)
        end = float(clip["end"]) + PADDING_END
        duration = end - start

        output_file = OUTPUT_DIR / f"clip_{index:03d}_score_{clip['score']}.mp4"

        command = [
            "ffmpeg",
            "-y",
            "-ss", str(start),
            "-i", str(VIDEO_PATH),
            "-t", str(duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "veryfast",
            "-crf", "23",
            str(output_file),
        ]

        print(f"\nCortando clip {index}: {output_file.name}")
        print(f"Inicio: {start}s | Duración: {duration}s")
        run_command(command)

    print("\nClips generados en:")
    print(OUTPUT_DIR)

if __name__ == "__main__":
    main()
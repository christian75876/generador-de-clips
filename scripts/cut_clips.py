from pathlib import Path
import json
import subprocess
import sys

PADDING_START = 0
PADDING_END = 0
MAX_CLIPS = 10

def run_command(command):
    print(" ".join(command))
    subprocess.run(command, check=True)

def main():
    if len(sys.argv) < 3:
        print("Uso:")
        print("python scripts/cut_clips.py <video_path> <output_dir>")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    candidates_path = output_dir / "candidates.json"
    clips_dir = output_dir / "raw_clips"

    if not video_path.exists():
        raise FileNotFoundError(f"No existe el video: {video_path}")

    if not candidates_path.exists():
        raise FileNotFoundError(f"No existe candidates: {candidates_path}")

    clips_dir.mkdir(parents=True, exist_ok=True)

    with open(candidates_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:MAX_CLIPS]

    for index, clip in enumerate(candidates, start=1):
        start = max(0, float(clip["start"]) - PADDING_START)
        end = float(clip["end"]) + PADDING_END
        duration = end - start

        output_file = clips_dir / f"clip_{index:03d}_score_{clip['score']}.mp4"

        command = [
            "ffmpeg",
            "-y",
            "-ss", str(start),
            "-i", str(video_path),
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
    print(clips_dir)

if __name__ == "__main__":
    main()
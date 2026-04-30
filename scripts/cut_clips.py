from pathlib import Path
import json
import subprocess
import sys

from config import load_config

def format_time(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h > 0:
        return f"{h:02d}-{m:02d}-{s:02d}"

    return f"{m:02d}-{s:02d}"

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

    config = load_config()
    clips_config = config["clips"]

    padding_start = clips_config["padding_start"]
    padding_end = clips_config["padding_end"]
    max_clips = clips_config["max_clips"]

    if not video_path.exists():
        raise FileNotFoundError(f"No existe el video: {video_path}")

    if not candidates_path.exists():
        raise FileNotFoundError(f"No existe candidates: {candidates_path}")

    clips_dir.mkdir(parents=True, exist_ok=True)

    with open(candidates_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:max_clips]

    for index, clip in enumerate(candidates, start=1):
        start = max(0, float(clip.get("cut_start", clip["start"])) - padding_start)
        end = float(clip.get("cut_end", clip["end"])) + padding_end
        duration = end - start

        start_str = format_time(start)
        end_str = format_time(end)

        output_file = clips_dir / (
            f"clip_{index:03d}_{start_str}_to_{end_str}_score_{clip['score']}.mp4"
        )

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

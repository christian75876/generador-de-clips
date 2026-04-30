from pathlib import Path
import json
import sys
from faster_whisper import WhisperModel

from config import load_config

def main():
    if len(sys.argv) < 3:
        print("Uso:")
        print("python scripts/transcribe.py <video_path> <output_dir>")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if not video_path.exists():
        raise FileNotFoundError(f"No existe el video: {video_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "transcript.json"

    config = load_config()
    whisper_config = config["whisper"]

    print(f"Transcribiendo: {video_path}")
    print(f"Output: {output_file}")

    model = WhisperModel(
        whisper_config["model_size"],
        device=whisper_config["device"],
        compute_type=whisper_config["compute_type"]
    )

    segments, info = model.transcribe(
        str(video_path),
        language=whisper_config["language"],
        vad_filter=whisper_config["vad_filter"],
        beam_size=whisper_config["beam_size"]
    )

    transcript = []

    for segment in segments:
        item = {
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip()
        }

        transcript.append(item)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)

    print(f"Transcripción completada: {len(transcript)} segmentos")

if __name__ == "__main__":
    main()

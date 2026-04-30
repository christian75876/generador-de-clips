from pathlib import Path
import json
from faster_whisper import WhisperModel

BASE_DIR = Path(__file__).resolve().parent.parent

VIDEO_PATH = BASE_DIR / "input" / "streams" / "video.mp4"
OUTPUT_PATH = BASE_DIR / "output" / "transcripts" / "video_transcript.json"

MODEL_SIZE = "tiny"  # tiny, base, small, medium, large-v3
LANGUAGE = "es"


def main():
    if not VIDEO_PATH.exists():
        raise FileNotFoundError(f"No existe el video: {VIDEO_PATH}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print(f"Transcribiendo: {VIDEO_PATH}")
    print(f"Modelo: {MODEL_SIZE}")

    model = WhisperModel(
        MODEL_SIZE,
        device="cpu",
        compute_type="int8"
    )

    segments, info = model.transcribe(
        str(VIDEO_PATH),
        language=LANGUAGE,
        vad_filter=True,
        beam_size=5
    )

    transcript = []

    for segment in segments:
        item = {
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip()
        }

        transcript.append(item)

        print(
            f"[{item['start']}s - {item['end']}s] {item['text']}"
        )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)

    print("\nTranscripción completada.")
    print(f"Archivo generado: {OUTPUT_PATH}")
    print(f"Segmentos detectados: {len(transcript)}")

if __name__ == "__main__":
    main()

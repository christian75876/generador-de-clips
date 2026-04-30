from pathlib import Path
import json
import re

BASE_DIR = Path(__file__).resolve().parent.parent

TRANSCRIPT_PATH = BASE_DIR / "output" / "transcripts" / "video_transcript.json"
OUTPUT_PATH = BASE_DIR / "output" / "candidates" / "video_candidates.json"

MIN_CLIP_DURATION = 8
MAX_CLIP_DURATION = 20

KEYWORDS = [
    "no puede ser",
    "qué",
    "como",
    "increíble",
    "brutal",
    "espera",
    "mira",
    "ojo",
    "wow",
    "jajaja",
    "me mató",
    "literal",
    "bro",
    "uy",
    "epa",
    "wtf",
    "importante",
    "esto es",
    "la verdad",
    "te digo",
    "escucha",
]

def score_text(text: str) -> int:
    text_lower = text.lower()
    score = 0

    # Palabras clave
    for keyword in KEYWORDS:
        if keyword in text_lower:
            score += 3

    # Preguntas suelen ser buenos hooks
    if "?" in text:
        score += 2

    # Exclamaciones
    if "!" in text:
        score += 2

    # Risa o reacción
    if re.search(r"\b(ja|jaja|jajaja|jeje|lol)\b", text_lower):
        score += 3

    # Frases largas suelen tener más contexto
    words = text.split()
    if len(words) >= 25:
        score += 2

    if len(words) >= 45:
        score += 3

    return score

def main():
    if not TRANSCRIPT_PATH.exists():
        raise FileNotFoundError(f"No existe la transcripción: {TRANSCRIPT_PATH}")

    with open(TRANSCRIPT_PATH, "r", encoding="utf-8") as f:
        segments = json.load(f)

    candidates = []

    for i, segment in enumerate(segments):
        start = segment["start"]
        end = segment["end"]
        text_parts = [segment["text"]]

        j = i + 1

        # Agrupar segmentos hasta formar un clip de duración útil
        while j < len(segments) and (end - start) < MIN_CLIP_DURATION:
            text_parts.append(segments[j]["text"])
            end = segments[j]["end"]
            j += 1

        # Extender un poco si no pasa el máximo
        while j < len(segments) and (end - start) < MAX_CLIP_DURATION:
            next_text = segments[j]["text"]
            combined_text = " ".join(text_parts + [next_text])

            if score_text(combined_text) >= score_text(" ".join(text_parts)):
                text_parts.append(next_text)
                end = segments[j]["end"]
                j += 1
            else:
                break

        clip_text = " ".join(text_parts)
        duration = end - start
        score = score_text(clip_text)

        if duration >= MIN_CLIP_DURATION and score >= 3:
            candidates.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(duration, 2),
                "score": score,
                "title": generate_title(clip_text),
                "reason": generate_reason(score, clip_text),
                "text": clip_text
            })

    # Quitar duplicados parecidos por timestamp
    unique_candidates = []
    used_ranges = []

    for candidate in sorted(candidates, key=lambda x: x["score"], reverse=True):
        overlaps = False

        for used in used_ranges:
            if candidate["start"] < used["end"] and candidate["end"] > used["start"]:
                overlaps = True
                break

        if not overlaps:
            unique_candidates.append(candidate)
            used_ranges.append({
                "start": candidate["start"],
                "end": candidate["end"]
            })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(unique_candidates, f, ensure_ascii=False, indent=2)

    print(f"Candidatos generados: {len(unique_candidates)}")
    print(f"Archivo generado: {OUTPUT_PATH}")

    for idx, c in enumerate(unique_candidates[:10], start=1):
        print("\n" + "-" * 60)
        print(f"Clip #{idx}")
        print(f"Inicio: {c['start']}s")
        print(f"Fin: {c['end']}s")
        print(f"Duración: {c['duration']}s")
        print(f"Score: {c['score']}")
        print(f"Título: {c['title']}")
        print(f"Razón: {c['reason']}")
        print(f"Texto: {c['text'][:300]}...")

def generate_title(text: str) -> str:
    words = text.strip().split()
    title = " ".join(words[:10])

    if len(words) > 10:
        title += "..."

    return title

def generate_reason(score: int, text: str) -> str:
    reasons = []

    text_lower = text.lower()

    if any(k in text_lower for k in KEYWORDS):
        reasons.append("contiene palabras o frases de reacción")

    if "?" in text:
        reasons.append("incluye una pregunta útil como hook")

    if "!" in text:
        reasons.append("incluye énfasis o emoción")

    if len(text.split()) >= 25:
        reasons.append("tiene suficiente contexto para un clip")

    if not reasons:
        reasons.append("tiene potencial por estructura y duración")

    return ", ".join(reasons)

if __name__ == "__main__":
    main()
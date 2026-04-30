from pathlib import Path
import json
import re
import sys

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

    for keyword in KEYWORDS:
        if keyword in text_lower:
            score += 3

    if "?" in text:
        score += 2

    if "!" in text:
        score += 2

    if re.search(r"\b(ja|jaja|jajaja|jeje|lol)\b", text_lower):
        score += 3

    words = text.split()

    if len(words) >= 25:
        score += 2

    if len(words) >= 45:
        score += 3

    return score

def generate_title(text: str) -> str:
    words = text.strip().split()
    title = " ".join(words[:10])

    if len(words) > 10:
        title += "..."

    return title

def generate_reason(text: str) -> str:
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

def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("python scripts/detect_clips.py <output_dir>")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    transcript_path = output_dir / "transcript.json"
    output_path = output_dir / "candidates.json"

    if not transcript_path.exists():
        raise FileNotFoundError(f"No existe la transcripción: {transcript_path}")

    with open(transcript_path, "r", encoding="utf-8") as f:
        segments = json.load(f)

    candidates = []

    for i, segment in enumerate(segments):
        start = float(segment["start"])
        end = float(segment["end"])
        text_parts = [segment["text"]]

        j = i + 1

        while j < len(segments) and (end - start) < MIN_CLIP_DURATION:
            text_parts.append(segments[j]["text"])
            end = float(segments[j]["end"])
            j += 1

        while j < len(segments) and (end - start) < MAX_CLIP_DURATION:
            next_text = segments[j]["text"]
            current_text = " ".join(text_parts)
            combined_text = " ".join(text_parts + [next_text])

            if score_text(combined_text) >= score_text(current_text):
                text_parts.append(next_text)
                end = float(segments[j]["end"])
                j += 1
            else:
                break

        duration = end - start

        if duration > MAX_CLIP_DURATION:
            end = start + MAX_CLIP_DURATION
            duration = MAX_CLIP_DURATION

        clip_text = " ".join(text_parts)
        score = score_text(clip_text)

        if duration >= MIN_CLIP_DURATION and score >= 3:
            candidates.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(duration, 2),
                "score": score,
                "title": generate_title(clip_text),
                "reason": generate_reason(clip_text),
                "text": clip_text
            })

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

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(unique_candidates, f, ensure_ascii=False, indent=2)

    print(f"Candidatos generados: {len(unique_candidates)}")
    print(f"Archivo generado: {output_path}")

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

if __name__ == "__main__":
    main()
from pathlib import Path
import json
import re
import sys

from config import load_config

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

CLOSING_PATTERNS = [
    "ya está",
    "listo",
    "eso fue",
    "se acabó",
    "terminó",
    "bueno",
    "ok",
    "vale",
    "siguiente",
    "vamos",
    "continuamos",
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

def is_natural_closing(text: str) -> bool:
    text_lower = text.lower().strip()

    if text_lower.endswith((".", "!", "?")):
        return True

    return any(pattern in text_lower for pattern in CLOSING_PATTERNS)

def should_extend_clip(current_text: str, next_text: str, current_duration: float, ideal_clip_duration: float) -> bool:
    combined_text = f"{current_text} {next_text}".strip()

    current_score = score_text(current_text)
    combined_score = score_text(combined_text)

    if current_duration >= ideal_clip_duration and is_natural_closing(current_text):
        return False

    if combined_score > current_score:
        return True

    if current_duration < ideal_clip_duration:
        return True

    return False

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

    if is_natural_closing(text):
        reasons.append("tiene cierre natural")

    if not reasons:
        reasons.append("tiene potencial por estructura y duración")

    return ", ".join(reasons)

def load_audio_peaks(output_dir: Path):
    audio_path = output_dir / "audio_peaks.json"

    if not audio_path.exists():
        return []

    with open(audio_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    return data.get("peaks", [])

def find_audio_hits(start: float, end: float, audio_peaks, nearby_seconds: float):
    hits = []
    padded_start = start - nearby_seconds
    padded_end = end + nearby_seconds

    for peak in audio_peaks:
        peak_start = float(peak["start"])
        peak_end = float(peak["end"])

        if peak_start <= padded_end and peak_end >= padded_start:
            hits.append(peak)

    return hits

def score_audio_hits(audio_hits, audio_config) -> int:
    if not audio_hits:
        return 0

    score_bonus = audio_config.get("score_bonus", 3)
    max_score_bonus = audio_config.get("max_score_bonus", 8)
    best_audio_score = max(int(hit.get("score", 1)) for hit in audio_hits)
    audio_bonus = score_bonus + best_audio_score - 1

    return min(audio_bonus, max_score_bonus)

def generate_audio_reason(audio_hits) -> str:
    if not audio_hits:
        return ""

    reasons = sorted({hit.get("reason", "pico de audio") for hit in audio_hits})
    return "coincide con audio destacado: " + "; ".join(reasons[:2])

def adjust_cut_bounds(start: float, end: float, audio_hits, audio_config, min_duration: float, max_duration: float):
    if not audio_config.get("natural_boundaries", True) or not audio_hits:
        return start, end, ""

    alignment_seconds = audio_config.get("boundary_alignment_seconds", 4)
    max_shift = audio_config.get("max_boundary_shift", 5)
    cut_start = start
    cut_end = end
    reasons = []

    start_hits = []
    end_hits = []

    for hit in audio_hits:
        hit_start = float(hit["start"])
        hit_end = float(hit["end"])
        natural_start = float(hit.get("natural_start", hit_start))
        natural_end = float(hit.get("natural_end", hit_end))

        if hit_start <= start + alignment_seconds and abs(natural_start - start) <= max_shift:
            start_hits.append((natural_start, hit))

        if hit_end >= end - alignment_seconds and abs(natural_end - end) <= max_shift:
            end_hits.append((natural_end, hit))

    if start_hits:
        cut_start, hit = min(start_hits, key=lambda item: item[0])
        reasons.append(hit.get("boundary_reason", "inicio natural"))

    if end_hits:
        cut_end, hit = max(end_hits, key=lambda item: item[0])
        reasons.append(hit.get("boundary_reason", "cierre natural"))

    if cut_end - cut_start < min_duration or cut_end - cut_start > max_duration:
        return start, end, ""

    reason = "; ".join(sorted(set(reasons)))
    return cut_start, cut_end, reason

def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print("python scripts/detect_clips.py <output_dir>")
        sys.exit(1)

    output_dir = Path(sys.argv[1])
    transcript_path = output_dir / "transcript.json"
    output_path = output_dir / "candidates.json"

    config = load_config()
    clips_config = config["clips"]
    audio_config = config.get("audio", {})

    min_clip_duration = clips_config["min_duration"]
    max_clip_duration = clips_config["max_duration"]
    ideal_clip_duration = clips_config["ideal_duration"]
    min_score = clips_config["min_score"]
    nearby_seconds = audio_config.get("nearby_seconds", 0)

    if not transcript_path.exists():
        raise FileNotFoundError(f"No existe la transcripción: {transcript_path}")

    with open(transcript_path, "r", encoding="utf-8") as f:
        segments = json.load(f)

    audio_peaks = load_audio_peaks(output_dir) if audio_config.get("enabled", True) else []
    candidates = []

    for i, segment in enumerate(segments):
        start = float(segment["start"])
        end = float(segment["end"])
        text_parts = [segment["text"]]

        j = i + 1

        while j < len(segments) and (end - start) < min_clip_duration:
            text_parts.append(segments[j]["text"])
            end = float(segments[j]["end"])
            j += 1

        while j < len(segments) and (end - start) < max_clip_duration:
            current_text = " ".join(text_parts)
            next_text = segments[j]["text"]
            current_duration = end - start

            if should_extend_clip(current_text, next_text, current_duration, ideal_clip_duration):
                text_parts.append(next_text)
                end = float(segments[j]["end"])
                j += 1
            else:
                break

        duration = end - start

        if duration > max_clip_duration:
            end = start + max_clip_duration
            duration = max_clip_duration

        clip_text = " ".join(text_parts)
        text_score = score_text(clip_text)
        audio_hits = find_audio_hits(start, end, audio_peaks, nearby_seconds)
        audio_score = score_audio_hits(audio_hits, audio_config) if audio_hits else 0
        score = text_score + audio_score
        cut_start, cut_end, boundary_reason = adjust_cut_bounds(
            start,
            end,
            audio_hits,
            audio_config,
            min_clip_duration,
            max_clip_duration,
        )
        cut_duration = cut_end - cut_start

        reason = generate_reason(clip_text)
        audio_reason = generate_audio_reason(audio_hits)

        if audio_reason:
            reason = f"{reason}, {audio_reason}"

        if boundary_reason:
            reason = f"{reason}, corte ajustado por audio: {boundary_reason}"

        if duration >= min_clip_duration and score >= min_score:
            candidates.append({
                "start": round(start, 2),
                "end": round(end, 2),
                "duration": round(duration, 2),
                "cut_start": round(cut_start, 2),
                "cut_end": round(cut_end, 2),
                "cut_duration": round(cut_duration, 2),
                "score": score,
                "text_score": text_score,
                "audio_score": audio_score,
                "boundary_reason": boundary_reason,
                "audio_peaks": [
                    {
                        "start": peak["start"],
                        "end": peak["end"],
                        "natural_start": peak.get("natural_start", peak["start"]),
                        "natural_end": peak.get("natural_end", peak["end"]),
                        "score": peak.get("score", 0),
                        "reason": peak.get("reason", "pico de audio"),
                        "boundary_reason": peak.get("boundary_reason", "")
                    }
                    for peak in audio_hits
                ],
                "title": generate_title(clip_text),
                "reason": reason,
                "text": clip_text
            })

    unique_candidates = []
    used_ranges = []

    for candidate in sorted(candidates, key=lambda x: x["score"], reverse=True):
        overlaps = False
        candidate_start = candidate.get("cut_start", candidate["start"])
        candidate_end = candidate.get("cut_end", candidate["end"])

        for used in used_ranges:
            if candidate_start < used["end"] and candidate_end > used["start"]:
                overlaps = True
                break

        if not overlaps:
            unique_candidates.append(candidate)
            used_ranges.append({
                "start": candidate_start,
                "end": candidate_end
            })

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
        print(f"Corte: {c.get('cut_start', c['start'])}s -> {c.get('cut_end', c['end'])}s")
        print(f"Score: {c['score']}")
        print(f"Título: {c['title']}")
        print(f"Razón: {c['reason']}")
        print(f"Texto: {c['text'][:300]}...")

if __name__ == "__main__":
    main()

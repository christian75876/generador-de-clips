from array import array
from pathlib import Path
import json
import math
import statistics
import subprocess
import sys

from config import load_config

MIN_DB = -90.0
MAX_SAMPLE = 32768.0

def dbfs(value: float) -> float:
    if value <= 0:
        return MIN_DB

    return max(MIN_DB, 20 * math.log10(value / MAX_SAMPLE))

def read_audio_windows(video_path: Path, sample_rate: int, window_seconds: float):
    samples_per_window = max(1, int(sample_rate * window_seconds))
    bytes_per_window = samples_per_window * 2

    command = [
        "ffmpeg",
        "-v", "error",
        "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-f", "s16le",
        "pipe:1",
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if process.stdout is None or process.stderr is None:
        raise RuntimeError("No se pudo iniciar ffmpeg para analizar audio")

    windows = []
    sample_cursor = 0

    while True:
        chunk = process.stdout.read(bytes_per_window)

        if not chunk:
            break

        if len(chunk) % 2:
            chunk = chunk[:-1]

        samples = array("h")
        samples.frombytes(chunk)

        if sys.byteorder != "little":
            samples.byteswap()

        if not samples:
            continue

        peak = max(abs(sample) for sample in samples)
        rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))

        start = sample_cursor / sample_rate
        end = (sample_cursor + len(samples)) / sample_rate
        sample_cursor += len(samples)

        windows.append({
            "start": round(start, 2),
            "end": round(end, 2),
            "rms_db": round(dbfs(rms), 2),
            "peak_db": round(dbfs(peak), 2),
        })

    stderr = process.stderr.read().decode("utf-8", errors="replace").strip()
    returncode = process.wait()

    if returncode != 0:
        raise RuntimeError(f"ffmpeg falló analizando audio: {stderr}")

    return windows

def find_natural_boundaries(segment, windows, audio_config, noise_floor_db: float) -> dict:
    window_seconds = audio_config["window_seconds"]
    search_seconds = audio_config.get("boundary_search_seconds", 4)
    search_windows = max(1, int(search_seconds / window_seconds))
    quiet_threshold_db = max(
        audio_config.get("boundary_silence_db", -38),
        noise_floor_db + audio_config.get("boundary_quiet_offset_db", -4),
    )
    change_db = audio_config.get("boundary_change_db", 6)
    padding_start = audio_config.get("boundary_padding_start", 0.25)
    padding_end = audio_config.get("boundary_padding_end", 0.35)

    start_index = segment["start_index"]
    end_index = segment["end_index"]
    natural_start = segment["start"]
    natural_end = segment["end"]
    start_reason = "inicio del pico"
    end_reason = "fin del pico"

    earliest_index = max(0, start_index - search_windows)

    for index in range(start_index - 1, earliest_index - 1, -1):
        current = windows[index]
        next_window = windows[index + 1] if index + 1 < len(windows) else None

        if current["rms_db"] <= quiet_threshold_db:
            natural_start = current["start"]
            start_reason = "silencio previo"
            break

        if next_window and next_window["rms_db"] - current["rms_db"] >= change_db:
            natural_start = current["start"]
            start_reason = "subida brusca"
            break

    latest_index = min(len(windows) - 1, end_index + search_windows)

    for index in range(end_index + 1, latest_index + 1):
        current = windows[index]
        previous = windows[index - 1]

        if current["rms_db"] <= quiet_threshold_db:
            natural_end = current["end"]
            end_reason = "silencio posterior"
            break

        if previous["rms_db"] - current["rms_db"] >= change_db:
            natural_end = current["end"]
            end_reason = "caida brusca"
            break

    natural_start = max(0, natural_start - padding_start)
    natural_end = min(windows[-1]["end"], natural_end + padding_end)

    if natural_end <= natural_start:
        natural_start = segment["start"]
        natural_end = segment["end"]
        start_reason = "inicio del pico"
        end_reason = "fin del pico"

    return {
        "natural_start": round(natural_start, 2),
        "natural_end": round(natural_end, 2),
        "natural_duration": round(natural_end - natural_start, 2),
        "boundary_reason": f"{start_reason}, {end_reason}",
        "quiet_threshold_db": round(quiet_threshold_db, 2),
    }

def score_audio_segment(segment, windows, audio_config, noise_floor_db: float, rms_threshold: float) -> dict:
    window_seconds = audio_config["window_seconds"]
    silence_before_seconds = audio_config["silence_before_seconds"]
    silence_before_db = audio_config["silence_before_db"]
    reaction_max_duration = audio_config["reaction_max_duration"]
    min_peak_db = audio_config["min_peak_db"]
    strong_relative_db = audio_config["strong_relative_db"]

    start_index = segment["start_index"]
    end_index = segment["end_index"]
    duration = segment["end"] - segment["start"]

    previous_window_count = max(1, int(silence_before_seconds / window_seconds))
    previous_start = max(0, start_index - previous_window_count)
    previous_windows = windows[previous_start:start_index]
    previous_avg_db = (
        sum(window["rms_db"] for window in previous_windows) / len(previous_windows)
        if previous_windows
        else noise_floor_db
    )

    score = 2
    reasons = []

    if segment["max_rms_db"] >= rms_threshold + strong_relative_db:
        score += 2
        reasons.append("energia alta")
    elif segment["max_rms_db"] >= rms_threshold:
        score += 1
        reasons.append("subida de volumen")

    if segment["max_peak_db"] >= min_peak_db:
        score += 1
        reasons.append("pico de volumen")

    if previous_avg_db + silence_before_db <= segment["max_rms_db"]:
        score += 2
        reasons.append("silencio previo")

    if duration <= reaction_max_duration:
        score += 1
        reasons.append("posible reaccion corta")

    if not reasons:
        reasons.append("energia destacada")

    boundaries = find_natural_boundaries(segment, windows, audio_config, noise_floor_db)

    return {
        "start": round(segment["start"], 2),
        "end": round(segment["end"], 2),
        "duration": round(duration, 2),
        "score": score,
        "rms_db": round(segment["max_rms_db"], 2),
        "peak_db": round(segment["max_peak_db"], 2),
        "reason": ", ".join(reasons),
        "previous_avg_db": round(previous_avg_db, 2),
        "window_start": start_index,
        "window_end": end_index,
        **boundaries,
    }

def detect_audio_peaks(windows, audio_config):
    if not windows:
        return [], MIN_DB, MIN_DB

    rms_values = [window["rms_db"] for window in windows]
    noise_floor_db = statistics.median(rms_values)

    rms_threshold = max(
        audio_config["min_rms_db"],
        noise_floor_db + audio_config["relative_rms_db"],
    )

    min_peak_db = audio_config["min_peak_db"]
    merge_gap = audio_config["merge_gap"]
    min_segment_duration = audio_config["min_segment_duration"]
    max_peaks = audio_config["max_peaks"]

    segments = []
    current = None

    for index, window in enumerate(windows):
        is_high_energy = (
            window["rms_db"] >= rms_threshold
            or window["peak_db"] >= min_peak_db
        )

        if not is_high_energy:
            continue

        if current and window["start"] - current["end"] <= merge_gap:
            current["end"] = window["end"]
            current["end_index"] = index
            current["max_rms_db"] = max(current["max_rms_db"], window["rms_db"])
            current["max_peak_db"] = max(current["max_peak_db"], window["peak_db"])
        else:
            if current:
                segments.append(current)

            current = {
                "start": window["start"],
                "end": window["end"],
                "start_index": index,
                "end_index": index,
                "max_rms_db": window["rms_db"],
                "max_peak_db": window["peak_db"],
            }

    if current:
        segments.append(current)

    peaks = []

    for segment in segments:
        if segment["end"] - segment["start"] < min_segment_duration:
            continue

        peaks.append(score_audio_segment(
            segment,
            windows,
            audio_config,
            noise_floor_db,
            rms_threshold,
        ))

    peaks = sorted(
        peaks,
        key=lambda peak: (peak["score"], peak["rms_db"], peak["peak_db"]),
        reverse=True,
    )[:max_peaks]

    return sorted(peaks, key=lambda peak: peak["start"]), noise_floor_db, rms_threshold

def main():
    if len(sys.argv) < 3:
        print("Uso:")
        print("python scripts/analyze_audio.py <video_path> <output_dir>")
        sys.exit(1)

    video_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_path = output_dir / "audio_peaks.json"

    if not video_path.exists():
        raise FileNotFoundError(f"No existe el video: {video_path}")

    config = load_config()
    audio_config = config["audio"]

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Analizando audio: {video_path}")
    print(f"Output: {output_path}")

    if not audio_config.get("enabled", True):
        result = {
            "enabled": False,
            "video": str(video_path),
            "peaks": [],
        }
    else:
        windows = read_audio_windows(
            video_path,
            audio_config["sample_rate"],
            audio_config["window_seconds"],
        )
        peaks, noise_floor_db, rms_threshold = detect_audio_peaks(windows, audio_config)

        result = {
            "enabled": True,
            "video": str(video_path),
            "sample_rate": audio_config["sample_rate"],
            "window_seconds": audio_config["window_seconds"],
            "noise_floor_db": round(noise_floor_db, 2),
            "rms_threshold_db": round(rms_threshold, 2),
            "total_windows": len(windows),
            "peaks": peaks,
        }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Picos de audio detectados: {len(result['peaks'])}")
    print(f"Archivo generado: {output_path}")

    for idx, peak in enumerate(result["peaks"][:10], start=1):
        print("\n" + "-" * 60)
        print(f"Pico #{idx}")
        print(f"Inicio: {peak['start']}s")
        print(f"Fin: {peak['end']}s")
        print(f"Corte natural: {peak['natural_start']}s -> {peak['natural_end']}s")
        print(f"Score audio: {peak['score']}")
        print(f"RMS: {peak['rms_db']} dB | Peak: {peak['peak_db']} dB")
        print(f"Razón: {peak['reason']}")
        print(f"Límite: {peak['boundary_reason']}")

if __name__ == "__main__":
    main()

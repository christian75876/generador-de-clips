from pathlib import Path
import json
import subprocess
import sys
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
INPUT_DIR = BASE_DIR / "input" / "streams"
OUTPUT_DIR = BASE_DIR / "output"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def list_videos():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    return sorted([
        p for p in INPUT_DIR.iterdir()
        if p.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]
    ])


def run_pipeline(video_path: Path):
    command = [
        sys.executable,
        str(BASE_DIR / "scripts" / "run_pipeline.py"),
        str(video_path.relative_to(BASE_DIR))
    ]

    process = subprocess.run(
        command,
        cwd=BASE_DIR,
        capture_output=True,
        text=True
    )

    return process.returncode, process.stdout, process.stderr


# UI
st.set_page_config(page_title="Content Pipeline", layout="wide")

st.title("🎬 Content Pipeline")
st.caption("Detector automático de clips de streams")

config = load_config()
videos = list_videos()

# Sidebar config
st.sidebar.header("Configuración")

st.sidebar.subheader("Clips")
config["clips"]["min_duration"] = st.sidebar.slider(
    "Duración mínima",
    1, 60,
    int(config["clips"]["min_duration"])
)

config["clips"]["max_duration"] = st.sidebar.slider(
    "Duración máxima",
    5, 120,
    int(config["clips"]["max_duration"])
)

config["clips"]["min_score"] = st.sidebar.slider(
    "Score mínimo",
    0, 20,
    int(config["clips"]["min_score"])
)

config["clips"]["max_clips"] = st.sidebar.slider(
    "Máx clips",
    1, 20,
    int(config["clips"]["max_clips"])
)

config["audio"]["enabled"] = st.sidebar.checkbox(
    "Audio inteligente",
    value=config["audio"]["enabled"]
)

if st.sidebar.button("💾 Guardar config"):
    save_config(config)
    st.sidebar.success("Config guardada")

st.divider()

# Video selector
if not videos:
    st.warning("No hay videos en input/streams/")
    selected_video = None
else:
    selected_video = st.selectbox(
        "Selecciona un video",
        videos,
        format_func=lambda x: x.name
    )

# Run button
if st.button("🚀 Procesar video", disabled=not selected_video):

    save_config(config)

    st.info(f"Procesando: {selected_video.name}")

    with st.spinner("Ejecutando pipeline..."):
        code, out, err = run_pipeline(selected_video)

    if code == 0:
        st.success("Pipeline completado")

        output_folder = OUTPUT_DIR / selected_video.stem

        st.subheader("📂 Output")
        st.code(str(output_folder))

        clips_dir = output_folder / "raw_clips"

        if clips_dir.exists():
            clips = sorted(clips_dir.glob("*.mp4"))

            st.subheader(f"🎥 Clips ({len(clips)})")

            for clip in clips[:10]:
                st.video(str(clip))
                st.caption(clip.name)

        st.subheader("📜 Logs")
        st.code(out)

    else:
        st.error("Error en pipeline")

        st.subheader("STDOUT")
        st.code(out)

        st.subheader("STDERR")
        st.code(err)

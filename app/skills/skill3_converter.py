"""
Skill #3 — Media Converter
Downloads and converts YouTube videos to MP3/MP4 via yt-dlp + FFmpeg.
Emits real-time progress via a queue for SSE streaming.
"""

import re
import subprocess
import sys
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Resolve project root so paths work regardless of cwd
_HERE = Path(__file__).resolve().parent.parent.parent  # project root
SESSIONS_DIR = _HERE / "app" / "sessions"
MAX_TIMEOUT  = 900  # 15 minutes

# Local ffmpeg binary (downloaded by setup_ffmpeg.py)
_FFMPEG_LOCAL = _HERE / "bin" / "ffmpeg.exe"

PROGRESS_RE = re.compile(
    r'\[download\]\s+([\d.]+)%\s+of\s+~?\s*([\d.]+\s*\w+)\s+at\s+([\d.]+\s*[\w/]+)\s+ETA\s+([\d:]+)'
)
SAFE_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _ytdlp_cmd() -> list[str]:
    """Return the yt-dlp invocation — PATH binary or python -m fallback."""
    import shutil
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    return [sys.executable, "-m", "yt_dlp"]


def _ffmpeg_args() -> list[str]:
    """Return --ffmpeg-location arg if local binary exists."""
    if _FFMPEG_LOCAL.exists():
        return ["--ffmpeg-location", str(_FFMPEG_LOCAL.parent)]
    import shutil
    if shutil.which("ffmpeg"):
        return []  # use system ffmpeg
    return []  # will fail gracefully with clear error from yt-dlp


def ffmpeg_available() -> bool:
    import shutil
    return _FFMPEG_LOCAL.exists() or bool(shutil.which("ffmpeg"))


def _safe_name(name: str) -> str:
    return SAFE_FILENAME_RE.sub("_", name)


def _session_dir(session_id: str) -> Path:
    d = SESSIONS_DIR / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _build_cmd(video_id, target_format, audio_id, video_id_fmt, output_tmpl, extra_args, fallback_height=None):
    url = f"https://www.youtube.com/watch?v={video_id}"
    base = _ytdlp_cmd()
    ffmpeg = _ffmpeg_args()
    if target_format == "MP3":
        return [
            *base,
            "--format", audio_id or "bestaudio",
            "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0",
            "--embed-thumbnail", "--add-metadata", "--newline",
            *ffmpeg,
            "--output", output_tmpl, *extra_args, url,
        ]
    else:
        h = fallback_height or 1080
        fmt = f"{video_id_fmt}+{audio_id}/bestvideo[height<={h}]+bestaudio/best"
        return [
            *base,
            "--format", fmt,
            "--merge-output-format", "mp4", "--remux-video", "mp4",
            "--embed-thumbnail", "--add-metadata", "--newline",
            "--postprocessor-args", "ffmpeg:-c:v copy -c:a aac -b:a 192k",
            *ffmpeg,
            "--output", output_tmpl, *extra_args, url,
        ]


def _run(cmd, progress_queue, timeout=MAX_TIMEOUT):
    stderr_lines = []
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        progress_queue.put({"type": "error", "message": "yt-dlp not found. Please install it."})
        return -1, "yt-dlp not found."

    start = time.time()
    for line in proc.stdout:
        line = line.rstrip()
        stderr_lines.append(line)
        m = PROGRESS_RE.search(line)
        if m:
            pct, size, speed, eta = m.groups()
            progress_queue.put({
                "type": "progress",
                "percent": float(pct),
                "size": size.strip(),
                "speed": speed.strip(),
                "eta": eta.strip(),
            })
        elif any(k in line for k in ("[ffmpeg]", "[Merger]", "Destination:", "[ExtractAudio]")):
            progress_queue.put({"type": "status", "message": line})
        if time.time() - start > timeout:
            proc.kill()
            return -2, "Timeout exceeded."

    proc.wait()
    return proc.returncode, "\n".join(stderr_lines[-30:])


def run(session_id, video_id, target_format, metadata, auth_args, progress_queue, fallback_height=None):
    t0 = time.time()
    out_dir = _session_dir(session_id)
    safe_title = _safe_name(metadata.get("title", video_id))
    audio_id   = metadata.get("best_audio_format_id", "bestaudio")
    video_id_fmt = metadata.get("best_video_format_id", "bestvideo[height<=1080]")
    ext = "mp3" if target_format == "MP3" else "mp4"
    output_tmpl = str(out_dir / f"{safe_title}.%(ext)s")

    label = "áudio" if target_format == "MP3" else "vídeo"
    progress_queue.put({"type": "status", "message": f"⬇️ Baixando {label} do YouTube..."})

    cmd = _build_cmd(video_id, target_format, audio_id, video_id_fmt, output_tmpl, auth_args, fallback_height)
    returncode, error_log = _run(cmd, progress_queue)

    if returncode != 0:
        return {"job_status": "FAILED", "session_id": session_id,
                "output_file": None, "download_url": None,
                "processing_time_seconds": round(time.time() - t0),
                "fallback_used": bool(fallback_height), "error_log": error_log}

    # Locate output file
    candidates = sorted(out_dir.glob(f"{safe_title}.*"), key=lambda f: f.stat().st_mtime, reverse=True)
    final_file = next((c for c in candidates if c.suffix.lstrip(".") in
                       (ext, "mp3", "mp4", "ogg", "aac", "m4a")), None)

    if not final_file:
        return {"job_status": "FAILED", "session_id": session_id,
                "output_file": None, "download_url": None,
                "processing_time_seconds": round(time.time() - t0),
                "fallback_used": bool(fallback_height),
                "error_log": "Output file not found after conversion."}

    size_mb = round(final_file.stat().st_size / 1_048_576, 2)
    quality = "VBR ~320kbps" if target_format == "MP3" else f"{fallback_height or 1080}p"
    progress_queue.put({"type": "done", "message": "✅ Conversão concluída!"})

    return {
        "job_status": "SUCCESS",
        "session_id": session_id,
        "output_file": {
            "path": str(final_file),
            "filename": final_file.name,
            "format": target_format,
            "filesize_mb": size_mb,
            "duration_seconds": metadata.get("duration_seconds", 0),
            "quality": quality,
        },
        "download_url": f"/api/download/{session_id}/{final_file.name}",
        "processing_time_seconds": round(time.time() - t0),
        "fallback_used": bool(fallback_height),
        "fallback_format": str(fallback_height) if fallback_height else None,
        "error_log": None,
    }

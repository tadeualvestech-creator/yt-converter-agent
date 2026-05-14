"""
Orchestrator Central — Flask Backend
Implements the full 4-phase decision protocol and exposes a REST + SSE API.
"""

import sys
import os

# Resolve project root (one level above this file's directory)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import uuid
import json
import queue
import threading
import shutil
import time
import logging
from pathlib import Path
from flask import Flask, request, jsonify, Response, send_file, abort
from flask_cors import CORS

# Pasta de arquivos estáticos (Nuxt build output)
STATIC_DIR = os.path.join(PROJECT_ROOT, "frontend", ".output", "public")
# Fallback para pasta 'static' se o Nuxt não tiver sido compilado ainda
if not os.path.exists(STATIC_DIR):
    STATIC_DIR = os.path.join(PROJECT_ROOT, "static")


from app.skills import skill1_extractor as skill1
from app.skills import skill2_auth      as skill2
from app.skills import skill3_converter as skill3
from app.skills import skill4_recovery  as skill4
from app.skills import skill5_env_guard as skill5

import os
import sys

# Descobre onde está a pasta raiz do projeto (um nível acima da pasta 'app')
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ffmpeg_bin = os.path.join(base_dir, 'bin')

# Injeta o caminho correto no sistema
os.environ["PATH"] += os.pathsep + ffmpeg_bin

print(f"Servidor iniciado. FFmpeg localizado em: {ffmpeg_bin}")

logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("orchestrator")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/")
CORS(app)

SESSIONS_DIR  = Path(PROJECT_ROOT) / "app" / "sessions"
SESSION_TTL   = 1800   # 30 minutes
MAX_PARALLEL  = 3

# Track active jobs: session_id -> {"queue": queue, "result": dict|None, "status": str}
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cleanup_session(session_id: str, delay: int = SESSION_TTL):
    """Delete session folder after TTL seconds."""
    def _worker():
        time.sleep(delay)
        folder = SESSIONS_DIR / session_id
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
            logger.info(f"Session {session_id} cleaned up.")
        with _jobs_lock:
            _jobs.pop(session_id, None)
    threading.Thread(target=_worker, daemon=True).start()


def _count_active_jobs() -> int:
    with _jobs_lock:
        return sum(1 for j in _jobs.values() if j["status"] == "running")


def _orchestrate(session_id: str, url: str, target_format: str):
    """
    Full 4-phase orchestration loop running in a background thread.
    Pushes events to the session queue consumed by the SSE endpoint.
    """
    q = _jobs[session_id]["queue"]

    def emit(event_type: str, **kwargs):
        q.put({"type": event_type, **kwargs})

    # ---------- PHASE 1: extraction ----------
    emit("status", message="🔍 Validando o link...")
    auth_args = []
    auth_attempts = 0
    extract_result = skill1.run(url, target_format, auth_args)

    if extract_result["status"] == "REQUIRES_AUTH":
        # ---------- PHASE 2: auth ----------
        emit("status", message="🔐 Preparando acesso seguro...")
        auth_result = skill2.run(error_code="REQUIRES_AUTH")
        auth_args = auth_result.get("yt_dlp_extra_args", [])
        extract_result = skill1.run(url, target_format, auth_args)

        if extract_result["status"] != "READY":
            err = extract_result.get("error_detail", "")
            info = skill4.classify(err)
            report = skill4.incident_report(
                session_id, "skill_1", err, info["classification"],
                auth_attempts + 1, info["user_message"])
            emit("error", message=info["user_message"], report=report)
            _finish(session_id, "failed")
            return

    if extract_result["status"] == "ERROR":
        err = extract_result.get("error_detail", "") or extract_result.get("error_code", "")
        info = skill4.classify(err)
        report = skill4.incident_report(
            session_id, "skill_1", err, info["classification"],
            0, info["user_message"])
        emit("error", message=info["user_message"], report=report)
        _finish(session_id, "failed")
        return

    meta = extract_result["metadata"]
    emit("metadata", title=meta["title"], channel=meta["channel"],
         duration=meta["duration_seconds"], thumbnail=meta.get("thumbnail_url", ""),
         message=f"✅ Vídeo encontrado: {meta['title']}")

    # ---------- PHASE 3: conversion ----------
    emit("status", message=f"🔧 Convertendo para {target_format}...")

    retries = 0
    fallback_heights = [720, 480, 360] if target_format == "MP4" else [None]
    fallback_idx = 0
    job_result = None

    while retries <= 3:
        fh = fallback_heights[min(fallback_idx, len(fallback_heights) - 1)]
        job_result = skill3.run(
            session_id=session_id,
            video_id=meta["video_id"],
            target_format=target_format,
            metadata=meta,
            auth_args=auth_args,
            progress_queue=q,
            fallback_height=fh,
        )

        if job_result["job_status"] == "SUCCESS":
            break

        # ---------- PHASE 4: recovery ----------
        raw_err = job_result.get("error_log", "")
        info = skill4.classify(raw_err)

        if info["is_fatal"] or retries >= info["max_retries"]:
            report = skill4.incident_report(
                session_id, "skill_3", raw_err, info["classification"],
                retries, info["user_message"])
            emit("error", message=info["user_message"], report=report)
            _finish(session_id, "failed")
            return

        delay = skill4.get_retry_delay(info["classification"], retries)
        emit("retry", message=f"⚠️ {info['user_message']} Tentativa {retries + 1}/3...",
             delay=delay)
        time.sleep(delay)

        if info["classification"] == "CODEC_ERROR":
            fallback_idx += 1
        retries += 1

    if not job_result or job_result["job_status"] != "SUCCESS":
        emit("error", message="Não foi possível completar a conversão após múltiplas tentativas.")
        _finish(session_id, "failed")
        return

    out = job_result["output_file"]
    emit("success",
         message="✅ Pronto! Seu arquivo está disponível para download.",
         filename=out["filename"],
         filesize_mb=out["filesize_mb"],
         quality=out["quality"],
         duration=out["duration_seconds"],
         download_url=job_result["download_url"],
         processing_time=job_result["processing_time_seconds"])

    _finish(session_id, "done")
    _cleanup_session(session_id, SESSION_TTL)


def _finish(session_id: str, status: str):
    with _jobs_lock:
        if session_id in _jobs:
            _jobs[session_id]["status"] = status
    # sentinel to close the SSE stream
    _jobs[session_id]["queue"].put({"type": "__done__"})


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_file(os.path.join(STATIC_DIR, "index.html"))


@app.route("/api/health")
def health():
    report = skill5.run(force=False)
    return jsonify(report)


@app.route("/api/convert", methods=["POST"])
def convert():
    data = request.get_json(force=True, silent=True) or {}
    url    = (data.get("url") or "").strip()
    fmt    = (data.get("format") or "MP3").upper()

    if fmt not in ("MP3", "MP4"):
        return jsonify({"error": "Formato inválido. Use MP3 ou MP4."}), 400

    if not url:
        return jsonify({"error": "URL não fornecida."}), 400

    if _count_active_jobs() >= MAX_PARALLEL:
        return jsonify({"error": "Servidor ocupado. Tente novamente em alguns instantes."}), 429

    # --- Skill #5: Pre-flight environment check ---
    ready, env_error = skill5.assert_ready(fmt)
    if not ready:
        return jsonify({"error": env_error}), 503

    session_id = str(uuid.uuid4())
    q = queue.Queue()

    with _jobs_lock:
        _jobs[session_id] = {"queue": q, "status": "running", "result": None}

    thread = threading.Thread(
        target=_orchestrate, args=(session_id, url, fmt), daemon=True)
    thread.start()

    return jsonify({"session_id": session_id})


@app.route("/api/events/<session_id>")
def events(session_id: str):
    """Server-Sent Events endpoint for real-time progress."""
    with _jobs_lock:
        if session_id not in _jobs:
            abort(404)
    q = _jobs[session_id]["queue"]

    def stream():
        while True:
            try:
                event = q.get(timeout=60)
            except queue.Empty:
                yield "event: heartbeat\ndata: {}\n\n"
                continue

            if event.get("type") == "__done__":
                yield f"event: close\ndata: {{}}\n\n"
                break

            payload = json.dumps(event, ensure_ascii=False)
            yield f"event: message\ndata: {payload}\n\n"

    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/download/<session_id>/<path:filename>")
def download(session_id: str, filename: str):
    file_path = SESSIONS_DIR / session_id / filename
    if not file_path.exists():
        abort(404)
    # Safety: prevent path traversal
    try:
        file_path.relative_to(SESSIONS_DIR / session_id)
    except ValueError:
        abort(403)
    return send_file(str(file_path), as_attachment=True, download_name=filename)


if __name__ == "__main__":
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    (Path(PROJECT_ROOT) / "app" / "auth").mkdir(parents=True, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

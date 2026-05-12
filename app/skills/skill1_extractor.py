"""
Skill #1 — YouTube Extractor
Validates the URL and extracts structured metadata via yt-dlp.
"""

import re
import subprocess
import sys
import shutil
import json
import logging

logger = logging.getLogger(__name__)

ALLOWED_DOMAINS = re.compile(
    r'^https?://(www\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)'
)

MAX_DURATION = {
    "MP3": 10800,   # 3 hours
    "MP4": 7200,    # 2 hours
}

ERROR_MAP = [
    (re.compile(r"Sign in to confirm you're not a bot", re.I), "REQUIRES_AUTH",  "REQUIRES_AUTH"),
    (re.compile(r"HTTP Error 403",                       re.I), "REQUIRES_AUTH",  "REQUIRES_AUTH"),
    (re.compile(r"Video unavailable in your country",    re.I), "ERROR",          "VIDEO_UNAVAILABLE"),
    (re.compile(r"Private video",                        re.I), "ERROR",          "VIDEO_UNAVAILABLE"),
    (re.compile(r"Video unavailable",                    re.I), "ERROR",          "VIDEO_UNAVAILABLE"),
    (re.compile(r"This video is not available",          re.I), "ERROR",          "VIDEO_UNAVAILABLE"),
    (re.compile(r"Sign in",                              re.I), "REQUIRES_AUTH",  "REQUIRES_AUTH"),
]


def _classify_error(stderr: str) -> tuple[str, str]:
    """Maps raw yt-dlp stderr to (status, error_code)."""
    for pattern, status, code in ERROR_MAP:
        if pattern.search(stderr):
            return status, code
    return "ERROR", "NETWORK_ERROR"


def _select_best_formats(formats: list[dict]) -> tuple[str | None, str | None]:
    """Choose best audio and video format IDs from yt-dlp format list."""
    audio_formats = [
        f for f in formats
        if f.get("vcodec") in (None, "none") and f.get("acodec") not in (None, "none")
    ]
    video_formats = [
        f for f in formats
        if f.get("vcodec") not in (None, "none")
        and f.get("acodec") in (None, "none")
        and f.get("height", 9999) <= 1080
    ]

    # Best audio: prefer m4a/opus, then highest abr
    audio_formats_sorted = sorted(
        audio_formats,
        key=lambda f: (
            1 if f.get("ext") in ("m4a", "opus", "webm") else 0,
            f.get("abr") or 0,
            f.get("tbr") or 0,
        ),
        reverse=True,
    )

    # Best video: highest resolution up to 1080p
    video_formats_sorted = sorted(
        video_formats,
        key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
        reverse=True,
    )

    best_audio_id = audio_formats_sorted[0]["format_id"] if audio_formats_sorted else None
    best_video_id = video_formats_sorted[0]["format_id"] if video_formats_sorted else None
    return best_audio_id, best_video_id


def _ytdlp_cmd() -> list[str]:
    if shutil.which("yt-dlp"):
        return ["yt-dlp"]
    return [sys.executable, "-m", "yt_dlp"]


def run(url: str, target_format: str = "MP3", extra_args: list[str] | None = None) -> dict:
    """
    Main entry point for Skill #1.
    Returns a JSON-compatible dict matching the contract schema.
    """
    extra_args = extra_args or []

    # --- URL Validation ---
    if not ALLOWED_DOMAINS.match(url):
        return {
            "status": "ERROR",
            "metadata": None,
            "error_code": "DOMAIN_REJECTED",
            "error_detail": f"URL not from an accepted domain: {url}",
        }

    # --- Run yt-dlp --dump-json ---
    cmd = [
        *_ytdlp_cmd(),
        "--dump-json",
        "--no-playlist",
        *extra_args,
        url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        return {
            "status": "ERROR",
            "metadata": None,
            "error_code": "YTDLP_NOT_FOUND",
            "error_detail": "yt-dlp executable not found. Please install it.",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "ERROR",
            "metadata": None,
            "error_code": "NETWORK_ERROR",
            "error_detail": "yt-dlp timed out after 60 seconds.",
        }

    if result.returncode != 0:
        stderr = result.stderr or ""
        status, code = _classify_error(stderr)
        return {
            "status": status,
            "metadata": None,
            "error_code": code,
            "error_detail": stderr.strip()[:500],
        }

    # --- Parse JSON ---
    try:
        info = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {
            "status": "ERROR",
            "metadata": None,
            "error_code": "PARSE_ERROR",
            "error_detail": str(e),
        }

    duration = info.get("duration", 0) or 0
    max_dur = MAX_DURATION.get(target_format, 10800)
    if duration > max_dur:
        return {
            "status": "ERROR",
            "metadata": None,
            "error_code": "DURATION_EXCEEDED",
            "error_detail": (
                f"Video duration {duration}s exceeds maximum allowed "
                f"{max_dur}s for {target_format}."
            ),
        }

    # --- Build formats list ---
    raw_formats = info.get("formats", [])
    available_formats = [
        {
            "format_id": f.get("format_id"),
            "ext": f.get("ext"),
            "quality": f.get("format_note") or f.get("quality", ""),
            "filesize_approx_mb": round((f.get("filesize") or f.get("filesize_approx") or 0) / 1_048_576, 1),
            "vcodec": f.get("vcodec"),
            "acodec": f.get("acodec"),
            "height": f.get("height"),
            "abr": f.get("abr"),
        }
        for f in raw_formats
    ]

    best_audio_id, best_video_id = _select_best_formats(raw_formats)

    thumbnail = info.get("thumbnail") or (info.get("thumbnails") or [{}])[-1].get("url", "")

    return {
        "status": "READY",
        "metadata": {
            "video_id": info.get("id"),
            "title": info.get("title"),
            "channel": info.get("uploader") or info.get("channel"),
            "duration_seconds": duration,
            "thumbnail_url": thumbnail,
            "upload_date": info.get("upload_date"),
            "available_formats": available_formats,
            "best_audio_format_id": best_audio_id,
            "best_video_format_id": best_video_id,
        },
        "error_code": None,
        "error_detail": None,
    }

"""
Skill #5 — Environment Guard
Pre-flight checks for FFmpeg, FFprobe, yt-dlp, disk space and write permissions.
Results are cached for 5 minutes to avoid repeated shell calls.
"""

import shutil
import subprocess
import sys
import os
import time
import logging
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_HERE      = Path(__file__).resolve().parent.parent.parent  # project root
_BIN_DIR   = _HERE / "bin"
_SESSIONS  = _HERE / "app" / "sessions"

MIN_FREE_MB   = 500
CACHE_TTL_SEC = 300  # 5 minutes

_cache: dict = {}
_cache_time: float = 0.0


# ---------------------------------------------------------------------------
# Individual checkers
# ---------------------------------------------------------------------------

def _check_binary(name: str, extra_paths: list[Path] | None = None) -> dict:
    """Check if a binary is available (PATH or local bin/)."""
    candidates = [name]
    if extra_paths:
        candidates = [str(p / name) for p in extra_paths] + candidates

    for candidate in candidates:
        try:
            r = subprocess.run(
                [candidate, "-version"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                # parse first line for version string
                first = (r.stdout or r.stderr or "").splitlines()[0]
                version = first.split()[2] if len(first.split()) > 2 else first[:20]
                return {"ok": True, "version": version, "path": candidate}
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    return {"ok": False, "version": None, "path": None}


def _check_ytdlp() -> dict:
    """Check yt-dlp version and staleness."""
    cmd = (
        [shutil.which("yt-dlp")] if shutil.which("yt-dlp")
        else [sys.executable, "-m", "yt_dlp"]
    )
    try:
        r = subprocess.run(
            [*cmd, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        version = r.stdout.strip()
        # Parse date from version string like "2026.03.17"
        try:
            parts = version.split(".")
            vdate = datetime(int(parts[0]), int(parts[1]), int(parts[2]), tzinfo=timezone.utc)
            days_old = (datetime.now(timezone.utc) - vdate).days
        except Exception:
            days_old = 0
        return {"ok": True, "version": version, "days_old": days_old,
                "stale": days_old > 30}
    except Exception as e:
        return {"ok": False, "version": None, "days_old": None, "stale": False, "error": str(e)}


def _check_disk() -> dict:
    """Check free disk space on the sessions partition."""
    try:
        _SESSIONS.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(str(_SESSIONS))
        free_mb = usage.free // (1024 * 1024)
        return {"ok": free_mb >= MIN_FREE_MB, "free_mb": free_mb}
    except Exception as e:
        return {"ok": False, "free_mb": None, "error": str(e)}


def _check_write_perm() -> dict:
    """Check write permission in the sessions directory."""
    try:
        _SESSIONS.mkdir(parents=True, exist_ok=True)
        test_file = _SESSIONS / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run(force: bool = False) -> dict:
    """
    Run all pre-flight checks.
    Returns a health report dict. Results cached for CACHE_TTL_SEC seconds.
    """
    global _cache, _cache_time
    now = time.time()

    if not force and _cache and (now - _cache_time) < CACHE_TTL_SEC:
        logger.debug("Returning cached env-guard result.")
        return _cache

    extra_paths = [_BIN_DIR] if _BIN_DIR.exists() else []

    checks = {
        "ffmpeg":     _check_binary("ffmpeg",  extra_paths),
        "ffprobe":    _check_binary("ffprobe", extra_paths),
        "yt_dlp":     _check_ytdlp(),
        "disk_space": _check_disk(),
        "write_perm": _check_write_perm(),
    }

    missing = [k for k, v in checks.items() if not v["ok"]]
    stale_ytdlp = checks["yt_dlp"].get("stale", False)

    # Determine overall health
    critical_deps = {"ffmpeg", "ffprobe", "yt_dlp", "write_perm"}
    critical_missing = [m for m in missing if m in critical_deps]

    if critical_missing:
        health = "CRITICAL"
    elif missing or stale_ytdlp:
        health = "WARNING"
    else:
        health = "OK"

    # Build actionable fix message
    fixes = []
    if "ffmpeg" in missing or "ffprobe" in missing:
        fixes.append("Execute: python setup_ffmpeg.py")
    if not checks["yt_dlp"]["ok"]:
        fixes.append("Execute: python -m pip install yt-dlp")
    if stale_ytdlp:
        fixes.append("Execute: python -m pip install -U yt-dlp  (yt-dlp desatualizado)")
    if "disk_space" in missing:
        fixes.append(f"Libere pelo menos {MIN_FREE_MB} MB em disco.")
    if "write_perm" in missing:
        fixes.append(f"Verifique permissoes de escrita em: {_SESSIONS}")

    result = {
        "system_health": health,
        "checks": checks,
        "missing_dependencies": missing,
        "stale_ytdlp": stale_ytdlp,
        "actionable_fix": " | ".join(fixes) if fixes else None,
        "severity": len(critical_missing) * 10 + len(missing) * 2,
        "block_conversion": bool(critical_missing),
    }

    _cache = result
    _cache_time = now

    if health != "OK":
        logger.warning(f"[Skill5] System health: {health} | Missing: {missing}")

    return result


def assert_ready(target_format: str = "MP3") -> tuple[bool, str | None]:
    """
    Quick check called before each conversion.
    Returns (is_ready, user_facing_error_message).
    """
    report = run()
    if not report["block_conversion"]:
        # For MP4, ffprobe is strictly required
        if target_format == "MP4" and not report["checks"]["ffprobe"]["ok"]:
            return False, ("FFprobe nao encontrado. Necessario para converter MP4. "
                           "Execute: python setup_ffmpeg.py")
        return True, None
    return False, report.get("actionable_fix") or "Dependencias do sistema ausentes."

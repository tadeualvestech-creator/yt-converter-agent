"""
Skill #4 — Error Recovery
Classifies failures, applies retry logic, translates errors to friendly messages,
and generates structured incident reports.
"""

import re
import logging
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Error classification table
# ---------------------------------------------------------------------------
ERROR_TABLE = [
    # (pattern, classification, friendly_message, max_retries)
    (re.compile(r"HTTP Error 429|Too Many Requests",        re.I),
     "RATE_LIMITED",
     "O YouTube detectou muitas requisições. Aguardando alguns minutos antes de tentar novamente automaticamente.",
     3),
    (re.compile(r"Sign in to confirm you're not a bot",     re.I),
     "AUTH_NEEDED",
     "O YouTube está pedindo verificação de identidade. Tentando renovar autenticação...",
     1),
    (re.compile(r"HTTP Error 403",                          re.I),
     "AUTH_NEEDED",
     "Acesso negado pelo YouTube. Tentando com autenticação reforçada...",
     1),
    (re.compile(r"Video unavailable in your country",       re.I),
     "FATAL",
     "Este vídeo não está disponível na sua região geográfica. Infelizmente não é possível convertê-lo.",
     0),
    (re.compile(r"Private video",                           re.I),
     "FATAL",
     "Este vídeo é privado. Apenas o proprietário pode acessá-lo.",
     0),
    (re.compile(r"Video unavailable|This video is not available", re.I),
     "FATAL",
     "Parece que este vídeo foi removido ou está privado no YouTube. Não consigo acessá-lo no momento.",
     0),
    # FFmpeg missing — must come BEFORE generic ffmpeg error
    (re.compile(r"ffprobe and ffmpeg not found|ffmpeg.*not found|ffmpeg.*not installed|"
                r"Postprocessing:.*ffprobe|WARNING.*ffmpeg.*available", re.I),
     "FFMPEG_MISSING",
     "FFmpeg não está instalado. Execute 'python setup_ffmpeg.py' para instalá-lo automaticamente.",
     0),
    (re.compile(r"ffmpeg exited with code|ffmpeg error|"
                r"Postprocessing: ffmpeg",                  re.I),
     "CODEC_ERROR",
     "Houve um problema técnico durante a conversão. Tentando com um formato alternativo...",
     1),
    (re.compile(r"Disk full|No space left",                 re.I),
     "DISK_FULL",
     "Estamos com pouco espaço no servidor. Fazendo limpeza automática e tentando novamente...",
     1),
    (re.compile(r"Signature extraction failed|nsig",        re.I),
     "OUTDATED",
     "O yt-dlp precisa ser atualizado. Atualizando automaticamente...",
     1),
    (re.compile(r"Connection timed out|Read timed out|urlopen error", re.I),
     "TRANSIENT",
     "A conexão foi interrompida. Tentando novamente...",
     3),
    (re.compile(r"yt-dlp not found|No module named",        re.I),
     "FATAL",
     "Dependência de sistema não encontrada. Contate o administrador.",
     0),
]

RETRY_DELAYS = {
    "TRANSIENT":      [5,   15,  30],
    "RATE_LIMITED":   [300, 600, 1200],
    "AUTH_NEEDED":    [2],
    "CODEC_ERROR":    [2],
    "DISK_FULL":      [5],
    "OUTDATED":       [3],
    "FFMPEG_MISSING": [],
}


def classify(raw_error: str) -> dict:
    """Classify a raw error string and return its metadata."""
    for pattern, classification, message, max_retries in ERROR_TABLE:
        if pattern.search(raw_error):
            return {
                "classification": classification,
                "user_message": message,
                "max_retries": max_retries,
                "is_fatal": classification == "FATAL",
            }
    return {
        "classification": "UNKNOWN",
        "user_message": "Ocorreu um erro inesperado. Nosso sistema está tentando se recuperar.",
        "max_retries": 1,
        "is_fatal": False,
    }


def get_retry_delay(classification: str, attempt: int) -> int:
    """Return seconds to wait before the next retry attempt."""
    delays = RETRY_DELAYS.get(classification, [10, 30, 60])
    idx = min(attempt, len(delays) - 1)
    return delays[idx]


def should_retry(classification: str, attempts_so_far: int, max_retries: int) -> bool:
    if classification == "FATAL":
        return False
    return attempts_so_far < max_retries


def incident_report(
    session_id: str,
    failed_skill: str,
    raw_error: str,
    classification: str,
    retries: int,
    user_message: str,
    recommendation: str = "",
) -> dict:
    """Build a structured incident report for the administrator."""
    return {
        "incident_report": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "failed_skill": failed_skill,
            "raw_error": raw_error[:500],
            "classification": classification,
            "retries_attempted": retries,
            "user_message": user_message,
            "system_recommendation": recommendation or _auto_recommendation(classification),
        }
    }


def _auto_recommendation(classification: str) -> str:
    recs = {
        "RATE_LIMITED":   "Configure um proxy rotativo ou aguarde o cooldown do IP.",
        "AUTH_NEEDED":    "Atualize cookies.txt ou configure um po_token válido.",
        "CODEC_ERROR":    "Verifique a instalação do FFmpeg e sua versão.",
        "DISK_FULL":      "Limpe arquivos temporários em app/sessions/ e /tmp/.",
        "OUTDATED":       "Execute: python -m pip install -U yt-dlp",
        "TRANSIENT":      "Verifique a conectividade de rede do servidor.",
        "FATAL":          "Nenhuma ação possível. Informe o usuário.",
        "FFMPEG_MISSING": "Execute: python setup_ffmpeg.py  (instala FFmpeg automaticamente)",
        "UNKNOWN":        "Analise os logs completos e reporte ao desenvolvedor.",
    }
    return recs.get(classification, "Analise os logs para mais detalhes.")

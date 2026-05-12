"""
Skill #2 — Auth Manager
Prepares yt-dlp authentication arguments using a hierarchy of bypass strategies.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

COOKIES_PATH   = os.getenv("YT_COOKIES_PATH",      "app/auth/cookies.txt")
PO_TOKEN_PATH  = os.getenv("YT_PO_TOKEN_PATH",     "app/auth/po_token.txt")
PO_TOKEN_VALUE = os.getenv("YT_PO_TOKEN",          "")
PROXY_URL      = os.getenv("YT_PROXY_URL",         "")
BROWSER_PREF   = os.getenv("YT_BROWSER_PREFERRED", "chrome")

USER_AGENTS = [
    # Chrome 125 Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    # Firefox 126 Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    # Safari 17 macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

BROWSER_ORDER = ["chrome", "firefox", "edge", "chromium", "opera", "brave"]


def _strategy_browser_cookies() -> list[str] | None:
    """Strategy 1: extract cookies from an installed browser."""
    browser = BROWSER_PREF if BROWSER_PREF in BROWSER_ORDER else "chrome"
    return [f"--cookies-from-browser", browser]


def _strategy_cookies_file() -> list[str] | None:
    """Strategy 2: use a pre-exported cookies.txt file."""
    path = Path(COOKIES_PATH)
    if path.exists() and path.stat().st_size > 0:
        return ["--cookies", str(path)]
    return None


def _strategy_po_token() -> list[str] | None:
    """Strategy 3: inject a PO Token for bot-challenge bypass."""
    token = PO_TOKEN_VALUE
    if not token:
        path = Path(PO_TOKEN_PATH)
        if path.exists():
            token = path.read_text().strip()
    if token:
        args = [
            "--extractor-args", f"youtube:player_client=web;po_token=web+{token}",
        ]
        if Path(COOKIES_PATH).exists():
            args += ["--cookies", COOKIES_PATH]
        return args
    return None


def _strategy_user_agent(index: int = 0) -> list[str]:
    """Strategy 4: rotate user-agent header."""
    ua = USER_AGENTS[index % len(USER_AGENTS)]
    return [
        "--add-header", f"User-Agent:{ua}",
        "--add-header", "Accept-Language:pt-BR,pt;q=0.9,en-US;q=0.8",
    ]


def _strategy_proxy() -> list[str] | None:
    """Strategy 5: route through an external proxy."""
    if PROXY_URL:
        return ["--proxy", PROXY_URL]
    return None


def run(error_code: str | None = None, ua_index: int = 0) -> dict:
    """
    Main entry point for Skill #2.
    Builds and returns the best available auth args for yt-dlp.
    """
    strategy_used = "NONE"
    extra_args: list[str] = []
    notes = ""

    if error_code == "REQUIRES_AUTH":
        # Try PO Token first (most targeted fix for bot challenges)
        args = _strategy_po_token()
        if args:
            extra_args = args
            strategy_used = "PO_TOKEN"
            notes = "PO Token injected for bot-challenge bypass."
        else:
            # Fall back to cookies file
            args = _strategy_cookies_file()
            if args:
                extra_args = args
                strategy_used = "COOKIES_FILE"
                notes = "cookies.txt loaded from disk."
            else:
                # Fall back to browser cookies
                extra_args = _strategy_browser_cookies()
                strategy_used = "BROWSER_COOKIES"
                notes = f"Extracting cookies from {BROWSER_PREF} browser session."
    else:
        # Default: browser cookies + user-agent
        args = _strategy_browser_cookies()
        ua_args = _strategy_user_agent(ua_index)
        extra_args = args + ua_args
        strategy_used = "BROWSER_COOKIES+UA"
        notes = "Default auth: browser cookies + rotated User-Agent."

    # Append proxy if configured
    proxy_args = _strategy_proxy()
    if proxy_args:
        extra_args += proxy_args
        notes += " Proxy enabled."

    auth_status = "SUCCESS" if extra_args else "PARTIAL"

    return {
        "auth_status": auth_status,
        "strategy_used": strategy_used,
        "yt_dlp_extra_args": extra_args,
        "session_id": str(uuid.uuid4()),
        "auth_timestamp": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
    }

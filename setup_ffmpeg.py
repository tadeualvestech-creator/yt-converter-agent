"""
setup_ffmpeg.py — Downloads and installs a portable FFmpeg binary for Windows.
Run once: python setup_ffmpeg.py
"""

import os
import sys
import zipfile
import urllib.request
import shutil
from pathlib import Path

BIN_DIR     = Path(__file__).parent / "bin"
FFMPEG_EXE  = BIN_DIR / "ffmpeg.exe"
FFPROBE_EXE = BIN_DIR / "ffprobe.exe"

# Gyan.dev essentials build — lightweight (~80 MB zip)
FFMPEG_URL = (
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
)


def download_ffmpeg():
    if FFMPEG_EXE.exists() and FFPROBE_EXE.exists():
        print(f"[OK] FFmpeg + FFprobe already present in {BIN_DIR}")
        return True

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = BIN_DIR / "ffmpeg.zip"

    print(f"[*] Downloading FFmpeg from {FFMPEG_URL}")
    print("    This may take a minute (~80 MB)...")

    try:
        def reporthook(count, block_size, total_size):
            if total_size > 0:
                pct = min(100, count * block_size * 100 // total_size)
                print(f"\r    Progress: {pct}%", end="", flush=True)

        urllib.request.urlretrieve(FFMPEG_URL, zip_path, reporthook)
        print()  # newline after progress

        print("[*] Extracting...")
        TARGETS = {"bin/ffmpeg.exe": "ffmpeg.exe", "bin/ffprobe.exe": "ffprobe.exe"}
        extracted = {}
        with zipfile.ZipFile(zip_path, "r") as z:
            for name in z.namelist():
                for suffix, dest_name in TARGETS.items():
                    if name.endswith(suffix) and dest_name not in extracted:
                        dest = BIN_DIR / dest_name
                        dest.write_bytes(z.read(name))
                        extracted[dest_name] = dest
                        print(f"[OK] Extracted {dest_name} -> {dest}")
                        break

        missing = [t for t in TARGETS.values() if t not in extracted]
        if missing:
            print(f"[ERROR] Missing from zip: {missing}")
            return False

        zip_path.unlink()  # clean up zip
        return True

    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        if zip_path.exists():
            zip_path.unlink()
        return False


if __name__ == "__main__":
    ok = download_ffmpeg()
    if ok:
        print("\n[OK] FFmpeg + FFprobe prontos. Inicie o servidor: python app/server.py")
    else:
        print("\n[!] Download automatico falhou.")
        print("    Baixe o FFmpeg manualmente em https://ffmpeg.org/download.html")
        print("    e coloque ffmpeg.exe e ffprobe.exe na pasta 'bin/' do projeto.")
    sys.exit(0 if ok else 1)

#!/usr/bin/env bash
cd "$(dirname "$0")"
python3 -m pip install -U -r requirements.txt
command -v ffmpeg >/dev/null || echo "[AVISO] ffmpeg não encontrado (Mac: brew install ffmpeg | Linux: sudo apt install ffmpeg)"
python3 server.py

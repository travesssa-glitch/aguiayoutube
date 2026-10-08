"""
YT Downloader local - servidor
Roda no seu PC (127.0.0.1:8765). A página web e a extensão do Chrome conversam com ele.
Requer: yt-dlp, Flask e ffmpeg instalado no sistema.
"""
import os
import re
import shutil
import tempfile
import threading
import time
import uuid
import webbrowser

import yt_dlp
from flask import Flask, jsonify, request, send_file, send_from_directory

PORT = 8765
HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(HERE, "static"), static_url_path="/static")

BASE = os.path.join(tempfile.gettempdir(), "ytdl_local")
os.makedirs(BASE, exist_ok=True)

JOBS = {}
LOCK = threading.Lock()

CODEC_NAMES = {"avc1": "H.264", "vp09": "VP9", "vp9": "VP9", "av01": "AV1", "hev1": "H.265", "hvc1": "H.265"}


def has_ffmpeg():
    return shutil.which("ffmpeg") is not None


def clean_text(e):
    s = re.sub(r"\x1b\[[0-9;]*m", "", str(e))
    return s.replace("ERROR: ", "")[:400]


def clean_old():
    now = time.time()
    for name in os.listdir(BASE):
        p = os.path.join(BASE, name)
        try:
            if now - os.path.getmtime(p) > 3600:
                shutil.rmtree(p, ignore_errors=True)
        except OSError:
            pass
    with LOCK:
        for k in [k for k, j in JOBS.items() if now - j["created"] > 3600]:
            JOBS.pop(k, None)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return jsonify(ok=True, ffmpeg=has_ffmpeg(), yt_dlp=yt_dlp.version.__version__)


@app.get("/api/info")
def api_info():
    url = (request.args.get("url") or "").strip()
    if not url:
        return jsonify(error="Link vazio."), 400
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": True}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:  # noqa: BLE001
        return jsonify(error=clean_text(e)), 400

    best_by_height = {}
    best_audio = None
    for f in info.get("formats") or []:
        vc = f.get("vcodec") or "none"
        ac = f.get("acodec") or "none"
        if vc != "none" and f.get("height"):
            h = f["height"]
            score = (f.get("fps") or 0, f.get("tbr") or 0)
            cur = best_by_height.get(h)
            if cur is None or score > cur[0]:
                best_by_height[h] = (score, f)
        elif ac != "none" and vc == "none":
            if best_audio is None or (f.get("abr") or 0) > (best_audio.get("abr") or 0):
                best_audio = f

    videos = []
    for h in sorted(best_by_height, reverse=True):
        f = best_by_height[h][1]
        fps = int(f.get("fps") or 0)
        label = f"{h}p" + (str(fps) if fps > 30 else "")
        codec = CODEC_NAMES.get((f.get("vcodec") or "").split(".")[0], (f.get("vcodec") or "?").split(".")[0])
        videos.append({
            "height": h,
            "fps": fps,
            "label": label,
            "codec": codec,
            "size": f.get("filesize") or f.get("filesize_approx") or 0,
        })

    audio = {"ext": "m4a", "abr": 0, "codec": "?", "size": 0}
    if best_audio:
        audio = {
            "ext": best_audio.get("ext") or "m4a",
            "abr": int(best_audio.get("abr") or 0),
            "codec": (best_audio.get("acodec") or "?").split(".")[0],
            "size": best_audio.get("filesize") or best_audio.get("filesize_approx") or 0,
        }

    return jsonify(
        title=info.get("title") or "video",
        uploader=info.get("uploader") or "",
        duration=info.get("duration") or 0,
        thumbnail=info.get("thumbnail") or "",
        videos=videos,
        audio=audio,
        ffmpeg=has_ffmpeg(),
    )


def run_job(job_id, p):
    job = JOBS[job_id]
    out_dir = os.path.join(BASE, job_id)
    os.makedirs(out_dir, exist_ok=True)
    n_streams = 2 if p["kind"] == "video" else 1

    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            frac = (d.get("downloaded_bytes", 0) / total) if total else 0
            job["percent"] = min(99.0, (job["streams_done"] + frac) / n_streams * 100)
            job["speed"] = d.get("speed") or 0
            job["eta"] = d.get("eta") or 0
            job["stage"] = "downloading"
        elif d["status"] == "finished":
            job["streams_done"] += 1
            if job["streams_done"] >= n_streams:
                job["stage"] = "processing"

    def pp_hook(d):
        if d.get("status") == "started":
            job["stage"] = "processing"

    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "outtmpl": os.path.join(out_dir, "%(title).150B.%(ext)s"),
        "windowsfilenames": True,
        "progress_hooks": [hook],
        "postprocessor_hooks": [pp_hook],
    }

    if p["kind"] == "video":
        h = p.get("height")
        if h:
            opts["format"] = f"bv*[height<={h}]+ba/b[height<={h}]/bv*+ba/b"
        else:
            opts["format"] = "bv*+ba/b"
        opts["merge_output_format"] = "mp4" if p.get("container") == "mp4" else "mkv"
    else:
        opts["format"] = "ba/b"
        fmt = p.get("audio_format", "original")
        if fmt != "original":
            pp = {"key": "FFmpegExtractAudio", "preferredcodec": fmt}
            if fmt == "mp3":
                pp["preferredquality"] = str(p.get("bitrate") or 320)
            opts["postprocessors"] = [pp]

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([p["url"]])
        files = [
            os.path.join(out_dir, f)
            for f in os.listdir(out_dir)
            if not f.endswith((".part", ".ytdl", ".temp"))
        ]
        if not files:
            raise RuntimeError("Nenhum arquivo foi gerado.")
        path = max(files, key=os.path.getsize)
        job.update(file=path, filename=os.path.basename(path), percent=100.0, stage="done", done=True)
    except Exception as e:  # noqa: BLE001
        job.update(error=clean_text(e), stage="error")


@app.post("/api/start")
def api_start():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    kind = data.get("kind", "video")
    if not url:
        return jsonify(error="Link vazio."), 400
    needs_ffmpeg = kind == "video" or data.get("audio_format", "original") != "original"
    if needs_ffmpeg and not has_ffmpeg():
        return jsonify(error="ffmpeg não encontrado. Instale o ffmpeg (veja o README) e reinicie o servidor."), 400

    clean_old()
    height = data.get("height")
    params = {
        "url": url,
        "kind": kind,
        "height": int(height) if height else None,
        "container": data.get("container", "mkv"),
        "audio_format": data.get("audio_format", "original"),
        "bitrate": data.get("bitrate"),
    }
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {
        "created": time.time(), "percent": 0.0, "stage": "waiting", "speed": 0, "eta": 0,
        "streams_done": 0, "done": False, "error": None, "file": None, "filename": None,
    }
    threading.Thread(target=run_job, args=(job_id, params), daemon=True).start()
    return jsonify(job=job_id)


@app.get("/api/progress/<job_id>")
def api_progress(job_id):
    j = JOBS.get(job_id)
    if not j:
        return jsonify(error="Download não encontrado."), 404
    return jsonify(percent=j["percent"], stage=j["stage"], speed=j["speed"], eta=j["eta"],
                   done=j["done"], error=j["error"], filename=j["filename"])


@app.get("/api/file/<job_id>")
def api_file(job_id):
    j = JOBS.get(job_id)
    if not j or not j.get("done") or not j.get("file"):
        return jsonify(error="Arquivo ainda não está pronto."), 404
    return send_file(j["file"], as_attachment=True, download_name=j["filename"])


if __name__ == "__main__":
    print(f"\n  YT Downloader local rodando em http://127.0.0.1:{PORT}")
    print("  ffmpeg:", "OK" if has_ffmpeg() else "NÃO ENCONTRADO (instale para juntar vídeo+áudio e converter MP3/WAV)")
    print("  Deixe esta janela aberta enquanto usa a extensão.\n")
    if os.environ.get("YTDL_NO_BROWSER") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    app.run(host="127.0.0.1", port=PORT, threaded=True)

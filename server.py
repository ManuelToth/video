"""Small fail-closed FFmpeg placeholder renderer for n8n Render Free demo.

No external media fetching, no arbitrary FFmpeg command execution, and no
persistent storage. Demo links are bearer URLs and expire after 1 hour.
"""

import hmac
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
import textwrap
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

API_KEY = os.environ.get("RENDER_API_KEY", "")
PORT = int(os.environ.get("PORT", "10000"))
ROOT = Path("/tmp/tcg-render")
ROOT.mkdir(parents=True, exist_ok=True)
JOBS = {}
LOCK = threading.Lock()
COLORS = ["0x20263f", "0x193e52", "0x284735", "0x48304b", "0x3c3b25"]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
EXPIRY = 3600


def validate_manifest(data):
    if not isinstance(data, dict):
        raise ValueError("JSON object expected")
    # Do not accept FFmpeg commands, file paths or external media URLs.
    if set(data.keys()) - {"title", "scenes"}:
        raise ValueError("Only title and scenes allowed")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != 5:
        raise ValueError("Exactly five scenes required")
    cleaned = []
    seconds = 0
    for item in scenes:
        if not isinstance(item, dict) or set(item.keys()) - {"text", "dauer_s"}:
            raise ValueError("Each scene needs only text and dauer_s")
        label = item.get("text")
        duration = item.get("dauer_s")
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 100 or "\x00" in label:
            raise ValueError("Scene text must contain 1 to 100 characters")
        if isinstance(duration, bool) or not isinstance(duration, (float, int)) or not math.isfinite(duration) or int(duration) != duration or not 2 <= duration <= 12:
            raise ValueError("Scene duration must be a whole number, 2 to 12 seconds")
        seconds += int(duration)
        cleaned.append({"text": label, "dauer_s": int(duration)})
    if seconds > 45:
        raise ValueError("Maximum 45 seconds")
    return cleaned


def ffmpeg(cmd, timeout=150):
    return subprocess.run(cmd, timeout=timeout, check=True, stdout=subprocess.DEVNULL,
                          stderr=subprocess.PIPE).stderr.decode("utf-8", errors="replace")


def render(job_id, scenes):
    work = ROOT / job_id
    try:
        work.mkdir(mode=0o700, exist_ok=False)
        listfile = work / "files.txt"
        parts = []
        for i, scene in enumerate(scenes):
            # Plain text file keeps user text out of the FFmpeg filter expression.
            label = "\n".join(textwrap.wrap(" ".join(scene["text"].split()), width=22))
            overlay = f"HYPOTHESE  -  TESTVIDEO\n\nSZENE {i+1}/5\n\n{label}"
            (work / f"scene_{i}.txt").write_text(overlay, encoding="utf-8")
            path = work / f"part_{i}.mp4"
            vf = (f"drawtext=fontfile={FONT}:textfile={work / f'scene_{i}.txt'}:"
                  "fontcolor=white:fontsize=23:line_spacing=12:"
                  "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.45:boxborderw=12")
            ffmpeg(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", f"color=c={COLORS[i]}:s=360x640:r=12:d={scene['dauer_s']}",
                    "-vf", vf, "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30",
                    "-pix_fmt", "yuv420p", "-threads", "1", str(path)], timeout=120)
            parts.append(path)
        listfile.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
        ffmpeg(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy",
                "-movflags", "+faststart", str(work / "preview.mp4")], timeout=60)
        with LOCK:
            JOBS[job_id]["status"] = "done"
    except Exception as ex:
        with LOCK:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = type(ex).__name__  # no internal command leak


def cleanup():
    now = time.time()
    with LOCK:
        stale = [jid for jid, data in JOBS.items() if now-data["created"] > EXPIRY]
        for jid in stale:
            JOBS.pop(jid, None)
    for jid in stale:
        shutil.rmtree(ROOT / jid, ignore_errors=True)


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        cleanup()
        path = urlsplit(self.path).path
        if path == "/health":
            return self.send_json(200, {"service": "tcg-media-renderer", "running": True, "render_enabled": bool(API_KEY)})
        match = re.fullmatch(r"/(status|download)/([A-Za-z0-9_-]{28,64})", path)
        if not match:
            return self.send_json(404, {"error": "not_found"})
        kind, jid = match.groups()
        with LOCK:
            job = dict(JOBS.get(jid, {}))
        if not job:
            return self.send_json(404, {"error": "expired_or_unknown_job"})
        if kind == "status":
            return self.send_json(200, {"job_id": jid, "status": job["status"],
                                        "error": job.get("error"),
                                        "download_path": f"/download/{jid}" if job["status"] == "done" else None})
        if job["status"] != "done":
            return self.send_json(409, {"error": "not_ready"})
        path = ROOT / jid / "preview.mp4"
        if not path.is_file():
            return self.send_json(404, {"error": "missing_file"})
        self.send_response(200)
        self.send_header("Content-Type", "video/mp4")
        self.send_header("Content-Disposition", 'attachment; filename="tcg-preview.mp4"')
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Cache-Control", "private, max-age=300")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        with path.open("rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def do_POST(self):
        cleanup()
        if urlsplit(self.path).path != "/render":
            return self.send_json(404, {"error": "not_found"})
        if not API_KEY:
            return self.send_json(503, {"error": "RENDER_API_KEY_not_configured"})
        provided = self.headers.get("X-API-Key", "")
        if not hmac.compare_digest(provided, API_KEY):
            return self.send_json(401, {"error": "unauthorized"})
        try:
            size = int(self.headers.get("Content-Length", "-1"))
            if not 0 < size <= 32768:
                return self.send_json(413, {"error": "request_too_large_or_missing_length"})
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            scenes = validate_manifest(data)
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as ex:
            return self.send_json(400, {"error": "invalid_manifest", "detail": str(ex)[:180]})
        with LOCK:
            if any(job["status"] in ("queued", "rendering") for job in JOBS.values()):
                return self.send_json(429, {"error": "renderer_busy"})
            jid = secrets.token_urlsafe(24)
            JOBS[jid] = {"created": time.time(), "status": "rendering"}
        threading.Thread(target=render, args=(jid, scenes), daemon=True).start()
        self.send_json(202, {"job_id": jid, "status": "rendering", "status_path": f"/status/{jid}"})


if __name__ == "__main__":
    print(f"TCG renderer listening on {PORT}; render_enabled={bool(API_KEY)}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()

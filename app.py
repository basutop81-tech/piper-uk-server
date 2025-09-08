import io, math, subprocess, tempfile, os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal

app = FastAPI(title="Local Piper TTS")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # OK for local dev; lock down later
    allow_methods=["*"],
    allow_headers=["*"],
)


# Voice files (UK English, male)
VOICE_DIR = os.environ.get("VOICE_DIR", "voices/en_GB/northern_english_male/medium")
MODEL = os.path.join(VOICE_DIR, "en_GB-northern_english_male-medium.onnx")
CONFIG = os.path.join(VOICE_DIR, "en_GB-northern_english_male-medium.onnx.json")

# Path to piper and (optional) ffmpeg inside the container/VM
PIPER = os.environ.get("PIPER_BIN", "/usr/local/bin/piper")
FFMPEG = os.environ.get("FFMPEG_BIN", "/usr/bin/ffmpeg")  # used only if MP3 requested

class TTSRequest(BaseModel):
    text: str
    format: Literal["wav","mp3"] = "wav"
    rate: float = 1.0  # 0.5–2.0 from your UI (1.0 = normal)

@app.post("/api/tts")
def synthesize(req: TTSRequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "Missing text.")
    if not (0.5 <= req.rate <= 2.0):
        raise HTTPException(400, "rate must be between 0.5 and 2.0")

    # Piper's "length_scale": smaller => faster. We'll invert your rate.
    # rate=2.0 (fast) -> length_scale=0.5 ; rate=0.5 (slow) -> length_scale=2.0
    length_scale = max(0.25, min(4.0, 1.0 / req.rate))

    # Synthesize WAV to stdout
    try:
        piper_cmd = [
            PIPER, "--model", MODEL, "--config", CONFIG,
            "--length_scale", str(length_scale),
            "--output_file", "-"  # stdout
        ]
        p = subprocess.Popen(piper_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        wav_bytes, err = p.communicate(input=text.encode("utf-8"))
        if p.returncode != 0 or not wav_bytes:
            raise RuntimeError(err.decode("utf-8", errors="ignore") or "Piper failed.")
    except Exception as e:
        raise HTTPException(500, f"Piper error: {e}")

    # If WAV requested, stream it back directly
    if req.format == "wav":
        return StreamingResponse(io.BytesIO(wav_bytes), media_type="audio/wav",
                                 headers={"Content-Disposition": 'attachment; filename="speech.wav"'})

    # Otherwise, transcode to MP3 with ffmpeg (if present)
    if not os.path.exists(FFMPEG):
        # graceful fallback to WAV if ffmpeg is unavailable
        return StreamingResponse(io.BytesIO(wav_bytes), media_type="audio/wav",
                                 headers={"Content-Disposition": 'attachment; filename="speech.wav"'})

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_in:
        f_in.write(wav_bytes); f_in.flush()
        out_path = f_in.name.replace(".wav", ".mp3")

    try:
        ff = subprocess.run([FFMPEG, "-y", "-i", f_in.name, "-b:a", "192k", out_path],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if ff.returncode != 0 or not os.path.exists(out_path):
            raise RuntimeError(ff.stderr.decode("utf-8", errors="ignore"))
        with open(out_path, "rb") as f:
            mp3 = f.read()
        return StreamingResponse(io.BytesIO(mp3), media_type="audio/mpeg",
                                 headers={"Content-Disposition": 'attachment; filename="speech.mp3"'})
    finally:
        try: os.remove(f_in.name)
        except: pass
        try: os.remove(out_path)
        except: pass

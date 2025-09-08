import io, os, re, subprocess, tempfile, wave
from typing import Literal, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Local Piper TTS (chunked + stitched)")

# --- CORS so your site can call the API ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # OK for dev; lock to your domain later
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Paths (set by Dockerfile or env) ---
VOICE_DIR = os.environ.get("VOICE_DIR", "/app/voices/en_GB/northern_english_male/medium")
MODEL = os.path.join(VOICE_DIR, "en_GB-northern_english_male-medium.onnx")
CONFIG = os.path.join(VOICE_DIR, "en_GB-northern_english_male-medium.onnx.json")
PIPER = os.environ.get("PIPER_BIN", "/usr/local/bin/piper/piper")  # <- correct binary path
FFMPEG = os.environ.get("FFMPEG_BIN", "/usr/bin/ffmpeg")           # optional (for mp3)

# --- Request model ---
class TTSRequest(BaseModel):
    text: str
    format: Literal["wav","mp3"] = "wav"
    rate: float = 1.0            # 0.5–2.0 (UI slider)

# --- Helpers ---
def chunk_text_serverside(text: str, max_len: int = 400) -> List[str]:
    """
    Split text into digestible parts, preferring sentence boundaries.
    """
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    # First split by sentence punctuation
    parts = re.split(r"(?<=[\.\?\!\:\;])\s+", text)
    chunks: List[str] = []
    cur = ""

    for part in parts:
        if not cur:
            cur = part
        elif len(cur) + 1 + len(part) <= max_len:
            cur += " " + part
        else:
            chunks.append(cur.strip())
            cur = part
    if cur.strip():
        chunks.append(cur.strip())

    # If any chunk is still too big, do a softer split on spaces
    final: List[str] = []
    for ch in chunks:
        if len(ch) <= max_len:
            final.append(ch)
        else:
            start = 0
            while start < len(ch):
                end = min(start + max_len, len(ch))
                # try to break at last space
                sp = ch.rfind(" ", start, end)
                if sp == -1 or sp <= start + 40:  # avoid tiny trailing fragment
                    sp = end
                final.append(ch[start:sp].strip())
                start = sp
    return [c for c in final if c]

def piper_wav_bytes(text: str, length_scale: float) -> bytes:
    """
    Call Piper once and return WAV bytes for a single chunk.
    """
    try:
        cmd = [
            PIPER, "--model", MODEL, "--config", CONFIG,
            "--length_scale", str(length_scale),
            "--output_file", "-"   # stdout WAV
        ]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        wav_bytes, err = p.communicate(input=text.encode("utf-8"))
        if p.returncode != 0 or not wav_bytes:
            raise RuntimeError(err.decode("utf-8", errors="ignore") or "Piper failed.")
        return wav_bytes
    except Exception as e:
        raise RuntimeError(f"Piper error: {e}")

def stitch_wavs(wav_list: List[bytes], pad_ms: int = 120) -> bytes:
    """
    Concatenate WAV files (same format) and insert a short silence between chunks.
    """
    if not wav_list:
        return b""

    # Read params from the first wav
    first = wave.open(io.BytesIO(wav_list[0]), "rb")
    n_channels = first.getnchannels()
    sampwidth = first.getsampwidth()
    framerate = first.getframerate()
    comptype = first.getcomptype()
    compname = first.getcompname()
    frames = [first.readframes(first.getnframes())]
    first.close()

    # Prepare silence pad
    pad_frames = int((pad_ms / 1000.0) * framerate)
    silence = (b"\x00" * sampwidth) * n_channels * pad_frames

    # Collect frames from the rest
    for wb in wav_list[1:]:
        w = wave.open(io.BytesIO(wb), "rb")
        # Basic safety: ensure consistent params
        if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (n_channels, sampwidth, framerate):
            w.close()
            raise RuntimeError("Chunk WAV parameters differ; cannot stitch.")
        frames.append(silence)
        frames.append(w.readframes(w.getnframes()))
        w.close()

    # Write final WAV
    out = io.BytesIO()
    wout = wave.open(out, "wb")
    wout.setnchannels(n_channels)
    wout.setsampwidth(sampwidth)
    wout.setframerate(framerate)
    wout.setcomptype(comptype, compname)
    for fr in frames:
        wout.writeframes(fr)
    wout.close()
    out.seek(0)
    return out.read()

@app.get("/")
def root():
    return {"ok": True, "message": "Piper TTS is running. Use POST /api/tts or visit /docs."}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/tts")
def synthesize(req: TTSRequest):
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(400, "Missing text.")
    if not (0.5 <= req.rate <= 2.0):
        raise HTTPException(400, "rate must be between 0.5 and 2.0")

    # Map your UI rate to Piper's length_scale
    length_scale = max(0.25, min(4.0, 1.0 / req.rate))

    # --- server-side chunking ---
    chunks = chunk_text_serverside(text, max_len=450)  # a bit larger than your UI chunks
    if not chunks:
        raise HTTPException(400, "No speakable text.")

    # Synthesize each chunk and stitch
    wav_parts: List[bytes] = []
    try:
        for ch in chunks:
            wav_parts.append(piper_wav_bytes(ch, length_scale))
    except Exception as e:
        raise HTTPException(500, str(e))

    full_wav = stitch_wavs(wav_parts, pad_ms=120)

    # WAV response straight away
    if req.format == "wav":
        return StreamingResponse(io.BytesIO(full_wav), media_type="audio/wav",
                                 headers={"Content-Disposition": 'attachment; filename="speech.wav"'})

    # MP3 transcode (if ffmpeg available), else fall back to WAV
    if not os.path.exists(FFMPEG):
        return StreamingResponse(io.BytesIO(full_wav), media_type="audio/wav",
                                 headers={"Content-Disposition": 'attachment; filename="speech.wav"'})

    with tempfile.TemporaryDirectory() as td:
        in_path = os.path.join(td, "in.wav")
        out_path = os.path.join(td, "out.mp3")
        with open(in_path, "wb") as f:
            f.write(full_wav)
        ff = subprocess.run([FFMPEG, "-y", "-i", in_path, "-b:a", "192k", out_path],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if ff.returncode != 0 or not os.path.exists(out_path):
            # fall back to WAV
            return StreamingResponse(io.BytesIO(full_wav), media_type="audio/wav",
                                     headers={"Content-Disposition": 'attachment; filename="speech.wav"'})
        with open(out_path, "rb") as f:
            mp3 = f.read()
    return StreamingResponse(io.BytesIO(mp3), media_type="audio/mpeg",
                             headers={"Content-Disposition": 'attachment; filename="speech.mp3"'})

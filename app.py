import io, os, re, subprocess, tempfile, wave
from typing import Literal, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Piper TTS (multi-voice, stitched + pitch)")

# Allow your front-end to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # For dev; lock to your domain(s) in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Binaries
PIPER  = os.environ.get("PIPER_BIN",  "/usr/local/bin/piper/piper")
FFMPEG = os.environ.get("FFMPEG_BIN", "/usr/bin/ffmpeg")

# Available voices (paths follow rhasspy/piper-voices layout)
VOICE_MAP = {
    "Anna":   {"dir": "/app/voices/en_US/hfc_female/medium",                 "model":"en_US-hfc_female-medium.onnx",                    "config":"en_US-hfc_female-medium.onnx.json"},
    "amy":          {"dir": "/app/voices/en_US/amy/medium",                         "model":"en_US-amy-medium.onnx",                           "config":"en_US-amy-medium.onnx.json"},
    "alba":         {"dir": "/app/voices/en_GB/alba/medium",                        "model":"en_GB-alba-medium.onnx",                          "config":"en_GB-alba-medium.onnx.json"},
    "northern_male":{"dir": "/app/voices/en_GB/northern_english_male/medium",      "model":"en_GB-northern_english_male-medium.onnx",         "config":"en_GB-northern_english_male-medium.onnx.json"},
    "davefx":       {"dir": "/app/voices/es_ES/davefx/medium",                      "model":"es_ES-davefx-medium.onnx",                        "config":"es_ES-davefx-medium.onnx.json"},
    "pratham":      {"dir": "/app/voices/hi_IN/pratham/medium",                     "model":"hi_IN-pratham-medium.onnx",                       "config":"hi_IN-pratham-medium.onnx.json"},
    "paola":        {"dir": "/app/voices/it_IT/paola/medium",                       "model":"it_IT-paola-medium.onnx",                         "config":"it_IT-paola-medium.onnx.json"},
    "thorsten":     {"dir": "/app/voices/de_DE/thorsten/medium",                    "model":"de_DE-thorsten-medium.onnx",                      "config":"de_DE-thorsten-medium.onnx.json"},
    "kareem":       {"dir": "/app/voices/ar_JO/kareem/low",                         "model":"ar_JO-kareem-low.onnx",                           "config":"ar_JO-kareem-low.onnx.json"},
    "gyro":         {"dir": "/app/voices/fa_IR/gyro/medium",                        "model":"fa_IR-gyro-medium.onnx",                          "config":"fa_IR-gyro-medium.onnx.json"},
    "siwis":        {"dir": "/app/voices/fr_FR/siwis/medium",                       "model":"fr_FR-siwis-medium.onnx",                         "config":"fr_FR-siwis-medium.onnx.json"},
    "nathalie":     {"dir": "/app/voices/nl_BE/nathalie/medium",                    "model":"nl_BE-nathalie-medium.onnx",                      "config":"nl_BE-nathalie-medium.onnx.json"},
    "mc_speech":    {"dir": "/app/voices/pl_PL/mc_speech/medium",                   "model":"pl_PL-mc_speech-medium.onnx",                     "config":"pl_PL-mc_speech-medium.onnx.json"},
    "faber":        {"dir": "/app/voices/pt_BR/faber/medium",                       "model":"pt_BR-faber-medium.onnx",                         "config":"pt_BR-faber-medium.onnx.json"},
    "irina":        {"dir": "/app/voices/ru_RU/irina/medium",                       "model":"ru_RU-irina-medium.onnx",                         "config":"ru_RU-irina-medium.onnx.json"},
    "vais1000":     {"dir": "/app/voices/vi_VN/vais1000/medium",                    "model":"vi_VN-vais1000-medium.onnx",                      "config":"vi_VN-vais1000-medium.onnx.json"},
    "huayan":       {"dir": "/app/voices/zh_CN/huayan/medium",                      "model":"zh_CN-huayan-medium.onnx",                        "config":"zh_CN-huayan-medium.onnx.json"},
}

class TTSRequest(BaseModel):
    text: str
    format: Literal["wav","mp3"] = "wav"
    rate: float = 1.0              # speed (0.5–2.0)
    pitch: float = 1.0             # NEW (0.5–2.0)
    volume: Optional[float] = 1.0  # reserved (you can map to gain if desired)
    voice: Literal[
        "hfc_female","amy","alba","northern_male","davefx","pratham","paola",
        "thorsten","kareem","gyro","siwis","nathalie","mc_speech","faber",
        "irina","vais1000","huayan"
    ] = "hfc_female"

def chunk_text_serverside(text: str, max_len: int = 450) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[\.\?\!\:\;])\s+", text)
    chunks, cur = [], ""
    for part in parts:
        if not cur:
            cur = part
        elif len(cur) + 1 + len(part) <= max_len:
            cur += " " + part
        else:
            chunks.append(cur.strip()); cur = part
    if cur.strip():
        chunks.append(cur.strip())
    final = []
    for ch in chunks:
        if len(ch) <= max_len:
            final.append(ch)
        else:
            start = 0
            while start < len(ch):
                end = min(start + max_len, len(ch))
                sp = ch.rfind(" ", start, end)
                if sp == -1 or sp <= start + 40:
                    sp = end
                final.append(ch[start:sp].strip())
                start = sp
    return [c for c in final if c]

def piper_wav_bytes(text: str, length_scale: float, model_path: str, config_path: str) -> bytes:
    cmd = [
        PIPER, "--model", model_path, "--config", config_path,
        "--length_scale", str(length_scale),
        "--output_file", "-"
    ]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    wav_bytes, err = p.communicate(input=text.encode("utf-8"))
    if p.returncode != 0 or not wav_bytes:
        raise RuntimeError(err.decode("utf-8", errors="ignore") or "Piper failed.")
    return wav_bytes

def stitch_wavs(wav_list: List[bytes], pad_ms: int = 120) -> bytes:
    if not wav_list:
        return b""
    first = wave.open(io.BytesIO(wav_list[0]), "rb")
    n_channels, sampwidth, framerate = first.getnchannels(), first.getsampwidth(), first.getframerate()
    comptype, compname = first.getcomptype(), first.getcompname()
    frames = [first.readframes(first.getnframes())]
    first.close()
    pad_frames = int((pad_ms / 1000.0) * framerate)
    silence = (b"\x00" * sampwidth) * n_channels * pad_frames
    for wb in wav_list[1:]:
        w = wave.open(io.BytesIO(wb), "rb")
        if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (n_channels, sampwidth, framerate):
            w.close(); raise RuntimeError("Chunk WAV params differ")
        frames.append(silence); frames.append(w.readframes(w.getnframes()))
        w.close()
    out = io.BytesIO()
    wout = wave.open(out, "wb")
    wout.setnchannels(n_channels); wout.setsampwidth(sampwidth); wout.setframerate(framerate)
    wout.setcomptype(comptype, compname)
    for fr in frames: wout.writeframes(fr)
    wout.close(); out.seek(0)
    return out.read()

@app.get("/")
def root():
    return {"ok": True, "message": "Piper TTS running. Use POST /api/tts or /docs."}

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
    if not (0.5 <= req.pitch <= 2.0):
        raise HTTPException(400, "pitch must be between 0.5 and 2.0")

    length_scale = max(0.25, min(4.0, 1.0 / req.rate))

    if req.voice not in VOICE_MAP:
        raise HTTPException(400, f"Voice {req.voice} not available.")
    vinfo = VOICE_MAP[req.voice]
    model_path = os.path.join(vinfo["dir"], vinfo["model"])
    config_path = os.path.join(vinfo["dir"], vinfo["config"])

    chunks = chunk_text_serverside(text, max_len=450)
    if not chunks:
        raise HTTPException(400, "No speakable text.")

    wav_parts = [piper_wav_bytes(ch, length_scale, model_path, config_path) for ch in chunks]
    full_wav = stitch_wavs(wav_parts)

    # Pitch shift using ffmpeg (keep duration roughly same)
    if abs(req.pitch - 1.0) > 1e-3 and os.path.exists(FFMPEG):
        with tempfile.TemporaryDirectory() as td:
            in_wav  = os.path.join(td, "in.wav")
            out_wav = os.path.join(td, "pitch.wav")
            with open(in_wav, "wb") as f: f.write(full_wav)
            p = max(0.5, min(2.0, req.pitch))
            cmd = [
                FFMPEG, "-y", "-i", in_wav,
                "-filter:a", f"asetrate=22050*{p},aresample=22050,atempo={1/p}",
                out_wav
            ]
            ff = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if ff.returncode == 0 and os.path.exists(out_wav):
                with open(out_wav, "rb") as f: full_wav = f.read()

    # Return WAV or MP3
    if req.format == "wav":
        return StreamingResponse(io.BytesIO(full_wav), media_type="audio/wav",
                                 headers={"Content-Disposition": 'attachment; filename="speech.wav"'})

    if not os.path.exists(FFMPEG):
        return StreamingResponse(io.BytesIO(full_wav), media_type="audio/wav",
                                 headers={"Content-Disposition": 'attachment; filename="speech.wav"'})

    with tempfile.TemporaryDirectory() as td:
        in_path, out_path = os.path.join(td, "in.wav"), os.path.join(td, "out.mp3")
        with open(in_path, "wb") as f: f.write(full_wav)
        ff = subprocess.run([FFMPEG, "-y", "-i", in_path, "-b:a", "192k", out_path],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if ff.returncode != 0 or not os.path.exists(out_path):
            return StreamingResponse(io.BytesIO(full_wav), media_type="audio/wav",
                                     headers={"Content-Disposition": 'attachment; filename="speech.wav"'})
        with open(out_path, "rb") as f: mp3 = f.read()
    return StreamingResponse(io.BytesIO(mp3), media_type="audio/mpeg",
                             headers={"Content-Disposition": 'attachment; filename="speech.mp3"'})




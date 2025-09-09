FROM python:3.11-slim

# OS deps (curl, ffmpeg for MP3, libstdc++ etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates coreutils ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Piper binary
RUN curl -L -o /tmp/piper.tar.gz https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz \
    && tar -xzf /tmp/piper.tar.gz -C /usr/local/bin \
    && rm /tmp/piper.tar.gz \
    && chmod +x /usr/local/bin/piper/piper

# Add voice (UK English male) – model + config
RUN mkdir -p /app/voices/en_GB/northern_english_male/medium
WORKDIR /app/voices/en_GB/northern_english_male/medium
# ONNX + JSON from official piper-voices (Hugging Face)
RUN curl -L -o en_GB-northern_english_male-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx \
  && curl -L -o en_GB-northern_english_male-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx.json

# App
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py ./

ENV VOICE_DIR=/app/voices/en_GB/northern_english_male/medium
ENV PIPER_BIN=/usr/local/bin/piper/piper
ENV FFMPEG_BIN=/usr/bin/ffmpeg

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

# Voice 1: en_US hfc_female medium
RUN mkdir -p /app/voices/en_US/hfc_female/medium \
  && curl -L -o /app/voices/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx \
       https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx \
  && curl -L -o /app/voices/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx.json \
       https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx.json

# Voice 2: en_GB northern_english_male medium
RUN mkdir -p /app/voices/en_GB/northern_english_male/medium \
  && curl -L -o /app/voices/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx \
       https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx \
  && curl -L -o /app/voices/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx.json \
       https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx.json

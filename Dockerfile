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

# === Piper voices ===
# US English
RUN mkdir -p /app/voices/en_US/hfc_female/medium && \
    curl -L -o /app/voices/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx && \
    curl -L -o /app/voices/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_female/medium/en_US-hfc_female-medium.onnx.json

RUN mkdir -p /app/voices/en_US/amy/medium && \
    curl -L -o /app/voices/en_US/amy/medium/en_US-amy-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx && \
    curl -L -o /app/voices/en_US/amy/medium/en_US-amy-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json

# UK English
RUN mkdir -p /app/voices/en_GB/alba/medium && \
    curl -L -o /app/voices/en_GB/alba/medium/en_GB-alba-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium/en_GB-alba-medium.onnx && \
    curl -L -o /app/voices/en_GB/alba/medium/en_GB-alba-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alba/medium/en_GB-alba-medium.onnx.json

RUN mkdir -p /app/voices/en_GB/northern_english_male/medium && \
    curl -L -o /app/voices/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx && \
    curl -L -o /app/voices/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/northern_english_male/medium/en_GB-northern_english_male-medium.onnx.json

# Spanish (Spain)
RUN mkdir -p /app/voices/es_ES/davefx/medium && \
    curl -L -o /app/voices/es_ES/davefx/medium/es_ES-davefx-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx && \
    curl -L -o /app/voices/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json

# Hindi
RUN mkdir -p /app/voices/hi_IN/pratham/medium && \
    curl -L -o /app/voices/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx && \
    curl -L -o /app/voices/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx.json

# Italian
RUN mkdir -p /app/voices/it_IT/paola/medium && \
    curl -L -o /app/voices/it_IT/paola/medium/it_IT-paola-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx && \
    curl -L -o /app/voices/it_IT/paola/medium/it_IT-paola-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/it/it_IT/paola/medium/it_IT-paola-medium.onnx.json

# German
RUN mkdir -p /app/voices/de_DE/thorsten/medium && \
    curl -L -o /app/voices/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx && \
    curl -L -o /app/voices/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx.json

# Arabic (Jordan)
RUN mkdir -p /app/voices/ar_JO/kareem/low && \
    curl -L -o /app/voices/ar_JO/kareem/low/ar_JO-kareem-low.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/ar/ar_JO/kareem/low/ar_JO-kareem-low.onnx && \
    curl -L -o /app/voices/ar_JO/kareem/low/ar_JO-kareem-low.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/ar/ar_JO/kareem/low/ar_JO-kareem-low.onnx.json

# Persian (Iran)
RUN mkdir -p /app/voices/fa_IR/gyro/medium && \
    curl -L -o /app/voices/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/fa/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx && \
    curl -L -o /app/voices/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/fa/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx.json

# French (France)
RUN mkdir -p /app/voices/fr_FR/siwis/medium && \
    curl -L -o /app/voices/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx && \
    curl -L -o /app/voices/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx.json

# Dutch (Belgium)
RUN mkdir -p /app/voices/nl_BE/nathalie/medium && \
    curl -L -o /app/voices/nl_BE/nathalie/medium/nl_BE-nathalie-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/nl/nl_BE/nathalie/medium/nl_BE-nathalie-medium.onnx && \
    curl -L -o /app/voices/nl_BE/nathalie/medium/nl_BE-nathalie-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/nl/nl_BE/nathalie/medium/nl_BE-nathalie-medium.onnx.json

# Polish
RUN mkdir -p /app/voices/pl_PL/mc_speech/medium && \
    curl -L -o /app/voices/pl_PL/mc_speech/medium/pl_PL-mc_speech-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/pl/pl_PL/mc_speech/medium/pl_PL-mc_speech-medium.onnx && \
    curl -L -o /app/voices/pl_PL/mc_speech/medium/pl_PL-mc_speech-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/pl/pl_PL/mc_speech/medium/pl_PL-mc_speech-medium.onnx.json

# Portuguese (Brazil)
RUN mkdir -p /app/voices/pt_BR/faber/medium && \
    curl -L -o /app/voices/pt_BR/faber/medium/pt_BR-faber-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx && \
    curl -L -o /app/voices/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json

# Russian
RUN mkdir -p /app/voices/ru_RU/irina/medium && \
    curl -L -o /app/voices/ru_RU/irina/medium/ru_RU-irina-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx && \
    curl -L -o /app/voices/ru_RU/irina/medium/ru_RU-irina-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/ru/ru_RU/irina/medium/ru_RU-irina-medium.onnx.json

# Vietnamese
RUN mkdir -p /app/voices/vi_VN/vais1000/medium && \
    curl -L -o /app/voices/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx && \
    curl -L -o /app/voices/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/vi/vi_VN/vais1000/medium/vi_VN-vais1000-medium.onnx.json

# Chinese (Simplified)
RUN mkdir -p /app/voices/zh_CN/huayan/medium && \
    curl -L -o /app/voices/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx && \
    curl -L -o /app/voices/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json \
    https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json

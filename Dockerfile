# Dockerfile para Gerador de Podcast TTS

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Install system dependencies (incluindo dependências para PyTorch/TTS)
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev \
    nodejs npm \
    ffmpeg curl wget git \
    build-essential libsndfile1 \
    libffi-dev libssl-dev \
    espeak espeak-data libespeak1 libespeak-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Create user
RUN useradd -m -u 1000 podcast && \
    mkdir -p /home/podcast/.local/share/piper-tts && \
    mkdir -p /home/podcast/.cache/tts && \
    chown -R podcast:podcast /home/podcast

WORKDIR /app

# Copy and install Python dependencies (em etapas para melhor cache)
COPY requirements.txt /app/

# Atualizar setuptools e pip primeiro para evitar conflitos
RUN pip3 install --no-cache-dir --upgrade pip setuptools>=67.0.0 wheel

# Instalar PyTorch primeiro (base)
RUN pip3 install --no-cache-dir torch>=1.13.0,\<2.1.0 torchaudio>=0.13.0,\<2.1.0 --index-url https://download.pytorch.org/whl/cpu

# Instalar dependências de áudio
RUN pip3 install --no-cache-dir numpy scipy librosa soundfile

# Instalar TTS com exclusões específicas
RUN pip3 install --no-cache-dir TTS==0.21.3 --no-deps && \
    pip3 install --no-cache-dir inflect unidecode phonemizer

# Instalar demais dependências
RUN pip3 install --no-cache-dir piper-tts PyYAML typing-extensions regex

# Copy and install Node.js dependencies  
COPY package.json /app/
RUN npm install --production

# Copy application code
COPY src/ /app/src/
COPY config/ /app/config/
COPY scripts/ /app/scripts/
COPY static/ /app/static/
COPY templates/ /app/templates/
COPY *.py /app/
COPY *.js /app/

# Create directories
RUN mkdir -p /app/output/{final,segments,temp} /app/uploads && \
    chown -R podcast:podcast /app

# Download Piper models
USER podcast
RUN cd /home/podcast/.local/share/piper-tts && \
    curl -L -o pt_BR-faber-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx" && \
    curl -L -o pt_BR-faber-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json"

# Configurar variáveis de ambiente para TTS
ENV TTS_CACHE_DIR=/home/podcast/.cache/tts
ENV HF_HOME=/home/podcast/.cache/huggingface

USER root
EXPOSE 3000
CMD ["node", "server.js"]

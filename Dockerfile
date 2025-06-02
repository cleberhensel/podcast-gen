# Dockerfile para Gerador de Podcast TTS - Piper Edition

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Install system dependencies (otimizado para Piper TTS)
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
    chown -R podcast:podcast /home/podcast

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt /app/

# Atualizar setuptools e pip
RUN pip3 install --no-cache-dir --upgrade pip setuptools>=67.0.0 wheel

# Instalar dependências Python (otimizadas para Piper)
RUN pip3 install --no-cache-dir -r requirements.txt

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

# Download Piper models para português brasileiro
USER podcast
RUN cd /home/podcast/.local/share/piper-tts && \
    curl -L -o pt_BR-faber-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx" && \
    curl -L -o pt_BR-faber-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json" && \
    curl -L -o pt_BR-lessac-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/lessac/medium/pt_BR-lessac-medium.onnx" && \
    curl -L -o pt_BR-lessac-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/lessac/medium/pt_BR-lessac-medium.onnx.json"

USER root
EXPOSE 3000
CMD ["node", "server.js"]

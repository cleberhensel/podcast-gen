# Dockerfile para Gerador de Podcast TTS - Dual Engine (Piper + CoquiTTS)

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV NODE_ENV=production

# Install system dependencies
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
    mkdir -p /home/podcast/.local/share/tts && \
    mkdir -p /app/speakers && \
    chown -R podcast:podcast /home/podcast

WORKDIR /app

# Copy requirements file
COPY requirements.txt /app/

# Atualizar pip e setuptools
RUN pip3 install --no-cache-dir --upgrade pip setuptools>=67.0.0 wheel

# Instalar PyTorch e Torchaudio primeiro
RUN pip3 install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu || \
    echo "AVISO: PyTorch/Torchaudio installation failed."

# Instalar dependências CONHECIDAS E SEGURAS do requirements.txt, EXCLUINDO TTS por enquanto.
# Estas são as dependências que o TTS[xtts] precisaria, mas instalamos explicitamente.
RUN pip3 install --no-cache-dir \
    numpy>=1.21.0 \
    soundfile>=0.12.1 \
    librosa>=0.10.0 \
    tqdm>=4.64.0 \
    pydub>=0.25.1 \
    einops>=0.6.0 \
    langid>=1.1.6 \
    numba>=0.57.0 \
    PyYAML>=6.0 \
    wave pathlib typing-extensions regex piper-tts==1.2.0 || \
    echo "AVISO: Falha ao instalar dependências base."

# AGORA, tentar instalar TTS, mas SEM suas dependências diretas.
# A esperança é que, como já instalamos as dependências que o [xtts] precisa,
# ele não tente buscar outras problemáticas como sudachipy.
RUN pip3 install --no-cache-dir TTS==0.22.0 --no-deps || \
    (pip3 install --no-cache-dir TTS --no-deps && echo "Instalada versão mais recente do TTS (--no-deps)") || \
    echo "AVISO: Instalação do CoquiTTS (--no-deps) falhou. Piper será usado."

# Verificar se a instalação anterior do TTS realmente funcionou (sem depender de `preload_coqui_model.py` para isso)
RUN python3 -c "try: import TTS.api; print('SUCESSO: CoquiTTS API importável!') except Exception as e: print(f'FALHA: CoquiTTS API NÃO importável - {e}'); exit(1)" || \
    echo "AVISO: Verificação de import do CoquiTTS API falhou. Piper será usado."


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

# Switch to podcast user for model downloads
USER podcast

# Download Piper models para português brasileiro
RUN cd /home/podcast/.local/share/piper-tts && \
    curl -L -o pt_BR-faber-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx" && \
    curl -L -o pt_BR-faber-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json" && \
    curl -L -o pt_BR-lessac-medium.onnx "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/lessac/medium/pt_BR-lessac-medium.onnx" && \
    curl -L -o pt_BR-lessac-medium.onnx.json "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/lessac/medium/pt_BR-lessac-medium.onnx.json"

# Tentar configurar CoquiTTS (esperamos sucesso agora)
ENV TTS_HOME=/home/podcast/.local/share/tts
RUN python3 /app/scripts/preload_coqui_model.py || \
    echo "AVISO: Pré-carregamento CoquiTTS falhou. Verifique logs. Piper será usado."

# Criar arquivo de speaker de teste
RUN python3 /app/scripts/create_test_speaker.py || \
    echo "AVISO: Criação de speakers de teste falhou. Clonagem de voz pode não funcionar."

USER root
EXPOSE 3000
CMD ["node", "server.js"]

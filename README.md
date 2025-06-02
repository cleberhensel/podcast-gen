# 🎙️ Podcast Generator TTS - Sistema Avançado de Geração de Podcasts

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-green?logo=python)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-12+-brightgreen?logo=node.js)](https://nodejs.org)
[![TTS](https://img.shields.io/badge/TTS-Multi--Engine-purple)](https://github.com/coqui-ai/TTS)

Sistema profissional para geração automatizada de podcasts usando **3 engines TTS** de última geração: **Coqui XTTS v2**, **Piper TTS** e **macOS TTS**. Interface web moderna com upload de roteiros e download automático de MP3s.

## ✨ **Características Principais**

### 🎯 **Múltiplas Engines TTS**
- **🥇 Coqui XTTS v2** - Qualidade premium com clonagem de voz e 16+ idiomas
- **🥈 Piper TTS** - Engine neural rápido e eficiente (ONNX)
- **🥉 macOS TTS** - Backup nativo confiável

### 🚀 **Recursos Avançados**
- ✅ **Vozes Masculinas e Femininas** diferenciadas
- ✅ **Interface Web Moderna** com drag & drop
- ✅ **Processamento em Background** com status em tempo real
- ✅ **Fallback Automático** entre engines
- ✅ **Configuração Flexível** via YAML
- ✅ **Docker Ready** - Deploy em segundos
- ✅ **Download Automático** de modelos TTS
- ✅ **Suporte Multilingual** (PT-BR, EN, ES, FR, DE, etc.)

### 🎵 **Qualidades de Áudio**
- **Sample Rate**: 22kHz (Piper) / 24kHz (Coqui)
- **Formato**: WAV + MP3 (192kbps)
- **Processamento**: FFmpeg para otimização
- **Vozes**: Diferenciação automática por personagem

## 🛠️ **Tecnologias Utilizadas**

### Backend
- **Python 3.10+** - Core engine
- **Coqui TTS XTTS v2** - Neural TTS premium
- **Piper TTS** - Fast neural synthesis
- **PyTorch** - Deep learning framework
- **FFmpeg** - Audio processing
- **PyYAML** - Configuration management

### Frontend & API
- **Node.js + Express.js** - Web server
- **Bootstrap 5** - Modern UI
- **HTML5 File API** - Drag & drop uploads
- **JavaScript ES6+** - Dynamic interface

### Infrastructure
- **Docker** - Containerization
- **Ubuntu 22.04** - Base image
- **Podman/Docker** - Container runtime

## 🚀 **Quick Start**

### Pré-requisitos
- **Docker** ou **Podman**
- **4GB+ RAM** (recomendado 8GB para Coqui)
- **5GB+ espaço livre** para modelos

### 1️⃣ **Clone e Build**
```bash
git clone <repository-url>
cd podcast-docker

# Build da imagem (15-20 min na primeira vez)
podman build -t podcast-generator .
```

### 2️⃣ **Executar Container**
```bash
# Rodar em background
podman run -d --name podcast-generator -p 3000:3000 podcast-generator

# Verificar status
podman logs podcast-generator
```

### 3️⃣ **Acessar Interface**
```
🌐 Interface Web: http://localhost:3000
```

## 📝 **Formato do Roteiro**

Crie arquivos `.txt` com o seguinte formato:

```text
# Título do Podcast
Meu Podcast Sobre Tecnologia

# Personagens e diálogos
HOST_MALE: Olá pessoal! Bem-vindos ao nosso podcast de tecnologia.

HOST_FEMALE: Oi! Hoje vamos falar sobre inteligência artificial e suas aplicações.

HOST_MALE: Isso mesmo! A IA está revolucionando várias áreas...

HOST_FEMALE: Vamos começar falando sobre machine learning.
```

### 🎭 **Personagens Suportados**
- `HOST_MALE` / `HOST_FEMALE` - Apresentadores
- `EXPERT_MALE` / `EXPERT_FEMALE` - Especialistas  
- `GUEST_MALE` / `GUEST_FEMALE` - Convidados
- `NARRATOR_MALE` / `NARRATOR_FEMALE` - Narradores

## ⚙️ **Configuração Avançada**

### 📁 **Estrutura de Arquivos**
```
podcast-docker/
├── src/                    # Código Python
│   ├── engines/           # Engines TTS
│   │   ├── coqui_tts.py  # Coqui XTTS engine
│   │   ├── piper_tts.py  # Piper TTS engine
│   │   └── macos_tts.py  # macOS TTS engine
│   ├── core/             # Core logic
│   └── models/           # Data models
├── config/
│   └── settings.yaml     # Configurações principais
├── static/               # Frontend assets
├── templates/            # HTML templates
├── scripts/              # Roteiros exemplo
└── output/               # Arquivos gerados
```

### 🔧 **settings.yaml**
```yaml
engines:
  default: "coqui"        # Engine padrão
  
  coqui:
    enabled: true
    model_name: "tts_models/multilingual/multi-dataset/xtts_v2"
    language: "pt"
    temperature: 0.7      # Criatividade vs estabilidade
    
  piper:
    enabled: true
    quality: "medium"
    
  macos:
    enabled: true
    default_rate: 200
```

## 🎙️ **Engines TTS Detalhadas**

### 🥇 **Coqui XTTS v2** *(Recomendado)*
- **Qualidade**: ⭐⭐⭐⭐⭐ Excelente
- **Velocidade**: ⭐⭐⭐ Média (~30s/min)
- **Recursos**: Clonagem de voz, 16+ idiomas, controle fino
- **Uso**: Produção profissional

**Configurações avançadas:**
```yaml
coqui:
  temperature: 0.7        # 0.1-1.0 (estabilidade vs criatividade)
  length_penalty: 1.0     # Controle de duração
  repetition_penalty: 2.0 # Evitar repetições
  top_k: 50              # Top-k sampling
  top_p: 0.85            # Top-p sampling
```

### 🥈 **Piper TTS**
- **Qualidade**: ⭐⭐⭐⭐ Muito Boa  
- **Velocidade**: ⭐⭐⭐⭐⭐ Muito Rápida (~5s/min)
- **Recursos**: Neural ONNX, modelos otimizados
- **Uso**: Produção rápida, testes

### 🥉 **macOS TTS**
- **Qualidade**: ⭐⭐⭐ Boa
- **Velocidade**: ⭐⭐⭐⭐⭐ Instantânea
- **Recursos**: Nativo, confiável
- **Uso**: Fallback, desenvolvimento

## 🔄 **Sistema de Fallback**

O sistema tenta engines nesta ordem:
1. **Coqui XTTS** (preferido)
2. **Piper TTS** (backup)  
3. **macOS TTS** (último recurso)

Se um engine falha, o próximo é usado automaticamente.

## 🐳 **Docker Detalhado**

### **Dockerfile Highlights**
```dockerfile
FROM ubuntu:22.04

# Instalar dependências
RUN apt-get update && apt-get install -y \
    python3 python3-pip nodejs npm ffmpeg \
    espeak espeak-data libespeak-dev

# Instalar PyTorch + Coqui TTS
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install TTS torch torchaudio

# Download automático modelos Piper
RUN curl -L -o pt_BR-faber-medium.onnx ...
```

### **docker-compose.yml**
```yaml
version: '3.8'
services:
  podcast-generator:
    build: .
    ports:
      - "3000:3000"
    volumes:
      - ./output:/app/output
    environment:
      - TTS_CACHE_DIR=/home/podcast/.cache/tts
```

## 🧪 **Testando o Sistema**

### **1. Verificar Engines**
```bash
podman exec podcast-generator python3 -c "
from src.engines.engine_factory import tts_factory
engines = tts_factory.get_available_engines()
print('🎙️ Engines disponíveis:', engines)

for engine in engines:
    info = tts_factory.get_engine_info(engine)
    print(f'   {engine}: {info.get(\"quality\", \"N/A\")} quality')
"
```

### **2. Teste Manual**
```bash
# Entrar no container
podman exec -it podcast-generator bash

# Gerar podcast de teste
python3 podcast_generator.py scripts/exemplo.txt --output-dir output/final --job-id test
```

### **3. Teste via API**
```bash
# Upload roteiro
curl -X POST -F "script=@scripts/exemplo.txt" http://localhost:3000/upload

# Verificar status
curl http://localhost:3000/status/<job-id>

# Download resultado
curl -O http://localhost:3000/download/<job-id>
```

## 📊 **Monitoramento & Logs**

### **Ver Logs**
```bash
# Logs completos
podman logs podcast-generator

# Logs em tempo real
podman logs -f podcast-generator

# Últimas 50 linhas
podman logs --tail 50 podcast-generator
```

### **Métricas do Container**
```bash
# Status do container
podman stats podcast-generator

# Informações detalhadas
podman inspect podcast-generator
```

## 🔧 **Troubleshooting**

### **Problemas Comuns**

#### ❌ "Coqui TTS não disponível"
```bash
# Verificar instalação
podman exec podcast-generator python3 -c "import TTS; print('✅ TTS OK')"

# Verificar modelos
podman exec podcast-generator ls -la /home/podcast/.cache/tts/
```

#### ❌ "Piper models not found"
```bash
# Verificar modelos Piper
podman exec podcast-generator ls -la /home/podcast/.local/share/piper-tts/

# Re-download se necessário
podman exec podcast-generator bash -c "cd /home/podcast/.local/share/piper-tts && curl -L -o ..."
```

#### ❌ "Port 3000 already in use"
```bash
# Verificar processos na porta
lsof -i :3000

# Rodar em porta diferente
podman run -p 3001:3000 podcast-generator
```

### **Reset Completo**
```bash
# Parar e remover container
podman stop podcast-generator
podman rm podcast-generator

# Remover imagem
podman rmi podcast-generator

# Rebuild from scratch
podman build --no-cache -t podcast-generator .
```

## 🚀 **Deployment em Produção**

### **Docker Compose**
```yaml
version: '3.8'
services:
  podcast-generator:
    build: .
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - podcast_output:/app/output
      - podcast_cache:/home/podcast/.cache
    environment:
      - NODE_ENV=production
      - TTS_CACHE_DIR=/home/podcast/.cache/tts
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  podcast_output:
  podcast_cache:
```

### **Reverse Proxy (Nginx)**
```nginx
server {
    listen 80;
    server_name podcast.example.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 10M;
    }
}
```

## 📈 **Performance & Otimização**

### **Recursos Recomendados**
- **CPU**: 4+ cores (8+ para Coqui XTTS)
- **RAM**: 8GB+ (16GB recomendado)
- **Storage**: 10GB+ para modelos
- **Network**: Boa conexão para download inicial

### **Otimizações**
```yaml
# settings.yaml
performance:
  parallel_synthesis: true
  max_workers: 4
  cache_enabled: true
  cache_size: 100  # MB

# Docker resource limits
deploy:
  resources:
    limits:
      memory: 8G
      cpus: '4'
```

## 🤝 **Contribuição**

1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-feature`
3. Commit: `git commit -m 'Adiciona nova feature'`
4. Push: `git push origin feature/nova-feature`
5. Pull Request

## 📝 **Changelog**

### v2.0.0 *(Current)*
- ✅ Adicionado Coqui XTTS v2
- ✅ Sistema multi-engine com fallback
- ✅ Interface web moderna
- ✅ Docker completo
- ✅ Suporte a 16+ idiomas

### v1.0.0
- ✅ Piper TTS + macOS TTS
- ✅ Processamento básico
- ✅ CLI interface

## 📄 **Licença**

MIT License - veja [LICENSE](LICENSE) para detalhes.

## 🙋‍♂️ **Suporte**

- 📧 **Issues**: [GitHub Issues](https://github.com/user/repo/issues)
- 💬 **Discussões**: [GitHub Discussions](https://github.com/user/repo/discussions)
- 📚 **Docs**: [Wiki](https://github.com/user/repo/wiki)

---

## ⭐ **Star o Projeto**

Se este projeto foi útil para você, considere dar uma ⭐!

---

**🎙️ Desenvolvido com ❤️ para a comunidade de criadores de conteúdo** 
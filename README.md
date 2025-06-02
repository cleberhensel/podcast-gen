# 🎙️ Podcast Generator TTS - Sistema Dockerizado para Geração de Podcasts

[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-18+-339933?logo=node.js&logoColor=white)](https://nodejs.org)
[![Piper TTS](https://img.shields.io/badge/TTS-Piper-9146FF)](https://github.com/rhasspy/piper)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Sistema profissional e dockerizado para geração automatizada de podcasts usando Piper TTS e interface web moderna. Deploy em segundos em qualquer computador!**

## 🌟 **Por que este projeto?**

Este sistema foi desenvolvido para democratizar a criação de podcasts de alta qualidade, oferecendo:

- **✅ Deploy Instantâneo**: Execute em qualquer máquina com Docker em menos de 2 minutos
- **✅ Vozes Naturais**: Piper TTS com modelos neurais otimizados para português brasileiro  
- **✅ Interface Moderna**: Web UI responsiva com drag & drop de arquivos
- **✅ Processamento Robusto**: Pipeline completo de áudio com normalização e otimização
- **✅ Zero Configuração**: Baixa modelos automaticamente, funciona out-of-the-box

## 🚀 **Quick Start - Docker**

### **Pré-requisitos**
- **Docker** ou **Podman** instalado
- **4GB RAM** disponível (recomendado)
- **3GB espaço livre** (para modelos e cache)

### **1️⃣ Clone e Execute**
```bash
# Clone o repositório
git clone <repository-url>
cd podcast-docker

# Build e execute com Docker Compose (recomendado)
docker-compose up --build -d

# OU execute manualmente
docker build -t podcast-generator .
docker run -d --name podcast-generator -p 3000:3000 podcast-generator
```

### **2️⃣ Acesse a Interface**
```
🌐 http://localhost:3000
```

### **3️⃣ Gere seu Primeiro Podcast**
1. Faça upload de um arquivo `.txt` com o roteiro
2. Aguarde o processamento (2-5 minutos)
3. Baixe o MP3 gerado automaticamente

**É isso! Seu podcast está pronto! 🎉**

## 📝 **Formato do Roteiro**

O sistema aceita arquivos `.txt` com formato simples e intuitivo:

```text
# Título do Podcast
Game Dev Masters - Aula 2: Geometrias Primitivas

[HOST_MALE]: Olá pessoal! Aqui é o Paulo, bem-vindos ao Game Dev Masters!

[HOST_FEMALE]: Oi Paulo! Ana aqui, e hoje vamos falar sobre geometrias primitivas do Three.js!

[HOST_MALE]: Perfeita escolha! Essas formas básicas são fundamentais para qualquer desenvolvedor.

[HOST_FEMALE]: Exato! Vamos começar com BoxGeometry e suas aplicações práticas.
```

### **🎭 Personagens Suportados**
- `[HOST_MALE]` / `[HOST_FEMALE]` - Apresentadores principais
- `[EXPERT_MALE]` / `[EXPERT_FEMALE]` - Especialistas técnicos  
- `[GUEST_MALE]` / `[GUEST_FEMALE]` - Convidados especiais
- `[NARRATOR_MALE]` / `[NARRATOR_FEMALE]` - Narradores

### **🎵 Vozes Brasileiras Incluídas**
- **Masculina**: `pt_BR-faber-medium` (voz natural e clara)
- **Feminina**: `pt_BR-lessac-medium` (voz expressiva e calorosa)

*Modelos baixados automaticamente do Hugging Face na primeira execução*

## 🏗️ **Arquitetura do Sistema**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Interface     │───▶│   Node.js API    │───▶│  Python Core    │
│   Web (React)   │    │   (Express.js)   │    │  (Piper TTS)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                               │                         │
                               ▼                         ▼
                       ┌──────────────┐         ┌──────────────┐
                       │   Uploads    │         │   FFmpeg     │
                       │   & Status   │         │ Processador  │
                       └──────────────┘         └──────────────┘
                               │                         │
                               ▼                         ▼
                       ┌─────────────────────────────────────┐
                       │        Volume Persistente           │
                       │  /app/output (podcasts gerados)    │
                       └─────────────────────────────────────┘
```

### **🔧 Componentes Principais**

#### **Backend Python (`src/`)**
- **`core/`**: Lógica central de geração de podcasts
- **`engines/`**: Engines TTS (Piper, fallbacks) 
- **`models/`**: Modelos de dados e parsing

#### **Frontend Node.js**
- **`server.js`**: API REST para upload e processamento
- **`static/`**: Interface web moderna com Bootstrap 5
- **`templates/`**: Templates HTML responsivos

#### **Configuração (`config/`)**
- **`settings.yaml`**: Configuração completa do sistema
- Suporte a múltiplos engines, qualidades e idiomas

#### **Docker & Deploy**
- **`Dockerfile`**: Imagem otimizada Ubuntu 22.04
- **`docker-compose.yml`**: Orquestração completa
- **`.dockerignore`**: Build otimizado

## ⚙️ **Configuração Avançada**

### **Mapeamento de Volumes**
```bash
# Persistir outputs e configurações
docker run -d \
  --name podcast-generator \
  -p 3000:3000 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/scripts:/app/scripts \
  podcast-generator
```

### **Configuração de Performance (`config/settings.yaml`)**
```yaml
# Otimizações para diferentes cenários
performance:
  parallel_synthesis: true     # Síntese paralela
  max_workers: 4              # CPU cores a usar
  cache_enabled: true         # Cache de modelos
  cache_size: 100             # MB de cache

# Qualidade vs Velocidade
engines:
  piper:
    quality: "medium"         # low, medium, high
    speed: 1.0               # 0.5-2.0
    neural: true             # Engine neural
    
audio:
  sample_rate: 22050         # Piper TTS otimizado
  normalize_volume: true     # Normalização automática
  apply_compression: true    # Compressão dinâmica
```

### **Configuração de Recursos**
```yaml
# Limites e validações
limits:
  max_segment_length: 60     # segundos por segmento
  max_total_duration: 900    # 15 minutos máximo
  max_characters: 8          # personagens simultâneos
  max_text_length: 500       # caracteres por fala
```

## 🐳 **Docker em Detalhes**

### **Build Otimizado**
O `Dockerfile` foi otimizado para:
- **Download automático** de modelos Piper TTS
- **Instalação mínima** de dependências do sistema
- **Usuário não-root** para segurança
- **Cache de layers** para builds rápidos
- **Healthcheck** integrado

### **Multi-stage Build**
```dockerfile
# Sistema base otimizado
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Dependências sistema (camada cacheable)
RUN apt-get update && apt-get install -y \
    python3 python3-pip nodejs npm ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Modelos TTS (download automático)
RUN curl -L -o pt_BR-faber-medium.onnx \
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/..."
```

### **Docker Compose para Produção**
```yaml
version: '3.8'
services:
  podcast-generator:
    build: .
    ports:
      - "3000:3000"
    volumes:
      - podcast_output:/app/output
      - ./config:/app/config:ro
    environment:
      - NODE_ENV=production
      - PYTHONUNBUFFERED=1
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

## 💻 **Desenvolvimento Local**

### **Sem Docker (desenvolvimento)**
```bash
# Backend Python
pip install -r requirements.txt
python podcast_generator.py scripts/exemplo.txt

# Frontend Node.js
npm install
npm start
```

### **Com Docker (produção)**
```bash
# Build local
docker build -t podcast-local .

# Desenvolvimento com volume mounting
docker run -it --rm \
  -p 3000:3000 \
  -v $(pwd):/app \
  podcast-local npm run dev
```

## 📊 **Monitoramento e Logs**

### **Logs em Tempo Real**
```bash
# Docker logs
docker logs -f podcast-generator

# Docker Compose logs
docker-compose logs -f podcast-generator
```

### **Health Check**
```bash
# Verificar status
curl http://localhost:3000/health

# Resposta esperada
{"status":"ok","engine":"piper","models":"loaded"}
```

### **Métricas de Performance**
- **Tempo médio**: 30-60 segundos por minuto de áudio
- **Uso de RAM**: 1-2GB durante processamento
- **Uso de CPU**: 50-80% (cores definidos em `max_workers`)
- **Espaço**: ~100MB por podcast de 10 minutos

## 🔧 **Troubleshooting**

### **Problemas Comuns**

#### **Container não inicia**
```bash
# Verificar logs
docker logs podcast-generator

# Problemas de permissão
docker exec -it podcast-generator chown -R podcast:podcast /app
```

#### **Modelos não baixam**
```bash
# Download manual
docker exec -it podcast-generator bash
cd /home/podcast/.local/share/piper-tts
curl -L -o pt_BR-faber-medium.onnx "https://huggingface.co/..."
```

#### **Interface não carrega**
```bash
# Verificar porta
netstat -tlnp | grep 3000

# Verificar firewall
ufw allow 3000
```

#### **Processamento lento**
```yaml
# Otimizar settings.yaml
performance:
  max_workers: 2          # Reduzir para máquinas fracas
  parallel_synthesis: false  # Processar sequencial
```

### **Logs de Debug**
```yaml
# config/settings.yaml
logging:
  level: "DEBUG"
  file: "podcast_generator.log"
```

## 🚀 **Deploy em Produção**

### **Docker Swarm**
```bash
docker stack deploy -c docker-compose.yml podcast-stack
```

### **Kubernetes**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: podcast-generator
spec:
  replicas: 2
  selector:
    matchLabels:
      app: podcast-generator
  template:
    metadata:
      labels:
        app: podcast-generator
    spec:
      containers:
      - name: podcast-generator
        image: podcast-generator:latest
        ports:
        - containerPort: 3000
```

### **Reverse Proxy (Nginx)**
```nginx
server {
    listen 80;
    server_name podcast.exemplo.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 📋 **Requisitos de Sistema**

### **Mínimo**
- **CPU**: 2 cores (x86_64 ou ARM64)
- **RAM**: 2GB disponível
- **Disco**: 3GB livres
- **OS**: Linux, macOS, Windows (com Docker)

### **Recomendado**
- **CPU**: 4+ cores (melhor performance paralela)
- **RAM**: 4GB+ (processamento simultâneo)
- **Disco**: 5GB+ (cache e modelos)
- **SSD**: Preferível para I/O rápido

### **Compatibilidade**
- ✅ **Linux**: Ubuntu 20.04+, Debian 11+, CentOS 8+
- ✅ **macOS**: 10.15+ (Intel e Apple Silicon)
- ✅ **Windows**: 10/11 com WSL2 + Docker Desktop
- ✅ **Cloud**: AWS, GCP, Azure, DigitalOcean

## 🤝 **Contribuição**

### **Como Contribuir**
1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

### **Desenvolvimento**
```bash
# Setup desenvolvimento
git clone <repo>
cd podcast-docker

# Executar testes
python -m pytest tests/

# Linting
flake8 src/
eslint static/app.js
```

### **Roadmap**
- [ ] Suporte a mais idiomas (ES, EN, FR)
- [ ] Interface de configuração web
- [ ] API REST completa
- [ ] Webhooks para integração
- [ ] Música de fundo automática
- [ ] Templates de podcast

## 📄 **Licença**

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🙏 **Agradecimentos**

- **[Piper TTS](https://github.com/rhasspy/piper)** - Engine TTS neural incrível
- **[Hugging Face](https://huggingface.co/)** - Hospedagem dos modelos de voz
- **Comunidade Open Source** - Por tornar projetos como este possíveis

---

**💡 Dica**: Para dúvidas ou suporte, abra uma [issue](issues) ou consulte a [documentação completa](docs/).

---
<div align="center">
<strong>Feito com ❤️ para democratizar a criação de podcasts de qualidade</strong>
</div> 
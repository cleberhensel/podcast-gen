# 🎙️ Podcast Generator TTS - Sistema Avançado de Geração de Podcasts

[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-green?logo=python)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-12+-brightgreen?logo=node.js)](https://nodejs.org)
[![TTS](https://img.shields.io/badge/TTS-Piper-purple)](https://github.com/rhasspy/piper)

Sistema profissional para geração automatizada de podcasts usando **Piper TTS** como engine principal e **macOS TTS** como fallback. Interface web moderna com upload de roteiros e download automático de MP3s.

## ✨ **Características Principais**

### 🎯 **Engines TTS**
- **🥇 Piper TTS** - Engine neural rápido e eficiente (ONNX)
- **🥈 macOS TTS** - Backup nativo confiável

### 🚀 **Recursos Avançados**
- ✅ **Vozes Masculinas e Femininas** diferenciadas
- ✅ **Interface Web Moderna** com drag & drop
- ✅ **Processamento em Background** com status em tempo real
- ✅ **Fallback Automático** entre engines
- ✅ **Configuração Flexível** via YAML
- ✅ **Docker Ready** - Deploy em segundos
- ✅ **Download Automático** de modelos TTS
- ✅ **Suporte Multilingual** (PT-BR, EN, ES, FR, DE)

### 🎵 **Qualidades de Áudio**
- **Sample Rate**: 22kHz (Piper TTS)
- **Formato**: WAV + MP3 (192kbps)
- **Processamento**: FFmpeg para otimização
- **Vozes**: Diferenciação automática por personagem

## 🛠️ **Tecnologias Utilizadas**

### Backend
- **Python 3.10+** - Core engine
- **Piper TTS** - Fast neural synthesis (ONNX)
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
- **2GB+ RAM** (recomendado 4GB)
- **2GB+ espaço livre** para modelos

### 1️⃣ **Clone e Build**
```bash
git clone <repository-url>
cd podcast-docker

# Build da imagem (10-15 min na primeira vez)
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
  default: "piper"        # Engine padrão
  
  piper:
    enabled: true
    quality: "medium"
    speed: 1.0
    
  macos:
    enabled: true
    default_rate: 200
```

## 🎙️ **Engines TTS Detalhadas**

### 🥇 **Piper TTS** *(Recomendado)*
- **Qualidade**: ⭐⭐⭐⭐ Muito Boa  
- **Velocidade**: ⭐⭐⭐⭐⭐ Muito Rápida (~5s/min)
- **Recursos**: Neural ONNX, modelos otimizados
- **Uso**: Produção profissional

**Configurações:**
```yaml
piper:
  enabled: true
  models_path: "~/.local/share/piper-tts"
  quality: "medium"        # low, medium, high
  speed: 1.0              # 0.5-2.0
  neural: true
  fallback_to_macos: true
```

### 🥈 **macOS TTS**
- **Qualidade**: ⭐⭐⭐ Boa
- **Velocidade**: ⭐⭐⭐⭐⭐ Instantânea
- **Recursos**: Nativo, confiável
- **Uso**: Fallback, desenvolvimento

## 🔄 **Sistema de Fallback**

O sistema tenta engines nesta ordem:
1. **Piper TTS** (preferido)
2. **macOS TTS** (fallback)

Se um engine falha, o próximo é usado automaticamente.

## 🐳 **Docker Detalhado**

### **Dockerfile Highlights**
```dockerfile
FROM ubuntu:22.04

# Instalar dependências
RUN apt-get update && apt-get install -y \
    python3 python3-pip nodejs npm ffmpeg \
    espeak espeak-data libespeak-dev

# Instalar Piper TTS
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install piper-tts
```

### **Volumes e Networking**
```bash
# Mapeamento de volumes
podman run -d \
  --name podcast-generator \
  -p 3000:3000 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/scripts:/app/scripts \
  podcast-generator
```

## 🔧 **Desenvolvimento**

### **Setup Local**
```bash
# Instalar dependências Python
pip install -r requirements.txt

# Instalar dependências Node.js  
npm install

# Rodar servidor de desenvolvimento
python podcast_generator.py scripts/exemplo.txt

# Rodar interface web
node server.js
```

### **Estrutura de Código**
- `src/engines/` - Implementações de engines TTS
- `src/core/` - Lógica principal do gerador
- `src/models/` - Modelos de dados
- `config/` - Configurações YAML
- `static/` - Assets web
- `templates/` - Templates HTML

## 🧪 **Testes**

### **Teste Rápido**
```bash
# Gerar podcast de teste
python podcast_generator.py scripts/teste.txt --output-dir output/test

# Verificar engines disponíveis
python -c "from src.engines.engine_factory import tts_factory; print(tts_factory.get_available_engines())"
```

### **Teste de Performance**
```bash
# Benchmark de velocidade
time python podcast_generator.py scripts/benchmark.txt
```

## 🚨 **Troubleshooting**

### **Problemas Comuns**

#### ❌ "Piper TTS não disponível"
```bash
# Instalar Piper TTS
pip install piper-tts

# Verificar instalação
python -c "import piper; print('Piper OK')"
```

#### ❌ "Modelos não encontrados"
```bash
# Criar diretório de modelos
mkdir -p ~/.local/share/piper-tts

# Download manual de modelos
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/lessac/medium/pt_BR-lessac-medium.onnx
```

#### ❌ "FFmpeg não encontrado"
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Container
apt-get update && apt-get install -y ffmpeg
```

#### ❌ "Porta 3000 em uso"
```bash
# Usar porta diferente
podman run -p 8080:3000 podcast-generator

# Ou parar processo usando porta 3000
lsof -ti:3000 | xargs kill -9
```

## 📊 **Performance**

### **Benchmarks Típicos**
- **Piper TTS**: ~5-10s por minuto de áudio
- **macOS TTS**: ~1-2s por minuto de áudio
- **Conversão MP3**: ~2-3s independente do tamanho

### **Requisitos de Sistema**
- **CPU**: 2+ cores (4+ recomendado)
- **RAM**: 2GB+ (4GB recomendado)
- **Disco**: 2GB+ livre para modelos
- **Rede**: Para download inicial de modelos

### **Otimizações**
- Use `quality: "medium"` para melhor balanço velocidade/qualidade
- Síntese paralela habilitada por padrão
- Cache de modelos automático
- Processamento de áudio otimizado com FFmpeg

## 📈 **Roadmap**

### **v2.0** *(Em desenvolvimento)*
- ✅ Migração para Piper TTS como principal
- ✅ Remoção de dependências pesadas (PyTorch)
- ✅ Melhoria de performance
- 🔄 Interface web aprimorada
- 🔄 API REST completa
- 🔄 Suporte a múltiplos idiomas

### **v2.1** *(Planejado)*
- 📋 Processamento em lote
- 📋 Templates de podcast
- 📋 Integração com serviços de hosting
- 📋 Métricas e analytics

## 📜 **Changelog**

### **v1.8.0** *(Atual)*
- ✅ Removido Coqui TTS (dependências pesadas)
- ✅ Piper TTS como engine principal
- ✅ Redução significativa de tamanho da imagem Docker
- ✅ Melhoria de performance geral
- ✅ Interface web otimizada

### **v1.7.0**
- ✅ Interface web com drag & drop
- ✅ Sistema de fallback automático
- ✅ Processamento em background
- ✅ Download automático de modelos

## 🤝 **Contribuindo**

1. Fork o repositório
2. Crie branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 **Licença**

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

## 🙏 **Agradecimentos**

- [Piper TTS](https://github.com/rhasspy/piper) - Engine TTS principal
- [FFmpeg](https://ffmpeg.org/) - Processamento de áudio
- [Docker](https://docker.com/) - Containerization
- [Bootstrap](https://getbootstrap.com/) - UI Framework 
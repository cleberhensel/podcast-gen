# Sistema de Extração de Samples de Áudio

Sistema modular para extrair, processar e otimizar samples de áudio para uso com engines TTS, especialmente otimizado para CoquiTTS.

## 📁 Estrutura

```
src/extractors/
├── __init__.py           # Exportações do módulo
├── base_extractor.py     # Classe base para extractors
├── youtube_extractor.py  # Extrator do YouTube
├── audio_processor.py    # Processador de áudio genérico
├── cli.py               # Interface de linha de comando
└── README.md            # Esta documentação
```

## 🚀 Início Rápido

### Interface CLI

```bash
# Ajuda geral
python -m src.extractors.cli --help

# Extrair sample do YouTube
python -m src.extractors.cli youtube "https://youtu.be/VIDEO_ID" \
    --start 30 --duration 8 --name "speaker_name"

# Listar samples existentes
python -m src.extractors.cli list

# Ver estatísticas
python -m src.extractors.cli stats
```

## 📚 Funcionalidades

### 🎬 YouTube Extractor

Extrai samples de áudio diretamente do YouTube com otimização automática.

**Características:**
- Extração de segments específicos (início + duração)
- Múltiplos segments de uma vez
- Separação de vozes masculinas/femininas
- Otimização automática para CoquiTTS (24kHz, Mono, Float32)
- Validação de formato

**Exemplos:**

```bash
# Sample único
python -m src.extractors.cli youtube "https://youtu.be/ABC123" \
    --start 90 --duration 8 --name "speaker_male"

# Múltiplos segments
python -m src.extractors.cli youtube "https://youtu.be/ABC123" \
    --segments '[
        {"start":30,"duration":8,"name":"male_voice"},
        {"start":120,"duration":10,"name":"female_voice"}
    ]'
```

### 🔧 Audio Processor

Processa e otimiza arquivos de áudio existentes.

**Características:**
- Otimização para CoquiTTS
- Processamento em lote
- Segmentação de arquivos longos
- Conversão de formatos
- Análise de qualidade

**Exemplos:**

```bash
# Otimizar arquivo único
python -m src.extractors.cli process audio.wav --optimize

# Processar diretório inteiro
python -m src.extractors.cli process ./input_dir/ --batch --optimize

# Segmentar arquivo longo
python -m src.extractors.cli process long_audio.wav \
    --segments '[
        {"start":0,"duration":8,"name":"segment1"},
        {"start":30,"duration":10,"name":"segment2"}
    ]'
```

### 📊 Ferramentas de Análise

Analise e gerencie seus samples de áudio.

**Características:**
- Listagem detalhada com informações técnicas
- Estatísticas completas (tamanho, duração, sample rate)
- Validação para CoquiTTS
- Limpeza automática baseada em critérios

**Exemplos:**

```bash
# Listar todos os samples
python -m src.extractors.cli list

# Estatísticas resumidas
python -m src.extractors.cli stats

# Limpar samples inadequados (muito curtos/longos)
python -m src.extractors.cli clean --min-duration 5 --max-duration 30
```

## 🎯 Integração com Sistema de Podcast

### Uso Direto

```bash
# Usar samples extraídos no gerador de podcast
python podcast_generator.py roteiro.txt \
    --engine coqui \
    --male-wav static/speaker_samples/male_voice.wav \
    --female-wav static/speaker_samples/female_voice.wav
```

### Fluxo de Trabalho Recomendado

1. **Extrair sample do YouTube:**
   ```bash
   python -m src.extractors.cli youtube 'URL' \
       --start 30 --duration 8 --name 'speaker1'
   ```

2. **Otimizar se necessário:**
   ```bash
   python -m src.extractors.cli process speaker1.wav --optimize
   ```

3. **Validar qualidade:**
   ```bash
   python -m src.extractors.cli stats
   ```

4. **Usar no podcast:**
   ```bash
   python podcast_generator.py roteiro.txt \
       --engine coqui --male-wav speaker1.wav
   ```

## 🔧 Dependências

### Obrigatórias
- `ffmpeg` - Processamento de áudio
- `ffprobe` - Análise de arquivos

### YouTube Extractor
- `yt-dlp` - Download do YouTube

### Instalação

```bash
# macOS (Homebrew)
brew install ffmpeg yt-dlp

# Ubuntu/Debian
sudo apt install ffmpeg
pip install yt-dlp

# Python packages
pip install yt-dlp
```

## 📋 Formatos Suportados

### Entrada
- Qualquer formato suportado pelo ffmpeg
- YouTube URLs (todos os formatos)
- Arquivos locais: WAV, MP3, M4A, FLAC, etc.

### Saída
- WAV otimizado para CoquiTTS:
  - Sample Rate: 24kHz
  - Canais: Mono
  - Codec: PCM Float32
  - Filtros: High-pass (80Hz) + Low-pass (8kHz)

## 🎨 Uso Programático

### Python API

```python
from src.extractors import YouTubeSampleExtractor, AudioSampleProcessor

# YouTube extractor
extractor = YouTubeSampleExtractor("output/samples")
sample_file = extractor.extract_sample(
    "https://youtu.be/VIDEO_ID", 
    start_time=30, 
    duration=8, 
    output_name="speaker1"
)

# Audio processor
processor = AudioSampleProcessor("output/samples")
optimized_file = processor.optimize_for_coqui(sample_file)

# Análise
stats = processor.analyze_samples()
print(f"Total samples: {stats['count']}")
```

### Múltiplos Segments

```python
# Extrair vários segments
segments = [
    {"start": 30, "duration": 8, "name": "male_voice"},
    {"start": 120, "duration": 10, "name": "female_voice"}
]

results = extractor.extract_multiple_samples(url, segments)
```

## ⚠️ Critérios de Qualidade para CoquiTTS

### Ideais ✅
- **Sample Rate:** 24kHz
- **Canais:** Mono
- **Duração:** 3-60 segundos
- **Qualidade:** Voz clara, sem ruído de fundo
- **Conteúdo:** Fala natural, sem música

### Aceitáveis ⚠️
- **Sample Rate:** 22kHz, 44kHz (será convertido)
- **Canais:** Stereo (será convertido para mono)
- **Duração:** 2-120 segundos

### Problemáticos ❌
- Sample rate muito baixo (<16kHz)
- Muito ruído de fundo
- Música sobreposta
- Voz distorcida
- Duração muito curta (<2s) ou longa (>120s)

## 🐛 Troubleshooting

### Erro: "yt-dlp não encontrado"
```bash
pip install yt-dlp
```

### Erro: "ffmpeg não encontrado"
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### Sample com qualidade ruim
- Use segments mais curtos (5-10 segundos)
- Escolha partes com fala clara
- Evite música de fundo
- Use `--optimize` para aplicar filtros

### YouTube bloqueado
- Tente URLs diferentes
- Use VPN se necessário
- Algumas regiões/vídeos podem estar bloqueados

## 📝 Changelog

### v1.0.0 (Atual)
- ✅ Estrutura modular completa
- ✅ Interface CLI avançada
- ✅ YouTube extractor robusto
- ✅ Processador de áudio genérico
- ✅ Ferramentas de análise
- ✅ Integração com sistema de podcast
- ✅ Validação para CoquiTTS
- ✅ Documentação completa

## 🤝 Contribuição

Para adicionar novos extractors:

1. Herde de `BaseSampleExtractor`
2. Implemente `extract_sample()`
3. Adicione ao `__init__.py`
4. Atualize CLI se necessário

Exemplo:
```python
class NewExtractor(BaseSampleExtractor):
    def extract_sample(self, source: str, **kwargs) -> Path:
        # Sua implementação aqui
        pass
```

## 📄 Licença

Mesmo que o projeto principal. 
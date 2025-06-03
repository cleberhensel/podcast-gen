const express = require('express');
const multer = require('multer');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs-extra');
const path = require('path');
const { spawn } = require('child_process');

const app = express();
const PORT = 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('static'));
app.use('/output', express.static('output'));

// Storage para uploads
const storage = multer.diskStorage({
    destination: 'uploads/',
    filename: (req, file, cb) => {
        const jobId = uuidv4();
        req.jobId = jobId;
        cb(null, `${jobId}.txt`);
    }
});

const upload = multer({
    storage,
    fileFilter: (req, file, cb) => {
        if (file.mimetype === 'text/plain' || file.originalname.endsWith('.txt')) {
            cb(null, true);
        } else {
            cb(new Error('Apenas arquivos .txt são permitidos'));
        }
    }
});

// Armazenar status dos jobs
const jobs = new Map();

// Página principal
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'templates', 'index.html'));
});

// Upload e processamento
app.post('/upload', upload.single('roteiro'), async (req, res) => {
    try {
        const jobId = req.jobId || uuidv4();
        const filePath = req.file.path;

        jobs.set(jobId, {
            status: 'processing',
            progress: 0,
            message: 'Iniciando processamento...',
            created: new Date()
        });

        // Responder imediatamente com job ID
        res.json({ jobId, status: 'started' });

        // Processar em background
        processScript(jobId, filePath);

    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Status do job
app.get('/status/:jobId', (req, res) => {
    const job = jobs.get(req.params.jobId);
    if (!job) {
        return res.status(404).json({ error: 'Job não encontrado' });
    }
    res.json(job);
});

// Download do arquivo
app.get('/download/:jobId', (req, res) => {
    const jobId = req.params.jobId;
    const filePath = path.join(__dirname, 'output', 'final', `${jobId}_podcast.mp3`);

    if (fs.existsSync(filePath)) {
        res.download(filePath, `podcast_${jobId}.mp3`);
    } else {
        res.status(404).json({ error: 'Arquivo não encontrado' });
    }
});

// Função para processar script
async function processScript(jobId, filePath) {
    try {
        updateJob(jobId, 'processing', 10, 'Analisando roteiro...');

        // Executar Python script
        const python = spawn('python3', [
            'podcast_generator.py',
            filePath,
            '--output-dir', 'output/final',
            '--job-id', jobId
        ]);

        let output = '';
        let error = '';

        python.stdout.on('data', (data) => {
            output += data.toString();
            console.log(`Python stdout: ${data.toString()}`);
            // Parse do progresso se necessário
            updateJobProgress(jobId, data.toString());
        });

        python.stderr.on('data', (data) => {
            error += data.toString();
            console.error(`Python stderr: ${data.toString()}`);
        });

        python.on('close', (code) => {
            if (code === 0) {
                updateJob(jobId, 'completed', 100, 'Podcast gerado com sucesso!');
            } else {
                // Melhor tratamento de erro para garantir mensagem clara
                let errorMessage = 'Erro no processamento';

                if (error && error.trim()) {
                    errorMessage = `Erro no processamento: ${error.trim()}`;
                } else if (output && output.includes('Error')) {
                    errorMessage = `Erro no processamento: ${output}`;
                } else {
                    errorMessage = `Erro no processamento: Falha na geração do podcast (código: ${code})`;
                }

                console.error(`Job ${jobId} falhou com código ${code}`);
                console.error(`Output: ${output}`);
                console.error(`Error: ${error}`);

                updateJob(jobId, 'error', 0, errorMessage);
            }

            // Limpar arquivo de upload
            fs.unlink(filePath).catch(console.error);
        });

    } catch (error) {
        updateJob(jobId, 'error', 0, `Erro: ${error.message}`);
    }
}

// Atualizar status do job
function updateJob(jobId, status, progress, message) {
    const job = jobs.get(jobId);
    if (job) {
        jobs.set(jobId, { ...job, status, progress, message, updated: new Date() });
    }
}

// Parse do progresso do Python
function updateJobProgress(jobId, output) {
    if (output.includes('Gerando voz masculina')) {
        updateJob(jobId, 'processing', 30, 'Gerando voz masculina...');
    } else if (output.includes('Gerando voz feminina')) {
        updateJob(jobId, 'processing', 50, 'Gerando voz feminina...');
    } else if (output.includes('Combinando segmentos')) {
        updateJob(jobId, 'processing', 80, 'Combinando segmentos...');
    } else if (output.includes('MP3 gerado')) {
        updateJob(jobId, 'processing', 95, 'Finalizando...');
    }
}

// Limpeza automática de jobs antigos
setInterval(() => {
    const now = new Date();
    for (const [jobId, job] of jobs.entries()) {
        const age = now - job.created;
        if (age > 24 * 60 * 60 * 1000) { // 24 horas
            jobs.delete(jobId);
            // Limpar arquivos associados
            const outputFile = path.join(__dirname, 'output', 'final', `${jobId}_podcast.mp3`);
            fs.unlink(outputFile).catch(() => { });
        }
    }
}, 60 * 60 * 1000); // A cada hora

app.listen(PORT, '0.0.0.0', () => {
    console.log(`🎙️ Podcast Generator rodando em http://localhost:${PORT}`);
}); 
let currentJobId = null;
let statusInterval = null;

// Elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const progressSection = document.getElementById('progress-section');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');
const progressPercent = document.getElementById('progress-percent');
const downloadSection = document.getElementById('download-section');
const downloadBtn = document.getElementById('download-btn');
const errorSection = document.getElementById('error-section');
const errorMessage = document.getElementById('error-message');

// Upload zone click
uploadZone.addEventListener('click', () => {
    fileInput.click();
});

// File input change
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        uploadFile(e.target.files[0]);
    }
});

// Drag and drop
uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        uploadFile(files[0]);
    }
});

// Upload file
async function uploadFile(file) {
    if (!file.name.endsWith('.txt')) {
        showError('Apenas arquivos .txt são permitidos');
        return;
    }

    hideAllSections();
    showProgress();

    const formData = new FormData();
    formData.append('roteiro', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            currentJobId = result.jobId;
            monitorProgress();
        } else {
            showError(result.error || 'Erro no upload');
        }
    } catch (error) {
        showError('Erro de conexão: ' + error.message);
    }
}

// Monitor progress
function monitorProgress() {
    statusInterval = setInterval(async () => {
        try {
            const response = await fetch(`/status/${currentJobId}`);
            const status = await response.json();

            updateProgress(status.progress, status.message);

            if (status.status === 'completed') {
                clearInterval(statusInterval);
                showDownload();
            } else if (status.status === 'error') {
                clearInterval(statusInterval);
                showError(status.message);
            }
        } catch (error) {
            console.error('Erro ao verificar status:', error);
        }
    }, 1000);
}

// Update progress
function updateProgress(progress, message) {
    progressBar.style.width = progress + '%';
    progressPercent.textContent = progress + '%';
    progressText.textContent = message;
}

// Show sections
function hideAllSections() {
    uploadZone.style.display = 'none';
    progressSection.classList.add('d-none');
    downloadSection.classList.add('d-none');
    errorSection.classList.add('d-none');
}

function showProgress() {
    progressSection.classList.remove('d-none');
    updateProgress(0, 'Iniciando...');
}

function showDownload() {
    progressSection.classList.add('d-none');
    downloadSection.classList.remove('d-none');

    downloadBtn.onclick = () => {
        window.location.href = `/download/${currentJobId}`;
    };
}

function showError(message) {
    progressSection.classList.add('d-none');
    errorSection.classList.remove('d-none');
    errorMessage.textContent = message;

    // Reset after 5 seconds
    setTimeout(resetInterface, 5000);
}

function resetInterface() {
    hideAllSections();
    uploadZone.style.display = 'block';
    fileInput.value = '';
    currentJobId = null;
    if (statusInterval) {
        clearInterval(statusInterval);
    }
} 
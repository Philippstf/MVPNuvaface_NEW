# NuvaFace Windows Installation Script (PowerShell)
# Alternative to conda using Python venv

Write-Host "=== NuvaFace Windows Installation ===" -ForegroundColor Green

# Check Python version
$pythonVersion = python --version 2>&1
Write-Host "Found Python: $pythonVersion" -ForegroundColor Blue

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv nuvaface_env

# Activate virtual environment
Write-Host "Activating environment..." -ForegroundColor Yellow
& ".\nuvaface_env\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install PyTorch with CUDA 12.1 support
Write-Host "Installing PyTorch with CUDA support..." -ForegroundColor Yellow
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install core ML libraries
Write-Host "Installing diffusion and ML libraries..." -ForegroundColor Yellow
pip install diffusers transformers accelerate

# Try to install xformers (may fail on some systems)
Write-Host "Installing xformers (optional)..." -ForegroundColor Yellow
try {
    pip install xformers
} catch {
    Write-Host "Warning: xformers installation failed - continuing without it" -ForegroundColor Red
}

# Install computer vision and control libraries
Write-Host "Installing CV and control libraries..." -ForegroundColor Yellow
pip install controlnet-aux opencv-python mediapipe

# Install face recognition
Write-Host "Installing face recognition libraries..." -ForegroundColor Yellow
pip install insightface onnxruntime-gpu

# Install web framework and utilities
Write-Host "Installing FastAPI and utilities..." -ForegroundColor Yellow
pip install fastapi uvicorn[standard] pillow einops

# Install additional dependencies
Write-Host "Installing geometry processing libraries..." -ForegroundColor Yellow
pip install shapely scikit-image scipy

# Install quality assessment
Write-Host "Installing image quality assessment..." -ForegroundColor Yellow
pip install lpips scikit-image

Write-Host "=== Installation complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the environment in the future, run:" -ForegroundColor Cyan
Write-Host ".\nuvaface_env\Scripts\Activate.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To start the development server, run:" -ForegroundColor Cyan
Write-Host "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor White
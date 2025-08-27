# CPU-Only Installation (if no CUDA GPU available)
Write-Host "=== Installing CPU-Only Version ===" -ForegroundColor Green

# Activate environment
& ".\nuvaface_env\Scripts\Activate.ps1"

# Remove all GPU packages
pip uninstall xformers torch torchvision onnxruntime-gpu -y

# Install CPU-only versions
Write-Host "Installing CPU-only PyTorch..." -ForegroundColor Yellow
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install CPU-only onnxruntime
pip install onnxruntime

# Reinstall diffusers
pip install --upgrade diffusers

Write-Host "=== CPU-Only Installation Complete ===" -ForegroundColor Green
Write-Host "Note: Performance will be slower without GPU" -ForegroundColor Yellow
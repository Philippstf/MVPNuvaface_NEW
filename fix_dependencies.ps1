# Fix Dependencies - Remove problematic packages and reinstall
Write-Host "=== Fixing Dependencies ===" -ForegroundColor Green

# Activate environment
& ".\nuvaface_env\Scripts\Activate.ps1"

# Remove problematic packages
Write-Host "Removing xformers..." -ForegroundColor Yellow
pip uninstall xformers -y

# Reinstall PyTorch with proper CUDA support
Write-Host "Reinstalling PyTorch..." -ForegroundColor Yellow
pip uninstall torch torchvision -y
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install diffusers without xformers dependency
Write-Host "Reinstalling diffusers..." -ForegroundColor Yellow
pip install --upgrade diffusers

# Test imports
Write-Host "Testing imports..." -ForegroundColor Yellow
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import diffusers; print(f'Diffusers: {diffusers.__version__}')"

Write-Host "=== Fix Complete ===" -ForegroundColor Green
Write-Host "You can now start the server with:" -ForegroundColor Cyan
Write-Host "python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor White
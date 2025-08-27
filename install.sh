#!/bin/bash
set -e

echo "=== NuvaFace PoC Installation ==="

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "Error: conda not found. Please install Anaconda/Miniconda first."
    exit 1
fi

# Create conda environment
echo "Creating conda environment 'nuvaface'..."
conda create -n nuvaface python=3.10 -y

# Activate environment
echo "Activating environment..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate nuvaface

# Install PyTorch with CUDA 12.1 support
echo "Installing PyTorch with CUDA support..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install core ML libraries
echo "Installing diffusion and ML libraries..."
pip install diffusers transformers accelerate xformers

# Install computer vision and control libraries
echo "Installing CV and control libraries..."
pip install controlnet-aux opencv-python mediapipe

# Install face recognition
echo "Installing face recognition libraries..."
pip install insightface onnxruntime-gpu

# Install web framework and utilities
echo "Installing FastAPI and utilities..."
pip install fastapi uvicorn[standard] pillow einops

# Install additional dependencies for Weg B (geometry warping)
echo "Installing geometry processing libraries..."
pip install shapely scikit-image scipy

# Install quality assessment
echo "Installing image quality assessment..."
pip install lpips scikit-image

echo "=== Installation complete! ==="
echo "To activate the environment, run:"
echo "conda activate nuvaface"
echo ""
echo "To start the development server, run:"
echo "uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload"
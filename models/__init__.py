"""
Model loading and caching for NuvaFace pipelines.
This has been simplified for the Gemini-based architecture.
"""
import torch
from typing import Dict, Any

# Global cache for any potential future local models
_model_cache: Dict[str, Any] = {}

def get_device() -> torch.device:
    """Get the best available device (primarily for mediapipe segmentation)."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    # MPS backend can be problematic, prefer CPU
    # elif torch.backends.mps.is_available():
    #     return torch.device("mps")
    else:
        return torch.device("cpu")

def clear_cache():
    """Clear all cached models to free memory."""
    global _model_cache
    _model_cache.clear()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def get_cache_info() -> Dict[str, str]:
    """Get information about currently cached models."""
    # Returns an empty dict as no models are cached in this version
    return {model: type(obj).__name__ for model, obj in _model_cache.items()}

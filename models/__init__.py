"""
Model loading and caching for NuvaFace pipelines.
This has been simplified for the Gemini-based architecture.
"""
from typing import Dict, Any

# Global cache for any potential future local models
_model_cache: Dict[str, Any] = {}

def get_device() -> str:
    """Get the best available device (CPU for Cloud Run)."""
    # For Cloud Run, we just return CPU since we're not using torch/GPU
    return "cpu"

def clear_cache():
    """Clear all cached models to free memory."""
    global _model_cache
    _model_cache.clear()

def get_cache_info() -> Dict[str, str]:
    """Get information about currently cached models."""
    # Returns an empty dict as no models are cached in this version
    return {model: type(obj).__name__ for model, obj in _model_cache.items()}

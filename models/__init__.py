"""
Model loading and caching for NuvaFace pipelines.
Lazy loading to optimize startup time and memory usage.
"""

import os
import torch
from typing import Optional, Dict, Any
from diffusers import StableDiffusionInpaintPipeline, StableDiffusionInstructPix2PixPipeline
from controlnet_aux import CannyDetector, PidiNetDetector, MidasDetector

# Optional import for insightface (identity checking)
try:
    import insightface
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    print("Warning: insightface not available - identity checking will be disabled")
    insightface = None
    INSIGHTFACE_AVAILABLE = False

# Global cache for loaded models
_model_cache: Dict[str, Any] = {}

def get_device() -> torch.device:
    """Get the best available device."""
    if torch.cuda.is_available():
        return torch.device("cuda")
    elif torch.backends.mps.is_available():
        return torch.device("mps")
    else:
        return torch.device("cpu")

def get_sd_inpaint_pipeline(use_xformers: bool = True) -> StableDiffusionInpaintPipeline:
    """Load and cache Stable Diffusion Inpainting pipeline."""
    cache_key = "sd_inpaint"
    
    if cache_key not in _model_cache:
        device = get_device()
        
        # Use local model path
        model_path = os.path.join(os.path.dirname(__file__), "stable-diffusion-inpainting")
        
        pipeline = StableDiffusionInpaintPipeline.from_pretrained(
            model_path,
            torch_dtype=torch.float16 if device.type == "cuda" else torch.float32,
            safety_checker=None,  # Disable for medical/aesthetic use case
            requires_safety_checker=False,
            local_files_only=True
        )
        
        pipeline = pipeline.to(device)
        
        if use_xformers and device.type == "cuda":
            try:
                pipeline.enable_xformers_memory_efficient_attention()
            except ImportError:
                print("Warning: xformers not available, using default attention")
        
        # Enable memory efficient attention for better performance
        if hasattr(pipeline, "enable_model_cpu_offload"):
            pipeline.enable_model_cpu_offload()
        
        _model_cache[cache_key] = pipeline
    
    return _model_cache[cache_key]

def get_ip2p_pipeline(use_xformers: bool = True) -> StableDiffusionInstructPix2PixPipeline:
    """Load and cache InstructPix2Pix pipeline."""
    cache_key = "ip2p"
    
    if cache_key not in _model_cache:
        device = get_device()
        
        pipeline = StableDiffusionInstructPix2PixPipeline.from_pretrained(
            "timbrooks/instruct-pix2pix",
            torch_dtype=torch.float16 if device.type == "cuda" else torch.float32,
            safety_checker=None,
            requires_safety_checker=False
        )
        
        pipeline = pipeline.to(device)
        
        if use_xformers and device.type == "cuda":
            try:
                pipeline.enable_xformers_memory_efficient_attention()
            except ImportError:
                print("Warning: xformers not available, using default attention")
        
        if hasattr(pipeline, "enable_model_cpu_offload"):
            pipeline.enable_model_cpu_offload()
        
        _model_cache[cache_key] = pipeline
    
    return _model_cache[cache_key]

def get_canny_detector() -> CannyDetector:
    """Load and cache Canny edge detector."""
    cache_key = "canny"
    
    if cache_key not in _model_cache:
        _model_cache[cache_key] = CannyDetector()
    
    return _model_cache[cache_key]

def get_pidinet_detector() -> PidiNetDetector:
    """Load and cache PiDiNet soft edge detector."""
    cache_key = "pidinet"
    
    if cache_key not in _model_cache:
        # Use simple Canny detector as alternative to avoid downloads
        _model_cache[cache_key] = CannyDetector()
    
    return _model_cache[cache_key]

def get_midas_detector() -> MidasDetector:
    """Load and cache MiDaS depth detector.""" 
    cache_key = "midas"
    
    if cache_key not in _model_cache:
        # Use simple approach or disable for now to avoid downloads
        # We can implement basic depth estimation later
        _model_cache[cache_key] = None  # Placeholder
    
    return _model_cache[cache_key]

def get_arcface_model():
    """Load and cache ArcFace model for identity preservation."""
    cache_key = "arcface"
    
    if not INSIGHTFACE_AVAILABLE:
        raise ImportError("insightface not available - please install it for identity checking")
    
    if cache_key not in _model_cache:
        app = insightface.app.FaceAnalysis(providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        app.prepare(ctx_id=0, det_size=(640, 640))
        _model_cache[cache_key] = app
    
    return _model_cache[cache_key]

def clear_cache():
    """Clear all cached models to free memory."""
    global _model_cache
    _model_cache.clear()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

def get_cache_info() -> Dict[str, str]:
    """Get information about currently cached models."""
    return {model: type(obj).__name__ for model, obj in _model_cache.items()}
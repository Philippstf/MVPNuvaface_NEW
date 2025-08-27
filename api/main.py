"""
FastAPI main application for NuvaFace aesthetic simulation API.
Implements endpoints for face segmentation and aesthetic procedure simulation.
"""

import time
import random
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import schemas
from .schemas import (
    SegmentRequest, SegmentResponse, BoundingBox,
    FillerSimulationRequest, BotoxSimulationRequest, SimulationResponse,
    ProcessingParameters, QualityMetrics,
    HealthResponse, ErrorResponse,
    AreaType, PipelineType, get_prompt_for_area, get_adaptive_prompt_for_area
)

# Import engine modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.utils import load_image, image_to_base64, preprocess_image, set_seed
from engine.parsing import segment_area, validate_area
from engine.controls import preprocess_for_inpainting, preprocess_for_ip2p
from engine.edit_sd import simulate_sd_inpaint
from engine.edit_ip2p import simulate_ip2p
from engine.qc import qc, comprehensive_assessment
from engine.qc import get_quality_controller
from models import get_device, get_cache_info

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NuvaFace API",
    description="Aesthetic procedure simulation API with AI-powered facial editing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for UI
import os
ui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")
if os.path.exists(ui_path):
    app.mount("/ui", StaticFiles(directory=ui_path, html=True), name="ui")

# Global variables for caching
_startup_complete = False


@app.on_event("startup")
async def startup_event():
    """Initialize models and warm up the system."""
    global _startup_complete
    
    logger.info("Starting NuvaFace API...")
    
    # Initialize device info
    device = get_device()
    logger.info(f"Using device: {device}")
    
    # Warm up models (optional - models are lazy loaded)
    try:
        logger.info("API startup complete - models will be loaded on demand")
        _startup_complete = True
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down NuvaFace API...")
    from models import clear_cache
    clear_cache()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="internal_server_error",
            message="An internal server error occurred",
            details={"type": type(exc).__name__}
        ).dict()
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    device = get_device()
    cache_info = get_cache_info()
    
    import torch
    memory_usage = {}
    if torch.cuda.is_available():
        memory_usage = {
            "allocated_mb": torch.cuda.memory_allocated() / 1024 / 1024,
            "reserved_mb": torch.cuda.memory_reserved() / 1024 / 1024
        }
    
    return HealthResponse(
        status="healthy" if _startup_complete else "starting",
        version="1.0.0",
        models_loaded={model: True for model in cache_info.keys()},
        gpu_available=device.type == "cuda",
        memory_usage=memory_usage
    )


@app.post("/segment", response_model=SegmentResponse)
async def segment_face(request: SegmentRequest):
    """
    Segment facial area to generate mask for aesthetic editing.
    
    Args:
        request: Segmentation request with image and area
        
    Returns:
        Segmentation response with mask and metadata
    """
    try:
        # Load and preprocess image
        image = load_image(request.image)
        processed_image, preprocess_meta = preprocess_image(image, target_size=768, align_face=False)
        
        # Validate area
        if not validate_area(request.area):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported area: {request.area}"
            )
        
        # Segment area
        mask_image, segment_metadata = segment_area(
            processed_image, 
            request.area, 
            feather_px=request.feather_px
        )
        
        # Convert mask to base64
        mask_base64 = image_to_base64(mask_image, format='PNG')
        
        # Create bounding box
        bbox = BoundingBox(**segment_metadata['bbox'])
        
        # Combine metadata
        combined_metadata = {
            **segment_metadata,
            **preprocess_meta,
            'feather_px': request.feather_px
        }
        
        return SegmentResponse(
            mask_png=mask_base64,
            bbox=bbox,
            metadata=combined_metadata,
            landmarks_count=segment_metadata.get('landmarks_count'),
            confidence=segment_metadata.get('confidence', 1.0)
        )
        
    except Exception as e:
        logger.error(f"Segmentation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Segmentation failed: {str(e)}"
        )


@app.post("/simulate/filler", response_model=SimulationResponse)
async def simulate_filler(request: FillerSimulationRequest):
    """
    Simulate filler aesthetic procedure on lips, chin, or cheeks.
    
    Args:
        request: Filler simulation request
        
    Returns:
        Simulation response with result and quality metrics
    """
    return await _simulate_procedure(request, "filler")


@app.post("/simulate/botox", response_model=SimulationResponse)
async def simulate_botox(request: BotoxSimulationRequest):
    """
    Simulate Botox procedure on forehead area.
    
    Args:
        request: Botox simulation request
        
    Returns:
        Simulation response with result and quality metrics
    """
    return await _simulate_procedure(request, "botox")


async def _simulate_procedure(request, procedure_type: str):
    """
    Internal function to handle both filler and botox simulation.
    
    Args:
        request: Simulation request
        procedure_type: Type of procedure ("filler" or "botox")
        
    Returns:
        Simulation response
    """
    try:
        start_time = time.time()
        
        # Generate seed if not provided
        if request.seed is None:
            request.seed = random.randint(0, 2**32 - 1)
        
        # Load and preprocess image
        image = load_image(request.image)
        
        # ALWAYS use real photo optimization (user confirmed they only use real photos)
        from engine.real_photo_optimizer import get_real_photo_processor
        photo_processor = get_real_photo_processor()
        photo_type = 'real'  # Force real photo processing
        logger.info(f"Forcing real photo processing for all images")
        
        # Apply real photo preprocessing
        optimized_image = photo_processor.preprocess_real_photo(image)
        processed_image, preprocess_meta = preprocess_image(optimized_image, target_size=768, align_face=True)
        
        # Get or generate mask
        if request.mask:
            mask_image = load_image(request.mask).convert('L')
        else:
            mask_image, _ = segment_area(processed_image, request.area)
        
        # Get adaptive prompt for area based on strength
        prompt = get_adaptive_prompt_for_area(request.area, request.strength)
        
        # Generate control maps based on pipeline
        if request.pipeline == PipelineType.INSTRUCT_PIX2PIX:
            control_maps = preprocess_for_ip2p(processed_image)
        else:
            control_maps = preprocess_for_inpainting(processed_image)
        
        # Run simulation based on pipeline with photo-type optimization
        if request.pipeline == PipelineType.INSTRUCT_PIX2PIX:
            # Use optimized IP2P for real photos
            if photo_type == 'real':
                from engine.edit_ip2p import get_ip2p_editor
                editor = get_ip2p_editor()
                # Override parameters for real photos
                optimal_params = photo_processor.get_real_photo_ip2p_params(request.strength)
                # Custom simulate call with optimized parameters
                result_image, params = editor.simulate_ip2p_with_params(
                    processed_image, mask_image, control_maps,
                    request.strength, request.seed, prompt, request.area, optimal_params
                )
            else:
                result_image, params = simulate_ip2p(
                    processed_image, mask_image, control_maps,
                    request.strength, request.seed, prompt, request.area
                )
        else:
            # ALWAYS use optimized SD-Inpainting with real photo parameters
            from engine.edit_sd import get_sd_editor
            editor = get_sd_editor()
            optimal_params = photo_processor.get_real_photo_sd_params(request.strength)
            logger.info(f"Using real photo optimization with params: {optimal_params}")
            # Custom simulate call with optimized parameters
            result_image, params = editor.simulate_inpaint_with_params(
                processed_image, mask_image, control_maps,
                request.strength, request.seed, prompt, optimal_params
            )
        
        # Quality control assessment
        id_similarity, ssim_off_mask = qc(processed_image, result_image, mask_image)
        
        # Comprehensive QC (optional)
        qc_results = comprehensive_assessment(processed_image, result_image, mask_image)
        qc_controller = get_quality_controller()
        should_retry_flag, retry_reason = qc_controller.should_retry(qc_results) if 'quality_passed' in qc_results else (False, None)
        
        # Create quality metrics
        quality_metrics = QualityMetrics(
            id_similarity=id_similarity,
            ssim_off_mask=ssim_off_mask,
            id_warning=qc_results.get('id_warning'),
            ssim_warning=qc_results.get('ssim_warning'),
            quality_passed=qc_results.get('quality_passed')
        )
        
        # Generate warnings
        warnings = []
        if quality_metrics.id_warning:
            warnings.append("Identity similarity below threshold - consider lower strength")
        if quality_metrics.ssim_warning:
            warnings.append("Off-target changes detected - mask may need refinement")
        
        # Convert images to base64
        result_base64 = image_to_base64(result_image)
        original_base64 = image_to_base64(processed_image)
        mask_base64 = image_to_base64(mask_image)
        
        # Create processing parameters
        processing_params = ProcessingParameters(**params)
        
        end_time = time.time()
        total_time = int((end_time - start_time) * 1000)
        
        return SimulationResponse(
            result_png=result_base64,
            original_png=original_base64,
            mask_png=mask_base64,
            params=processing_params,
            qc=quality_metrics,
            warnings=warnings,
            should_retry=should_retry_flag,
            retry_reason=retry_reason
        )
        
    except Exception as e:
        logger.error(f"Simulation error for {procedure_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}"
        )


@app.get("/areas")
async def get_supported_areas():
    """Get list of supported facial areas."""
    return {
        "filler_areas": [AreaType.LIPS, AreaType.CHIN, AreaType.CHEEKS],
        "botox_areas": [AreaType.FOREHEAD],
        "all_areas": [area.value for area in AreaType]
    }


@app.get("/pipelines")
async def get_supported_pipelines():
    """Get list of supported processing pipelines."""
    return {
        "pipelines": [pipeline.value for pipeline in PipelineType],
        "default": PipelineType.SD_INPAINT.value,
        "recommended": {
            "filler": PipelineType.SD_INPAINT.value,
            "botox": PipelineType.SD_INPAINT.value
        }
    }


@app.get("/prompts/{area}")
async def get_area_prompts(area: AreaType, language: str = "en", strength: int = 50):
    """Get adaptive prompts for specific area, language, and strength."""
    try:
        # Get both static and adaptive prompts
        static_prompt = get_prompt_for_area(area, language)
        adaptive_prompt = get_adaptive_prompt_for_area(area, strength, language)
        
        return {
            "area": area,
            "language": language,
            "strength": strength,
            "static_prompt": static_prompt,
            "adaptive_prompt": adaptive_prompt,
            "prompt": adaptive_prompt  # Default to adaptive
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameters: {str(e)}"
        )


@app.get("/models/status")
async def get_model_status():
    """Get current model loading status and cache information."""
    cache_info = get_cache_info()
    device = get_device()
    
    import torch
    gpu_info = {}
    if torch.cuda.is_available():
        gpu_info = {
            "device_name": torch.cuda.get_device_name(0),
            "memory_allocated": torch.cuda.memory_allocated(),
            "memory_reserved": torch.cuda.memory_reserved(),
            "memory_total": torch.cuda.get_device_properties(0).total_memory
        }
    
    return {
        "device": str(device),
        "loaded_models": cache_info,
        "gpu_info": gpu_info
    }


# Development endpoints (can be removed in production)

@app.post("/debug/clear_cache")
async def clear_model_cache():
    """Clear model cache (development only)."""
    from models import clear_cache
    clear_cache()
    return {"status": "cache_cleared"}



@app.post("/debug/test_parameters")
async def test_parameters_systematically(request: dict):
    """Test different parameter combinations systematically."""
    try:
        # Load test image
        image = load_image(request['image'])
        
        # Force real photo processing
        from engine.real_photo_optimizer import get_real_photo_processor
        photo_processor = get_real_photo_processor()
        optimized_image = photo_processor.preprocess_real_photo(image)
        processed_image, _ = preprocess_image(optimized_image, target_size=768, align_face=True)
        
        # Generate mask
        mask_image, _ = segment_area(processed_image, request['area'])
        
        # Test different parameter combinations
        test_results = []
        
        # Parameter test matrix
        test_params = [
            # Conservative tests
            {'denoising_strength': 0.15, 'guidance_scale': 4.0, 'controlnet_scale': 0.80, 'name': 'very_conservative'},
            {'denoising_strength': 0.20, 'guidance_scale': 4.5, 'controlnet_scale': 0.75, 'name': 'conservative'},
            {'denoising_strength': 0.25, 'guidance_scale': 5.0, 'controlnet_scale': 0.70, 'name': 'moderate'},
            {'denoising_strength': 0.30, 'guidance_scale': 5.5, 'controlnet_scale': 0.65, 'name': 'moderate_strong'},
            {'denoising_strength': 0.35, 'guidance_scale': 6.0, 'controlnet_scale': 0.60, 'name': 'strong'},
        ]
        
        from engine.edit_sd import get_sd_editor
        from engine.controls import preprocess_for_inpainting
        
        editor = get_sd_editor()
        control_maps = preprocess_for_inpainting(processed_image)
        prompt = "enhanced natural lips, smooth texture, healthy volume, natural beauty"
        
        for params in test_params:
            try:
                # Test with fixed seed for reproducibility
                test_seed = 12345
                
                # Override parameters
                custom_params = {
                    'denoising_strength': params['denoising_strength'],
                    'guidance_scale': params['guidance_scale'],
                    'controlnet_scale': params['controlnet_scale'],
                    'mask_feather': 8,
                    'num_inference_steps': 25
                }
                
                # Run test
                result_image, result_params = editor.simulate_inpaint_with_params(
                    processed_image, mask_image, control_maps,
                    50, test_seed, prompt, custom_params
                )
                
                # Quality assessment
                id_similarity, ssim_off_mask = qc(processed_image, result_image, mask_image)
                
                # Convert result to base64 for inspection
                result_base64 = image_to_base64(result_image)
                
                test_results.append({
                    'name': params['name'],
                    'parameters': custom_params,
                    'quality': {
                        'id_similarity': float(id_similarity),
                        'ssim_off_mask': float(ssim_off_mask)
                    },
                    'result_image': result_base64
                })
                
                logger.info(f"Test {params['name']}: ID={id_similarity:.3f}, SSIM={ssim_off_mask:.3f}")
                
            except Exception as e:
                test_results.append({
                    'name': params['name'],
                    'parameters': params,
                    'error': str(e)
                })
                logger.error(f"Test {params['name']} failed: {e}")
        
        return {
            'test_results': test_results,
            'original_image': image_to_base64(processed_image),
            'mask_image': image_to_base64(mask_image)
        }
        
    except Exception as e:
        logger.error(f"Parameter testing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Parameter testing failed: {str(e)}"
        )


@app.post("/debug/test_quality/{area}")
async def test_quality_metrics(area: AreaType, test_image: str):
    """Test quality metrics on an image (development only)."""
    try:
        image = load_image(test_image)
        processed_image, _ = preprocess_image(image)
        mask_image, _ = segment_area(processed_image, area)
        
        # Test with original image (should have perfect metrics)
        qc_results = comprehensive_assessment(processed_image, processed_image, mask_image)
        
        return {
            "area": area,
            "qc_results": qc_results,
            "expected": "Perfect scores for identical images"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
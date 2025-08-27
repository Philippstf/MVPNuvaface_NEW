"""
Pydantic models for API request/response schemas.
Defines data structures for NuvaFace API endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union
from enum import Enum


class AreaType(str, Enum):
    """Supported facial areas for aesthetic procedures."""
    LIPS = "lips"
    CHIN = "chin" 
    CHEEKS = "cheeks"
    FOREHEAD = "forehead"


class PipelineType(str, Enum):
    """Available processing pipelines."""
    SD_INPAINT = "sd_inpaint"
    INSTRUCT_PIX2PIX = "ip2p"
    HYBRID_B = "B"  # Future: Geometry warping + inpainting


# Request Models

class SegmentRequest(BaseModel):
    """Request model for face segmentation endpoint."""
    image: str = Field(..., description="Base64 encoded image or image URL")
    area: AreaType = Field(..., description="Facial area to segment")
    feather_px: Optional[int] = Field(default=3, ge=0, le=10, description="Mask feathering in pixels")
    
    @validator('image')
    def validate_image(cls, v):
        if not v:
            raise ValueError("Image is required")
        # Basic validation - could be enhanced with format checking
        return v


class SimulationRequest(BaseModel):
    """Base request model for aesthetic simulation."""
    image: str = Field(..., description="Base64 encoded image or image URL")
    area: AreaType = Field(..., description="Facial area to modify")
    strength: int = Field(..., ge=0, le=100, description="Effect strength (0-100)")
    pipeline: PipelineType = Field(default=PipelineType.SD_INPAINT, description="Processing pipeline")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")
    mask: Optional[str] = Field(default=None, description="Optional custom mask (base64)")
    
    @validator('strength')
    def validate_strength(cls, v):
        return max(0, min(100, v))
    
    @validator('seed')
    def validate_seed(cls, v):
        if v is not None:
            return max(0, min(2**32 - 1, v))
        return v


class FillerSimulationRequest(SimulationRequest):
    """Request model for filler simulation (lips, chin, cheeks)."""
    area: AreaType = Field(..., description="Filler area: lips, chin, or cheeks")
    
    @validator('area')
    def validate_filler_area(cls, v):
        if v not in [AreaType.LIPS, AreaType.CHIN, AreaType.CHEEKS]:
            raise ValueError("Filler area must be lips, chin, or cheeks")
        return v


class BotoxSimulationRequest(SimulationRequest):
    """Request model for Botox simulation (forehead)."""
    area: AreaType = Field(default=AreaType.FOREHEAD, description="Botox area: forehead")
    
    @validator('area')
    def validate_botox_area(cls, v):
        if v != AreaType.FOREHEAD:
            raise ValueError("Botox area must be forehead")
        return v


# Response Models

class BoundingBox(BaseModel):
    """Bounding box coordinates."""
    x: int = Field(..., description="Left coordinate")
    y: int = Field(..., description="Top coordinate") 
    width: int = Field(..., description="Width")
    height: int = Field(..., description="Height")


class SegmentResponse(BaseModel):
    """Response model for face segmentation."""
    mask_png: str = Field(..., description="Base64 encoded mask image")
    bbox: BoundingBox = Field(..., description="Mask bounding box")
    metadata: Dict[str, Any] = Field(..., description="Segmentation metadata")
    landmarks_count: Optional[int] = Field(None, description="Number of detected landmarks")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence")


class ProcessingParameters(BaseModel):
    """Processing parameters used for generation."""
    denoising_strength: float = Field(..., description="Denoising strength")
    guidance_scale: float = Field(..., description="Guidance scale")
    controlnet_scale: float = Field(..., description="ControlNet conditioning scale")
    mask_feather: int = Field(..., description="Mask feathering pixels")
    seed: int = Field(..., description="Random seed used")
    prompt: str = Field(..., description="Text prompt used")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt used")
    num_inference_steps: int = Field(..., description="Number of diffusion steps")
    inference_time_ms: int = Field(..., description="Inference time in milliseconds")


class QualityMetrics(BaseModel):
    """Quality control metrics."""
    id_similarity: float = Field(..., ge=0, le=1, description="Identity similarity (ArcFace)")
    ssim_off_mask: float = Field(..., ge=0, le=1, description="SSIM in off-target regions")
    id_warning: Optional[bool] = Field(None, description="Identity preservation warning")
    ssim_warning: Optional[bool] = Field(None, description="Off-target change warning")
    quality_passed: Optional[bool] = Field(None, description="Overall quality check")


class SimulationResponse(BaseModel):
    """Response model for aesthetic simulation."""
    result_png: str = Field(..., description="Base64 encoded result image")
    original_png: Optional[str] = Field(None, description="Base64 encoded original (for reference)")
    mask_png: Optional[str] = Field(None, description="Base64 encoded mask used")
    params: ProcessingParameters = Field(..., description="Processing parameters")
    qc: QualityMetrics = Field(..., description="Quality control metrics")
    warnings: Optional[List[str]] = Field(default_factory=list, description="Quality warnings")
    should_retry: Optional[bool] = Field(None, description="Suggests if generation should be retried")
    retry_reason: Optional[str] = Field(None, description="Reason for retry suggestion")


# Status and Health Models

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    models_loaded: Dict[str, bool] = Field(..., description="Model loading status")
    gpu_available: bool = Field(..., description="GPU availability")
    memory_usage: Optional[Dict[str, float]] = Field(None, description="Memory usage stats")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# Batch Processing Models (Future)

class BatchSimulationRequest(BaseModel):
    """Request model for batch simulation (future feature)."""
    images: List[str] = Field(..., max_items=10, description="List of base64 images")
    area: AreaType = Field(..., description="Facial area to modify")
    strength: int = Field(..., ge=0, le=100, description="Effect strength")
    pipeline: PipelineType = Field(default=PipelineType.SD_INPAINT, description="Processing pipeline")
    seed: Optional[int] = Field(default=None, description="Base random seed")


class BatchSimulationResponse(BaseModel):
    """Response model for batch simulation."""
    results: List[SimulationResponse] = Field(..., description="Individual simulation results")
    batch_id: str = Field(..., description="Batch processing ID")
    total_time_ms: int = Field(..., description="Total batch processing time")


# Configuration Models

class ModelConfig(BaseModel):
    """Model configuration."""
    model_name: str = Field(..., description="Model identifier")
    device: str = Field(..., description="Processing device")
    precision: str = Field(..., description="Model precision")
    optimization: List[str] = Field(default_factory=list, description="Applied optimizations")


class ProcessingConfig(BaseModel):
    """Processing configuration."""
    default_steps: int = Field(default=30, description="Default inference steps")
    max_resolution: int = Field(default=768, description="Maximum image resolution")
    enable_safety_checker: bool = Field(default=False, description="Safety checker enabled")
    quality_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "id_similarity": 0.35,
            "ssim_off_mask": 0.98
        },
        description="Quality control thresholds"
    )


# Warping Models (Weg B - Future)

class WarpingParameters(BaseModel):
    """Parameters for geometry warping (Weg B)."""
    amplitude: float = Field(..., ge=0, le=1, description="Warp amplitude")
    landmark_confidence_threshold: float = Field(default=0.8, description="Minimum landmark confidence")
    max_displacement_px: int = Field(default=20, description="Maximum pixel displacement")
    fallback_to_diffusion: bool = Field(default=True, description="Fallback to Weg A if landmarks fail")


class WarpingSimulationRequest(SimulationRequest):
    """Request model for warping-based simulation."""
    pipeline: PipelineType = Field(default=PipelineType.HYBRID_B, description="Must use hybrid pipeline")
    warping_params: Optional[WarpingParameters] = Field(None, description="Warping parameters")


# Utility functions for validation

def validate_base64_image(image_str: str) -> bool:
    """Validate base64 image string format."""
    import base64
    import io
    from PIL import Image
    
    try:
        # Remove data URL prefix if present
        if image_str.startswith('data:image'):
            image_str = image_str.split(',')[1]
        
        # Decode and verify it's a valid image
        image_bytes = base64.b64decode(image_str)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Basic format validation
        if image.format not in ['JPEG', 'PNG', 'JPG']:
            return False
            
        # Size validation
        if image.width > 2048 or image.height > 2048:
            return False
            
        return True
    except Exception:
        return False


def get_prompt_for_area(area: AreaType, language: str = "en") -> str:
    """Get default prompt for specific area and language."""
    prompts = {
        "en": {
            AreaType.LIPS: "fuller, plumper, smoother lips, enhanced volume, perfect symmetry, soft natural texture, hydrated, glossy finish, no makeup, professional aesthetic enhancement",
            AreaType.CHIN: "enhanced chin projection and definition, stronger jawline, refined contour, natural volume, preserve skin texture", 
            AreaType.CHEEKS: "enhanced cheek volume and contour, lifted appearance, defined cheekbones, natural fullness, avoid over-smoothing",
            AreaType.FOREHEAD: "completely smooth forehead, eliminate all horizontal lines and wrinkles, flawless skin texture, natural lighting"
        },
        "de": {
            AreaType.LIPS: "vollere, prallere, glattere Lippen, verstärktes Volumen, perfekte Symmetrie, weiche natürliche Textur, hydratisiert, glänzendes Finish, kein Make-up, professionelle ästhetische Verbesserung",
            AreaType.CHIN: "verstärkte Kinnprojektion und Definition, stärkere Kieferlinie, verfeinerte Kontur, natürliches Volumen, Hauttextur erhalten",
            AreaType.CHEEKS: "verstärktes Wangenvolumen und Kontur, gehobenes Aussehen, definierte Wangenknochen, natürliche Fülle, keine Überglättung", 
            AreaType.FOREHEAD: "völlig glatte Stirn, alle horizontalen Linien und Falten eliminieren, makellose Hauttextur, natürliche Beleuchtung"
        }
    }
    
    return prompts.get(language, prompts["en"]).get(area, "natural enhancement")


def get_adaptive_prompt_for_area(area: AreaType, strength: int, language: str = "en") -> str:
    """
    Get strength-adaptive prompt for area. Higher strength = more dramatic enhancement.
    
    Args:
        area: Facial area
        strength: 0-100 (0ml - 3ml)
        language: Language code
        
    Returns:
        Adaptive prompt string
    """
    # Normalize strength to 0-1
    s = max(0, min(100, strength)) / 100.0
    
    if area == AreaType.LIPS:
        if language == "de":
            if s < 0.2:
                return "natürlich hydratisierte Lippen, weiche Textur, subtile Verbesserung"
            elif s < 0.5:
                return "leicht volle Lippen mit perfekt symmetrischer Kontur, ultra-glatte seidige Textur, professionelle ästhetische Verbesserung, makellos definierte Lippenränder, gleichmäßige Fülle, luxuriös weiche Oberfläche"
            elif s < 0.8:
                return "mittlere Fülle der Lippen mit perfekt symmetrischer Herzform, ultra-glatte seidige Textur ohne Unebenheiten, professionelle ästhetische Verbesserung, makellos definierte Cupid's Bow, gleichmäßig voluminöse Ober- und Unterlippe, luxuriös weiche Oberfläche, perfekte Proportionen"
            else:
                return "sehr voluminöse volle Lippen mit perfekt symmetrischer Herzform, ultra-glatte seidige Porzellan-Textur ohne jegliche Unebenheiten, professionelle High-End ästhetische Verbesserung, makellos definierte Cupid's Bow, gleichmäßig voluminöse Ober- und Unterlippe, luxuriös weiche seidenglatte Oberfläche, perfekte anatomische Proportionen, kristallklare Definition, spiegelglatte Textur"
        else:  # English
            if s < 0.2:
                return "naturally hydrated lips, soft texture, subtle enhancement"
            elif s < 0.5:
                return "slightly full lips with perfectly symmetrical contour, ultra-smooth silky texture, professional aesthetic enhancement, flawlessly defined lip edges, even fullness, luxuriously soft surface"
            elif s < 0.8:
                return "moderately full lips with perfectly symmetrical heart shape, ultra-smooth silky texture without any imperfections, professional aesthetic enhancement, flawlessly defined Cupid's bow, evenly voluminous upper and lower lip, luxuriously soft surface, perfect proportions"
            else:
                return "very voluminous full lips with perfectly symmetrical heart shape, ultra-smooth silky porcelain texture without any imperfections whatsoever, professional high-end aesthetic enhancement, flawlessly defined Cupid's bow, evenly voluminous upper and lower lip, luxuriously soft silk-smooth surface, perfect anatomical proportions, crystal-clear definition, mirror-smooth texture"
    
    elif area == AreaType.CHIN:
        if language == "de":
            if s < 0.3:
                return "leichte Kinnverbesserung, dezente Projektion"
            elif s < 0.7:
                return "verstärkte Kinnprojektion, definierte Kieferlinie"
            else:
                return "dramatische Kinnverbesserung, starke Projektion, definierte Gesichtskontur"
        else:
            if s < 0.3:
                return "subtle chin enhancement, gentle projection"
            elif s < 0.7:
                return "enhanced chin projection, defined jawline"
            else:
                return "dramatic chin enhancement, strong projection, defined facial contour"
    
    elif area == AreaType.CHEEKS:
        if language == "de":
            if s < 0.3:
                return "leichte Wangenkontur, dezentes Volumen"
            elif s < 0.7:
                return "verstärktes Wangenvolumen, definierte Wangenknochen"
            else:
                return "dramatisches Wangenvolumen, stark definierte Wangenknochen, gehobene Gesichtskontur"
        else:
            if s < 0.3:
                return "subtle cheek contour, gentle volume"
            elif s < 0.7:
                return "enhanced cheek volume, defined cheekbones"
            else:
                return "dramatic cheek volume, strongly defined cheekbones, lifted facial contour"
    
    elif area == AreaType.FOREHEAD:
        if language == "de":
            if s < 0.3:
                return "reduzierte Stirnfalten, glattere Haut"
            elif s < 0.7:
                return "deutlich reduzierte Falten, glatte Stirn"
            else:
                return "völlig glatte Stirn, alle Falten eliminiert, perfekte Hauttextur"
        else:
            if s < 0.3:
                return "reduced forehead lines, smoother skin"
            elif s < 0.7:
                return "significantly reduced wrinkles, smooth forehead"
            else:
                return "completely smooth forehead, all wrinkles eliminated, perfect skin texture"
    
    # Fallback
    return get_prompt_for_area(area, language)
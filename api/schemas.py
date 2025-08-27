"""
Pydantic models for API request/response schemas for the Gemini-powered NuvaFace API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class AreaType(str, Enum):
    """Supported facial areas for aesthetic procedures."""
    LIPS = "lips"
    CHIN = "chin"
    CHEEKS = "cheeks"
    FOREHEAD = "forehead"

# --- Request Models ---

class SegmentRequest(BaseModel):
    """Request model for face segmentation endpoint."""
    image: str = Field(..., description="Base64 encoded image")
    area: AreaType = Field(..., description="Facial area to segment")

class SimulationRequest(BaseModel):
    """Request model for a Gemini-powered aesthetic simulation."""
    image: str = Field(..., description="Base64 encoded image")
    area: AreaType = Field(..., description="Facial area to modify")
    strength: float = Field(..., ge=0.0, le=5.0, description="Effect strength in milliliters (ml), e.g., 0.0 to 5.0")
    mask: Optional[str] = Field(default=None, description="Optional base64 mask for UX display")
    seed: Optional[int] = Field(default=None, description="Seed (not currently used by Gemini engine but kept for schema consistency)")

# --- Response Models ---

class BoundingBox(BaseModel):
    """Bounding box coordinates."""
    x: int
    y: int
    width: int
    height: int

class SegmentResponse(BaseModel):
    """Response model for face segmentation."""
    mask_png: str = Field(..., description="Base64 encoded mask image")
    bbox: BoundingBox = Field(..., description="Mask bounding box")
    metadata: Dict[str, Any] = Field(..., description="Segmentation metadata")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence")

class ProcessingParameters(BaseModel):
    """Simplified processing parameters for Gemini response."""
    model: str = Field(default="gemini-1.5-flash-latest", description="Model used for generation")
    strength_ml: float = Field(..., description="Volume in milliliters")

class QualityMetrics(BaseModel):
    """Simplified quality metrics for Gemini response."""
    notes: str = Field(default="Metrics like ID similarity are not applicable for direct generation models.", description="Notes on quality assessment")
    quality_passed: bool = Field(default=True)

class SimulationResponse(BaseModel):
    """Response model for aesthetic simulation."""
    result_png: str = Field(..., description="Base64 encoded result image")
    original_png: str = Field(..., description="Base64 encoded original for comparison")
    mask_png: str = Field(..., description="Base64 encoded mask used for UX")
    params: ProcessingParameters = Field(..., description="Processing parameters")
    qc: QualityMetrics = Field(..., description="Quality control metrics")
    warnings: List[str] = Field(default_factory=list)

# --- Status and Health Models ---

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    models_loaded: Dict[str, Any]
    gpu_available: bool

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

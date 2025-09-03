"""
Pydantic models for Medical AI Assistant API

Data validation and serialization schemas for all API endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Union, Any
from enum import Enum
import base64
import re

class TreatmentArea(str, Enum):
    """Supported treatment areas for analysis."""
    LIPS = "lips"
    CHEEKS = "cheeks"
    CHIN = "chin"
    FOREHEAD = "forehead"

class AnalysisModes(BaseModel):
    """Configuration for what types of analysis to perform."""
    risk_zones: bool = Field(default=True, description="Generate risk zone overlays")
    injection_points: bool = Field(default=True, description="Generate injection point recommendations")

class RiskMapRequest(BaseModel):
    """Request model for risk map analysis."""
    image: str = Field(..., description="Base64 encoded image or image URL")
    area: TreatmentArea = Field(..., description="Treatment area to analyze")
    modes: AnalysisModes = Field(default_factory=AnalysisModes, description="Analysis modes")
    
    @validator('image')
    def validate_image(cls, v):
        """Validate image data format."""
        if v.startswith('data:image'):
            # Data URL format
            try:
                header, data = v.split(',', 1)
                base64.b64decode(data)
                return v
            except Exception:
                raise ValueError("Invalid base64 image data")
        elif v.startswith('http'):
            # URL format
            url_pattern = re.compile(
                r'^https?://'  # http:// or https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            if not url_pattern.match(v):
                raise ValueError("Invalid image URL format")
            return v
        else:
            # Plain base64
            try:
                base64.b64decode(v)
                return v
            except Exception:
                raise ValueError("Invalid base64 data")

class Point(BaseModel):
    """2D coordinate point."""
    x: float = Field(..., description="X coordinate in pixels")
    y: float = Field(..., description="Y coordinate in pixels")

class RiskZone(BaseModel):
    """Risk zone overlay definition."""
    name: str = Field(..., description="Risk zone identifier")
    polygon: List[Point] = Field(..., description="Polygon vertices defining the risk area")
    severity: str = Field(..., description="Risk level: low, moderate, high, critical")
    color: str = Field(default="#FF4D4D", description="Display color (hex format)")
    opacity: float = Field(default=0.25, description="Overlay opacity (0-1)")
    tooltip: Optional[str] = Field(None, description="Tooltip text for user interface")
    medical_reference: Optional[str] = Field(None, description="Medical/anatomical reference")
    rationale: Optional[str] = Field(None, description="Why this area is risky")
    safety_recommendations: List[str] = Field(default_factory=list, description="Safety guidelines")
    consequences: List[str] = Field(default_factory=list, description="Potential complications")
    style: Optional[Dict[str, Any]] = Field(None, description="Additional styling properties")

class InjectionPoint(BaseModel):
    """Injection point recommendation."""
    label: str = Field(..., description="Point identifier/name")
    position: Point = Field(..., description="Injection point coordinates")
    code: Optional[str] = Field(None, description="MD Code identifier")
    depth: Optional[str] = Field(None, description="Injection depth: dermal, subcutaneous, supraperiosteal")
    technique: Optional[str] = Field(None, description="Injection technique")
    volume: Optional[str] = Field(None, description="Recommended volume/units")
    tool: Optional[str] = Field(None, description="Preferred tool: needle, cannula")
    notes: Optional[str] = Field(None, description="Additional clinical notes")
    confidence: float = Field(default=0.8, description="Confidence score (0-1)")
    warnings: List[str] = Field(default_factory=list, description="Safety warnings")
    source: Optional[Dict[str, str]] = Field(None, description="Medical reference source")

class ImageSize(BaseModel):
    """Image dimensions."""
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")

class RiskMapResponse(BaseModel):
    """Response model for risk map analysis."""
    analysis_id: str = Field(..., description="Unique analysis identifier")
    image_size: ImageSize = Field(..., description="Original image dimensions")
    risk_zones: List[RiskZone] = Field(default_factory=list, description="Identified risk zones")
    injection_points: List[InjectionPoint] = Field(default_factory=list, description="Recommended injection points")
    confidence_score: float = Field(..., description="Overall analysis confidence (0-1)")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    deterministic_hash: str = Field(..., description="Hash for result consistency validation")
    area: TreatmentArea = Field(..., description="Analyzed treatment area")
    modes_applied: AnalysisModes = Field(..., description="Applied analysis modes")
    fallback_used: bool = Field(default=False, description="Whether fallback templates were used")
    warnings: List[str] = Field(default_factory=list, description="Analysis warnings or limitations")
    medical_disclaimer: str = Field(..., description="Medical disclaimer text")

class ServiceStatus(BaseModel):
    """Individual service health status."""
    healthy: bool = Field(..., description="Service health status")
    details: Optional[str] = Field(None, description="Additional status details")

class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Overall system status")
    timestamp: int = Field(..., description="Unix timestamp of check")
    services: Dict[str, bool] = Field(..., description="Individual service statuses")
    version: str = Field(..., description="API version")

class AnalysisStatus(str, Enum):
    """Analysis status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

# Internal models for service communication

class LandmarkResult(BaseModel):
    """Result from facial landmark detection."""
    success: bool = Field(..., description="Detection success status")
    landmarks: List[Point] = Field(default_factory=list, description="Detected facial landmarks")
    confidence: float = Field(default=0.0, description="Detection confidence")
    error_message: Optional[str] = Field(None, description="Error details if failed")

class NormalizedFace(BaseModel):
    """Normalized face coordinate system."""
    landmarks: List[Point] = Field(..., description="Normalized landmark coordinates")
    face_bbox: Dict[str, float] = Field(..., description="Face bounding box")
    confidence: float = Field(..., description="Normalization confidence")
    alignment_applied: bool = Field(default=False, description="Whether face alignment was applied")

class AreaKnowledge(BaseModel):
    """Knowledge base for a treatment area."""
    area: TreatmentArea = Field(..., description="Treatment area")
    injection_points: List[Dict[str, Any]] = Field(default_factory=list, description="Injection point definitions")
    risk_zones: List[Dict[str, Any]] = Field(default_factory=list, description="Risk zone definitions")
    version: str = Field(default="1.0", description="Knowledge base version")
    last_updated: Optional[int] = Field(None, description="Last update timestamp")

class RuleDefinition(BaseModel):
    """Rule definition for coordinate calculation."""
    type: str = Field(..., description="Rule type identifier")
    anchors: List[str] = Field(..., description="Landmark anchor names")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Rule parameters")

class FallbackTemplate(BaseModel):
    """Fallback template when landmarks fail."""
    area: TreatmentArea = Field(..., description="Treatment area")
    injection_points: List[Dict[str, Any]] = Field(default_factory=list, description="Template injection points")
    confidence_penalty: float = Field(default=0.5, description="Confidence reduction factor")

# Validation models for internal use

class ValidationResult(BaseModel):
    """Result from safety validation."""
    valid: bool = Field(..., description="Validation passed")
    filtered_points: List[InjectionPoint] = Field(default_factory=list, description="Validated injection points")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    safety_violations: List[str] = Field(default_factory=list, description="Safety rule violations")

class ConsistencyCheck(BaseModel):
    """Result from deterministic consistency validation."""
    consistent: bool = Field(..., description="Results are consistent with previous runs")
    deviation_pixels: float = Field(default=0.0, description="Maximum coordinate deviation in pixels")
    warnings: List[str] = Field(default_factory=list, description="Consistency warnings")

# Configuration models

class APIConfig(BaseModel):
    """API configuration settings."""
    max_image_size: int = Field(default=2048, description="Maximum image dimension")
    max_processing_time: int = Field(default=30000, description="Maximum processing time in ms")
    enable_fallback: bool = Field(default=True, description="Enable fallback templates")
    enable_consistency_checks: bool = Field(default=True, description="Enable deterministic validation")
    log_level: str = Field(default="INFO", description="Logging level")

class SecurityConfig(BaseModel):
    """Security configuration."""
    enable_rate_limiting: bool = Field(default=True, description="Enable API rate limiting")
    max_requests_per_minute: int = Field(default=60, description="Rate limit per minute")
    require_api_key: bool = Field(default=False, description="Require API key authentication")
    allowed_origins: List[str] = Field(default=["*"], description="CORS allowed origins")

# Export all models
__all__ = [
    "TreatmentArea",
    "AnalysisModes", 
    "RiskMapRequest",
    "Point",
    "RiskZone",
    "InjectionPoint",
    "ImageSize",
    "RiskMapResponse",
    "HealthCheckResponse",
    "ErrorResponse",
    "LandmarkResult",
    "NormalizedFace",
    "AreaKnowledge",
    "RuleDefinition",
    "FallbackTemplate",
    "ValidationResult",
    "ConsistencyCheck",
    "APIConfig",
    "SecurityConfig"
]
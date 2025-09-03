"""
Medical AI Assistant Risk Map API

FastAPI service for analyzing facial landmarks and providing
medically-grounded injection point recommendations and risk zone overlays.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import traceback
from typing import Optional
import time

from models.schemas import (
    RiskMapRequest, 
    RiskMapResponse, 
    HealthCheckResponse,
    AnalysisStatus,
    ErrorResponse
)
from services.image_processor import ImageProcessor
from services.knowledge_loader import KnowledgeLoader
from services.coordinate_mapper import CoordinateMapper
from models.landmarks import FaceLandmarkDetector
from models.rules_engine import RulesEngine
from utils.deterministic import DeterministicValidator
from utils.face_alignment import FaceAligner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Medical AI Assistant - Risk Map API",
    description="Anatomically-grounded facial analysis for aesthetic treatment planning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core services
try:
    image_processor = ImageProcessor()
    landmark_detector = FaceLandmarkDetector()
    knowledge_loader = KnowledgeLoader()
    rules_engine = RulesEngine()
    coordinate_mapper = CoordinateMapper()
    face_aligner = FaceAligner()
    deterministic_validator = DeterministicValidator()
    
    logger.info("✅ All services initialized successfully")
except Exception as e:
    logger.error(f"❌ Service initialization failed: {str(e)}")
    raise

# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint for monitoring service status."""
    try:
        # Test core services
        services_status = {
            "image_processor": image_processor.is_healthy(),
            "landmark_detector": landmark_detector.is_healthy(),
            "knowledge_loader": knowledge_loader.is_healthy(),
            "rules_engine": rules_engine.is_healthy()
        }
        
        all_healthy = all(services_status.values())
        
        return HealthCheckResponse(
            status="healthy" if all_healthy else "degraded",
            timestamp=int(time.time()),
            services=services_status,
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")

# Main analysis endpoint
@app.post("/api/risk-map/analyze", response_model=RiskMapResponse)
async def analyze_risk_map(request: RiskMapRequest, background_tasks: BackgroundTasks):
    """
    Analyze facial image and return risk zones and injection points.
    
    This endpoint:
    1. Processes and validates the input image
    2. Detects facial landmarks using MediaPipe
    3. Normalizes coordinates for deterministic results
    4. Loads area-specific medical knowledge
    5. Applies rule engine to generate coordinates
    6. Returns structured overlay data
    """
    start_time = time.time()
    analysis_id = f"analysis_{int(start_time * 1000)}"
    
    try:
        logger.info(f"🔍 Starting analysis {analysis_id} for area: {request.area}")
        
        # Step 1: Process and validate image
        logger.debug("📸 Processing image...")
        image_data = await image_processor.process_image(request.image)
        
        if image_data is None:
            raise HTTPException(
                status_code=400, 
                detail="Invalid or corrupted image data"
            )
        
        # Step 2: Detect facial landmarks
        logger.debug("🎯 Detecting facial landmarks...")
        landmarks_result = await landmark_detector.detect_landmarks(image_data)
        
        if not landmarks_result.success:
            logger.warning(f"⚠️  Landmark detection failed, using fallback for {request.area}")
            return await _generate_fallback_response(
                request.area, 
                image_data.shape, 
                analysis_id,
                "Landmark detection failed - using template"
            )
        
        # Step 3: Normalize face coordinates
        logger.debug("📐 Normalizing coordinates...")
        normalized_face = face_aligner.normalize_face(
            landmarks_result.landmarks, 
            image_data.shape
        )
        
        # Step 4: Generate deterministic hash for consistency validation
        input_hash = deterministic_validator.generate_input_hash(
            landmarks_result.landmarks, 
            request.area
        )
        
        # Step 5: Load area-specific knowledge base
        logger.debug(f"📚 Loading knowledge for area: {request.area}")
        area_knowledge = knowledge_loader.load_area_knowledge(request.area)
        
        if not area_knowledge:
            raise HTTPException(
                status_code=404,
                detail=f"No knowledge base found for area: {request.area}"
            )
        
        # Step 6: Apply rules engine to generate coordinates
        risk_zones = []
        injection_points = []
        
        if request.modes.risk_zones:
            logger.debug("🚨 Generating risk zones...")
            risk_zones = rules_engine.apply_risk_zone_rules(
                area_knowledge.risk_zones,
                normalized_face,
                image_data.shape
            )
        
        if request.modes.injection_points:
            logger.debug("💉 Generating injection points...")
            injection_points = rules_engine.apply_injection_point_rules(
                area_knowledge.injection_points,
                normalized_face,
                image_data.shape
            )
        
        # Step 7: Apply safety validations
        logger.debug("🛡️  Applying safety validations...")
        injection_points = coordinate_mapper.validate_injection_safety(
            injection_points, 
            risk_zones, 
            request.area
        )
        
        # Step 8: Calculate confidence score
        confidence_score = _calculate_confidence_score(
            landmarks_result,
            normalized_face,
            len(injection_points),
            len(risk_zones)
        )
        
        # Step 9: Prepare response
        processing_time = int((time.time() - start_time) * 1000)
        
        response = RiskMapResponse(
            analysis_id=analysis_id,
            image_size={
                "width": image_data.shape[1],
                "height": image_data.shape[0]
            },
            risk_zones=risk_zones,
            injection_points=injection_points,
            confidence_score=confidence_score,
            processing_time_ms=processing_time,
            deterministic_hash=input_hash,
            area=request.area,
            modes_applied=request.modes,
            fallback_used=False,
            warnings=[],
            medical_disclaimer="For trained medical professionals only. Not for patient consultation."
        )
        
        # Step 10: Validate consistency (background task)
        background_tasks.add_task(
            deterministic_validator.validate_consistency,
            input_hash,
            response.dict()
        )
        
        logger.info(f"✅ Analysis {analysis_id} completed in {processing_time}ms")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Analysis {analysis_id} failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

async def _generate_fallback_response(
    area: str, 
    image_shape: tuple, 
    analysis_id: str,
    reason: str
) -> RiskMapResponse:
    """Generate template-based fallback response when landmark detection fails."""
    
    logger.info(f"🔄 Generating fallback response for {area}: {reason}")
    
    try:
        # Load fallback templates
        fallback_data = knowledge_loader.load_fallback_templates(area)
        
        if not fallback_data:
            # Minimal safe response if no templates available
            return RiskMapResponse(
                analysis_id=analysis_id,
                image_size={"width": image_shape[1], "height": image_shape[0]},
                risk_zones=[],
                injection_points=[],
                confidence_score=0.1,
                processing_time_ms=50,
                deterministic_hash="fallback",
                area=area,
                modes_applied={"risk_zones": False, "injection_points": False},
                fallback_used=True,
                warnings=[
                    "Automated detection failed - no template available",
                    "Manual assessment required for treatment planning"
                ],
                medical_disclaimer="FALLBACK MODE: For trained medical professionals only."
            )
        
        # Scale template to image size
        scaled_points = coordinate_mapper.scale_template_to_image(
            fallback_data.injection_points,
            image_shape
        )
        
        return RiskMapResponse(
            analysis_id=analysis_id,
            image_size={"width": image_shape[1], "height": image_shape[0]},
            risk_zones=[],  # Conservative: no risk zones in fallback
            injection_points=scaled_points,
            confidence_score=0.3,
            processing_time_ms=100,
            deterministic_hash="fallback_template",
            area=area,
            modes_applied={"risk_zones": False, "injection_points": True},
            fallback_used=True,
            warnings=[
                "Face landmarks not detected - using approximate template",
                "Results are approximate - manual verification required",
                "Consider retaking photo with better lighting/positioning"
            ],
            medical_disclaimer="TEMPLATE MODE: Approximate positioning only. Manual verification required."
        )
        
    except Exception as e:
        logger.error(f"Fallback generation failed: {str(e)}")
        
        # Ultimate minimal response
        return RiskMapResponse(
            analysis_id=analysis_id,
            image_size={"width": image_shape[1], "height": image_shape[0]},
            risk_zones=[],
            injection_points=[],
            confidence_score=0.0,
            processing_time_ms=10,
            deterministic_hash="minimal_fallback",
            area=area,
            modes_applied={"risk_zones": False, "injection_points": False},
            fallback_used=True,
            warnings=[
                "Analysis failed - no results available",
                "Manual assessment required",
                "Consider retaking photo or seeking specialist consultation"
            ],
            medical_disclaimer="FAILED ANALYSIS: Manual assessment required."
        )

def _calculate_confidence_score(
    landmarks_result,
    normalized_face,
    num_injection_points: int,
    num_risk_zones: int
) -> float:
    """Calculate overall confidence score for the analysis."""
    
    # Base confidence from landmark detection
    landmark_confidence = landmarks_result.confidence if hasattr(landmarks_result, 'confidence') else 0.8
    
    # Face normalization quality
    normalization_confidence = normalized_face.confidence if hasattr(normalized_face, 'confidence') else 0.9
    
    # Results completeness factor
    expected_points = {"lips": 6, "cheeks": 8, "chin": 6, "forehead": 7}
    expected_zones = {"lips": 4, "cheeks": 6, "chin": 5, "forehead": 5}
    
    completeness_factor = min(1.0, (num_injection_points + num_risk_zones) / 8.0)
    
    # Combined confidence score
    overall_confidence = (
        landmark_confidence * 0.5 +
        normalization_confidence * 0.3 +
        completeness_factor * 0.2
    )
    
    return max(0.1, min(1.0, overall_confidence))

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return ErrorResponse(
        error="Not Found",
        message="The requested resource was not found",
        status_code=404
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return ErrorResponse(
        error="Internal Server Error",
        message="An unexpected error occurred",
        status_code=500
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services and perform startup checks."""
    logger.info("🚀 Medical AI Assistant API starting up...")
    
    # Warm up services
    try:
        await knowledge_loader.warm_up()
        await landmark_detector.warm_up()
        logger.info("✅ Service warm-up completed")
    except Exception as e:
        logger.error(f"❌ Warm-up failed: {str(e)}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    logger.info("🛑 Medical AI Assistant API shutting down...")
    
    try:
        await landmark_detector.cleanup()
        await image_processor.cleanup()
        logger.info("✅ Cleanup completed")
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
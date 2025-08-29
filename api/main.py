"""
FastAPI main application for NuvaFace aesthetic simulation API.
Implements endpoints for face segmentation and Gemini-powered aesthetic simulation.
"""

import time
import random
import logging
import io
from io import BytesIO
import hashlib
import secrets
import uuid
from fastapi import FastAPI, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Import schemas
from .schemas import (
    SegmentRequest, SegmentResponse, BoundingBox,
    SimulationRequest, SimulationResponse,
    ProcessingParameters, QualityMetrics,
    HealthResponse, ErrorResponse,
    AreaType
)

# Import engine modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.utils import load_image, image_to_base64, preprocess_image
from engine.parsing import segment_area, validate_area
from engine.edit_gemini import generate_gemini_simulation # New Gemini Engine
from models import get_device, get_cache_info

# Direct Gemini Test (inline to avoid import issues)
import os
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="NuvaFace API",
    description="Aesthetic procedure simulation API with AI-powered facial editing via Gemini",
    version="2.0.0", # Version bump for new architecture
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Anti-Cache Middleware for all responses
@app.middleware("http")
async def add_anti_cache_headers(request, call_next):
    response = await call_next(request)
    
    # Add anti-cache headers to all API responses
    if request.url.path.startswith("/api/") or request.url.path.startswith("/simulate") or request.url.path.startswith("/test"):
        response.headers["Cache-Control"] = "no-store, no-cache, max-age=0, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        # Add unique response ID for tracking
        response.headers["X-Response-ID"] = str(uuid.uuid4())
        response.headers["X-Timestamp"] = str(int(time.time() * 1000))
    
    return response

# Mount static files for UI
ui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui")
if os.path.exists(ui_path):
    app.mount("/ui", StaticFiles(directory=ui_path, html=True), name="ui")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting NuvaFace API with Gemini Engine...")
    device = get_device()
    logger.info(f"Local device for segmentation: {device}")
    # No models to warm up locally for generation

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        models_loaded={"segmentation": True, "generation": True}, # Changed "gemini-api" to True
        gpu_available=get_device() == "cuda"
    )

@app.post("/segment", response_model=SegmentResponse)
async def segment_face(request: SegmentRequest):
    """
    Segment facial area to generate mask for aesthetic editing.
    This is now primarily for UX purposes.
    """
    try:
        image = load_image(request.image)
        processed_image, preprocess_meta = preprocess_image(image, target_size=768, align_face=False)
        
        if not validate_area(request.area):
            raise HTTPException(status_code=400, detail=f"Unsupported area: {request.area}")
        
        mask_image, segment_metadata = segment_area(processed_image, request.area)
        
        return SegmentResponse(
            mask_png=image_to_base64(mask_image, format='PNG'),
            bbox=BoundingBox(**segment_metadata['bbox']),
            metadata=segment_metadata,
            confidence=segment_metadata.get('confidence', 1.0) # Add this line back
        )
    except Exception as e:
        logger.error(f"Segmentation error: {e}")
        raise HTTPException(status_code=500, detail=f"Segmentation failed: {str(e)}")

@app.post("/simulate/filler", response_model=SimulationResponse)
async def simulate_filler(request: SimulationRequest):
    """
    Simulates a filler procedure by calling the Gemini API.
    The 'strength' parameter is interpreted as milliliters (ml).
    """
    return await _simulate_procedure(request)

async def _simulate_procedure(request: SimulationRequest):
    """
    Handles the simulation by calling the Gemini engine.
    """
    try:
        start_time = time.time()
        
        # The 'strength' from the slider is now treated as 'volume_ml'
        volume_ml = request.strength 
        
        logger.info(f"DEBUG: Received simulation request for {request.area} with {volume_ml}ml")
        logger.info(f"DEBUG: Request area value: {request.area.value}")

        # Load original image - use directly like working test (NO preprocessing!)
        original_image = load_image(request.image)
        logger.info(f"DEBUG: Loaded original image: {original_image.size}")
        
        # Use the working direct Gemini call (same as test endpoint - NO masks, NO preprocessing!)
        logger.info(f"DEBUG: Calling working direct Gemini with {volume_ml}ml {request.area.value}")
        result_image = await _direct_gemini_call_working(original_image, float(volume_ml), request.area.value)
        logger.info(f"DEBUG: Received result image from Gemini: {result_image.size}")
        
        # Check if result is identical to input (compare the same images we sent to Gemini)
        original_bytes = io.BytesIO()
        result_bytes = io.BytesIO()
        original_image.save(original_bytes, format='PNG')  # Use original_image like working test!
        result_image.save(result_bytes, format='PNG')
        
        original_data = original_bytes.getvalue()
        result_data = result_bytes.getvalue()
        
        identical = original_data == result_data
        logger.info(f"DEBUG: Result image is identical to original: {identical}")
        logger.info(f"DEBUG: Original image bytes: {len(original_data)}")
        logger.info(f"DEBUG: Result image bytes: {len(result_data)}")
        # logger.info(f"DEBUG: First 50 bytes original: {original_data[:50]}")
        # logger.info(f"DEBUG: First 50 bytes result: {result_data[:50]}")
        
        if identical:
            logger.warning(f"WARNING: Gemini returned identical image! Volume was {volume_ml}ml for area {request.area.value}")
            logger.warning(f"WARNING: This indicates quota/rate limiting or API degradation")
        else:
            logger.info(f"SUCCESS: Gemini returned different image (expected behavior)")
        
        # --- End of New Gemini Call ---

        # Convert images to base64 for the response (no masks in direct mode)
        result_base64 = image_to_base64(result_image)
        original_base64 = image_to_base64(original_image)
        # Create empty mask for compatibility
        from PIL import Image as PILImage
        empty_mask = PILImage.new('L', original_image.size, 0)  # Empty black mask
        mask_base64 = image_to_base64(empty_mask)
        
        end_time = time.time()
        
        # Create a simplified response as detailed QC metrics are less relevant now
        # Generate unique request ID and hash for anti-cache validation
        request_id = str(uuid.uuid4())
        
        # Calculate SHA-256 hash of result image bytes for uniqueness verification
        result_bytes = base64.b64decode(result_base64)
        result_hash = hashlib.sha256(result_bytes).hexdigest()
        
        # Log for anti-cache verification
        logger.info(f"🔍 ANTI-CACHE: Request ID: {request_id}")
        logger.info(f"🔍 ANTI-CACHE: Result Hash: {result_hash[:16]}...")
        logger.info(f"🔍 ANTI-CACHE: Volume: {volume_ml}ml, Area: {request.area.value}")
        
        return SimulationResponse(
            result_png=result_base64,
            original_png=original_base64,
            mask_png=mask_base64,
            params=ProcessingParameters(
                model="gemini-2.5-flash-image-preview",
                strength_ml=volume_ml  # Fixed: use strength_ml instead of strength
            ),
            qc=QualityMetrics(
                quality_passed=True,
                request_id=request_id,  # Add request ID for tracking
                result_hash=result_hash  # Add result hash for uniqueness verification
            ),
            warnings=[],
        )
        
    except Exception as e:
        logger.error(f"Gemini simulation error: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

@app.post("/test/direct-gemini")
async def test_direct_gemini(request: dict):
    """
    TEST ENDPOINT: Direkter Gemini-Call ohne Pipeline-Komplexität
    Upload -> Direkter 3.0ml Lip Enhancement Test
    """
    try:
        start_time = time.time()
        
        logger.info("DEBUG: Starting direct Gemini test...")
        
        # Bild laden (nur Base64 Support für Test)
        if 'image' not in request:
            raise HTTPException(status_code=400, detail="No image provided")
            
        original_image = load_image(request['image'])
        logger.info(f"DEBUG: Direct test - loaded image: {original_image.size}")
        
        # Use the working direct Gemini call for test endpoint (fixed 3.0ml lips)
        result_image = await _direct_gemini_call_working(original_image, 3.0, "lips")
        
        logger.info(f"DEBUG: Direct test - result image: {result_image.size}")
        
        # Einfacher Vergleich
        original_bytes = BytesIO()
        result_bytes = BytesIO()
        original_image.save(original_bytes, format='PNG')
        result_image.save(result_bytes, format='PNG')
        
        identical = original_bytes.getvalue() == result_bytes.getvalue()
        logger.info(f"DEBUG: Direct test - images identical: {identical}")
        
        end_time = time.time()
        
        return {
            "success": True,
            "result_png": image_to_base64(result_image),
            "original_png": image_to_base64(original_image),
            "processing_time_ms": int((end_time - start_time) * 1000),
            "images_identical": identical,
            "test_prompt": "3.0ml Lip Enhancement (Major Volume Transformation)",
            "message": "Direct Gemini call completed - compare with normal pipeline"
        }
        
    except Exception as e:
        logger.error(f"Direct Gemini test error: {e}")
        raise HTTPException(status_code=500, detail=f"Direct test failed: {str(e)}")

@app.get("/debug/api-key")
async def debug_api_key():
    """Debug endpoint to check API key setup"""
    api_key = os.getenv("GOOGLE_API_KEY") 
    if not api_key:
        return {"error": "GOOGLE_API_KEY not set"}
    
    return {
        "api_key_prefix": api_key[:10] + "...",
        "api_key_length": len(api_key),
        "environment": "cloud_run"
    }

async def _direct_gemini_call_working(input_image, volume_ml: float, area: str):
    """Working direct Gemini call - based on successful test endpoint"""
    import base64
    from PIL import Image
    
    # API Key
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    # Client initialisieren
    client = genai.Client(api_key=api_key)
    
    # Get the right prompt based on area and volume
    if area == "lips":
        prompt = get_prompt_for_lips(volume_ml)
    else:
        # Default fallback prompt
        prompt = f"Perform {area} enhancement with {volume_ml}ml treatment. Show natural, photorealistic results with enhanced volume and definition while keeping all other facial features exactly unchanged."
    
    logger.info(f"🔍 DEBUG: Using working direct call for {volume_ml}ml {area}")
    logger.info(f"🔍 DEBUG: Input image size: {input_image.size}")
    
    # Bild in JPEG konvertieren (für bessere Kompatibilität)
    if input_image.mode != 'RGB':
        input_image = input_image.convert('RGB')
    
    # Bild zu Bytes
    img_buffer = BytesIO()
    input_image.save(img_buffer, format='JPEG', quality=95)
    img_bytes = img_buffer.getvalue()
    
    try:
        logger.info(f"🔍 DEBUG: Calling Gemini 2.5 Flash Image directly...")
        
        # Content für multimodalen Input (working version)
        content = types.Content(
            parts=[
                types.Part(text=prompt),
                types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=img_bytes))
            ]
        )
        
        # Generate random seed for each call to prevent caching/identical results
        random_seed = secrets.randbelow(1000000)  # 0-999999
        logger.info(f"🎲 ANTI-CACHE: Using random seed: {random_seed}")
        
        # Gemini-Call mit Image-Response (working version) - ANTI-CACHE CONFIG
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview", 
            contents=[content],
            config=types.GenerateContentConfig(
                response_modalities=[types.Modality.TEXT, types.Modality.IMAGE],
                temperature=0.4,  # Increased from 0.3 for more stochasticity
                top_p=0.9,  # Add top_p for additional randomness
                # Note: Gemini doesn't support seeds directly, but we log it for tracking
                seed=None,  # Explicitly no seed caching
            )
        )
        
        logger.info(f"✅ Working Gemini call successful!")
        
        # Response verarbeiten
        if not response.candidates or not response.candidates[0].content:
            raise Exception("No response content from Gemini")
        
        # Bild-Part finden
        image_part = None
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_part = part
                break
        
        if not image_part:
            raise Exception("No image data in Gemini response")
        
        # Bild-Daten extrahieren
        image_data = image_part.inline_data.data
        
        if isinstance(image_data, bytes):
            logger.info("🔍 DEBUG: Got RAW BYTES from Gemini - using directly! ✅")
            image_bytes = image_data
        elif isinstance(image_data, str):
            logger.info("🔍 DEBUG: Got Base64 string - decoding...")
            image_bytes = base64.b64decode(image_data)
        else:
            raise Exception(f"Unexpected image data type: {type(image_data)}")
        
        # Bytes zu PIL Image
        result_image = Image.open(BytesIO(image_bytes))
        
        logger.info(f"🔍 DEBUG: Result image size: {result_image.size}")
        logger.info(f"✅ Working direct Gemini call completed successfully!")
        
        return result_image
        
    except Exception as e:
        logger.error(f"❌ ERROR: Working Gemini call failed: {e}")
        raise Exception(f"Working Gemini call failed: {e}")

def get_prompt_for_lips(volume_ml: float) -> str:
    """Generate volume-specific prompts optimized for Gemini 2.5 Flash Image"""
    
    # Calculate intensity percentage (0-100%) based on volume
    intensity = min(volume_ml * 20, 100)  # 5ml = 100%
    
    if volume_ml <= 0.5:  # 0-0.5ml: Minimal hydration
        return f"""Perform minimal lip enhancement with {volume_ml}ml hyaluronic acid.
VOLUME EFFECT: {intensity:.0f}% intensity - MINIMAL HYDRATION
- Slight hydration and natural texture enhancement
- Very subtle lip border definition
- Result: naturally hydrated, healthy-looking lips

POSITION & TECHNICAL REQUIREMENTS:
- CRITICAL: Keep EXACT same face position, angle, and framing as input
- CRITICAL: Maintain IDENTICAL head position and orientation 
- CRITICAL: Keep SAME background, lighting, and composition
- CRITICAL: Do NOT center, crop, or reposition the face
- CRITICAL: Only lips change - everything else EXACTLY as original
- Photorealistic result with same resolution and quality as input
- Natural lip texture and color
- Keep all other facial features exactly unchanged"""
    
    elif volume_ml <= 2.0:  # 0.5-2ml: Natural enhancement - ENHANCED for real portraits  
        return f"""Perform professional lip enhancement with {volume_ml}ml hyaluronic acid.
VOLUME EFFECT: {intensity:.0f}% intensity - STRONG NATURAL ENHANCEMENT
- Significant volume increase with noticeable fullness
- Clear lip projection and attractive, youthful appearance
- Well-defined, pronounced cupid's bow
- Result: visibly fuller, more attractive lips with natural beauty

SPECIFIC INSTRUCTIONS FOR VISIBLE RESULTS:
- Add 40-60% volume to both upper (35%) and lower lips (65%) 
- Create clear, defined lip borders that are noticeably enhanced
- Enhance cupid's bow prominently for attractive definition
- Show realistic skin texture with VISIBLE fullness increase
- Make the enhancement clearly noticeable but naturally beautiful
- Maintain natural skin tone and lighting
- NO other facial changes - only lip enhancement with visible results

POSITION & TECHNICAL REQUIREMENTS:
- CRITICAL: Keep EXACT same face position, angle, and framing as input
- CRITICAL: Maintain IDENTICAL head position and orientation 
- CRITICAL: Keep SAME background, lighting, and composition
- CRITICAL: Do NOT center, crop, or reposition the face
- CRITICAL: Only lips change - everything else EXACTLY as original
- Photorealistic result with noticeable before/after difference
- Same resolution and quality as input
- Natural lip texture and color but clearly enhanced size
- Professional aesthetic treatment appearance
- Keep all other facial features exactly unchanged
- IMPORTANT: Enhancement should be clearly visible and attractive
    
    elif volume_ml <= 4.0:  # 2-4ml: Major enhancement - AGGRESSIVE for real portraits
        return f"""Perform DRAMATIC lip enhancement with {volume_ml}ml hyaluronic acid injection.
VOLUME EFFECT: {intensity:.0f}% intensity - EXTREME VOLUME TRANSFORMATION
- MASSIVE volume increase with dramatic, pronounced fullness
- Very strong lip projection creating luxurious, plump appearance  
- Dramatically pronounced cupid's bow definition
- Bold, Instagram-worthy lip enhancement
- Result: DRAMATICALLY fuller, model-like, luxury lips

SPECIFIC INSTRUCTIONS FOR MAXIMUM EFFECT:
- Add 70-90% volume increase to BOTH upper (40%) and lower lips (60%)
- Create BOLD definition of lip borders with clear edges
- Enhance cupid's bow DRAMATICALLY and prominently
- Make lips noticeably LARGER and more voluminous than original
- Show enhanced fullness with realistic texture but OBVIOUS size increase
- Create professional aesthetic treatment look with VISIBLE transformation
- Maintain natural skin tone and lighting
- NO other facial changes - ONLY dramatic lip enhancement

POSITION & TECHNICAL REQUIREMENTS:
- CRITICAL: Keep EXACT same face position, angle, and framing as input
- CRITICAL: Maintain IDENTICAL head position and orientation 
- CRITICAL: Keep SAME background, lighting, and composition
- CRITICAL: Do NOT center, crop, or reposition the face
- CRITICAL: Only lips change - everything else EXACTLY as original
- Photorealistic result with CLEAR before/after difference
- Same resolution and quality as input
- Natural lip texture and color but ENHANCED size
- Professional luxury aesthetic treatment appearance
- Keep all other facial features exactly unchanged
- CRITICAL: Make the lip enhancement VISIBLY DRAMATIC and obvious

    else:  # 4ml+: Ultra-high volume - MAXIMUM TRANSFORMATION
        return f"""Perform ULTRA-DRAMATIC lip enhancement with {volume_ml}ml hyaluronic acid injection.
VOLUME EFFECT: {intensity:.0f}% intensity - MAXIMUM VOLUME TRANSFORMATION
- EXTREME volume increase with MAXIMUM dramatic fullness
- Ultra-strong lip projection creating bold, luxury appearance
- EXTREMELY pronounced cupid's bow definition
- Celebrity-level, ultra-plump lip enhancement  
- Result: MAXIMUM fuller, glamorous, ultra-luxury lips

ULTRA-AGGRESSIVE INSTRUCTIONS:
- Add 90-110% volume increase to BOTH upper (35%) and lower lips (65%)
- Create EXTREMELY BOLD definition of lip borders with sharp, clear edges
- Enhance cupid's bow to MAXIMUM prominence and definition
- Make lips SIGNIFICANTLY LARGER and dramatically more voluminous than original
- Show ultra-enhanced fullness with realistic texture but EXTREME size increase
- Create luxury celebrity aesthetic treatment look with MAXIMUM transformation
- Maintain natural skin tone and lighting
- NO other facial changes - ONLY ultra-dramatic lip enhancement

POSITION & TECHNICAL REQUIREMENTS:
- CRITICAL: Keep EXACT same face position, angle, and framing as input
- CRITICAL: Maintain IDENTICAL head position and orientation 
- CRITICAL: Keep SAME background, lighting, and composition
- CRITICAL: Do NOT center, crop, or reposition the face
- CRITICAL: Only lips change - everything else EXACTLY as original
- Photorealistic result with EXTREME before/after difference
- Same resolution and quality as input  
- Natural lip texture and color but MAXIMUM enhanced size
- Ultra-luxury celebrity aesthetic treatment appearance
- Keep all other facial features exactly unchanged
- CRITICAL: Make the lip enhancement EXTREMELY DRAMATIC and unmistakable

async def _direct_gemini_test_inline(input_image):
    """Inline direct Gemini test to avoid import issues"""
    import base64
    from PIL import Image
    
    # API Key prüfen
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    # Client initialisieren
    client = genai.Client(api_key=api_key)
    
    # Fester Test-Prompt für 3.0ml Lip Enhancement mit Position-Lock
    prompt = """Perform major lip enhancement with 3.0ml hyaluronic acid.
VOLUME EFFECT: 60% intensity - MAJOR VOLUME TRANSFORMATION
- Major volume increase with dramatic fullness
- Strong lip projection and luxurious appearance  
- Very pronounced cupid's bow definition
- Result: dramatically fuller, luxurious-looking lips

SPECIFIC INSTRUCTIONS:
- Add 50-65% volume to both upper (45%) and lower lips (55%)
- Create strong definition of lip borders
- Enhance cupid's bow prominently
- Show realistic skin texture with enhanced fullness
- Maintain natural skin tone and lighting
- NO other facial changes - only lip enhancement

POSITION & TECHNICAL REQUIREMENTS:
- CRITICAL: Keep EXACT same face position, angle, and framing as input
- CRITICAL: Maintain IDENTICAL head position and orientation 
- CRITICAL: Keep SAME background, lighting, and composition
- CRITICAL: Do NOT center, crop, or reposition the face
- CRITICAL: Only lips change - everything else EXACTLY as original
- Photorealistic result
- Same resolution and quality as input
- Natural lip texture and color
- Professional aesthetic treatment appearance
- Keep all other facial features exactly unchanged"""

    logger.info(f"🔍 DEBUG: Using inline test prompt for 3.0ml lips")
    logger.info(f"🔍 DEBUG: Input image size: {input_image.size}")
    
    # Bild in JPEG konvertieren (für bessere Kompatibilität)
    if input_image.mode != 'RGB':
        input_image = input_image.convert('RGB')
    
    # Bild zu Bytes
    img_buffer = BytesIO()
    input_image.save(img_buffer, format='JPEG', quality=95)
    img_bytes = img_buffer.getvalue()
    
    try:
        logger.info(f"🔍 DEBUG: Calling Gemini 2.5 Flash Image directly...")
        
        # Content für multimodalen Input (corrected syntax)
        content = types.Content(
            parts=[
                types.Part(text=prompt),
                types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=img_bytes))
            ]
        )
        
        # Gemini-Call mit Image-Response
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview", 
            contents=[content],
            config=types.GenerateContentConfig(
                response_modalities=[types.Modality.TEXT, types.Modality.IMAGE],
                temperature=0.3,
            )
        )
        
        logger.info(f"✅ Gemini call successful!")
        
        # Response verarbeiten
        if not response.candidates or not response.candidates[0].content:
            raise Exception("No response content from Gemini")
        
        # Bild-Part finden
        image_part = None
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_part = part
                break
        
        if not image_part:
            raise Exception("No image data in Gemini response")
        
        # Bild-Daten extrahieren
        image_data = image_part.inline_data.data
        
        if isinstance(image_data, bytes):
            logger.info("🔍 DEBUG: Got RAW BYTES from Gemini - using directly! ✅")
            image_bytes = image_data
        elif isinstance(image_data, str):
            logger.info("🔍 DEBUG: Got Base64 string - decoding...")
            image_bytes = base64.b64decode(image_data)
        else:
            raise Exception(f"Unexpected image data type: {type(image_data)}")
        
        # Bytes zu PIL Image
        result_image = Image.open(BytesIO(image_bytes))
        
        logger.info(f"🔍 DEBUG: Result image size: {result_image.size}")
        logger.info(f"✅ Direct Gemini test completed successfully!")
        
        return result_image
        
    except Exception as e:
        logger.error(f"❌ ERROR: Direct Gemini call failed: {e}")
        raise Exception(f"Direct Gemini test failed: {e}")

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
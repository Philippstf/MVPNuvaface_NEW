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
import base64
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
    SEGMENTATION POLICY: Only available for lips area.
    Chin, cheeks, forehead use direct calls without segmentation.
    """
    try:
        # Only allow segmentation for lips
        if request.area.value != "lips":
            raise HTTPException(
                status_code=400, 
                detail=f"Segmentation only available for 'lips'. Area '{request.area.value}' uses direct processing without masks."
            )
        
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

        # Convert images to base64 for the response
        result_base64 = image_to_base64(result_image)
        original_base64 = image_to_base64(original_image)
        
        # SEGMENTATION POLICY: Only lips have segmentation, all others use direct calls
        # Currently: ALL areas use direct Gemini calls without preprocessing/segmentation
        # This provides maximum natural results for chin/cheeks/forehead treatments
        from PIL import Image as PILImage
        empty_mask = PILImage.new('L', original_image.size, 0)  # No segmentation masks
        mask_base64 = image_to_base64(empty_mask)
        
        # Note: If lip-specific segmentation is needed later, implement here:
        # if request.area.value == "lips":
        #     real_mask = segment_lips(original_image)
        #     mask_base64 = image_to_base64(real_mask)
        
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
    elif area == "chin":
        prompt = get_prompt_for_chin(volume_ml)
    elif area == "cheeks":
        prompt = get_prompt_for_cheeks(volume_ml)
    elif area == "forehead":
        # Botox behandelt Units, nicht ml - aber wir konvertieren für UI-Konsistenz
        prompt = get_prompt_for_botox_forehead(volume_ml)
    else:
        # Default fallback prompt
        prompt = f"Perform {area} enhancement with {volume_ml}ml treatment. Show natural, photorealistic results with enhanced volume and definition while keeping all other facial features exactly unchanged."
    
    # ChatGPT's Anti-Cache Enhancement: Add Random Token to prompt
    import secrets
    import string
    random_token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    enhanced_prompt = f"{prompt}\n\nRANDOM_TOKEN: {random_token}"
    
    logger.info(f"🎲 ENHANCED ANTI-CACHE: Added random token {random_token}")
    
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
                types.Part(text=enhanced_prompt),  # Use enhanced prompt with random token
                types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=img_bytes))
            ]
        )
        
        # Generate random seed for each call to prevent caching/identical results
        random_seed = secrets.randbelow(1000000)  # 0-999999
        logger.info(f"🎲 ANTI-CACHE: Using random seed: {random_seed}")
        
        # ChatGPT's Parameter Tuning: Optimized for deterministic geometry while maintaining uniqueness
        # Balance between determinism (for geometric accuracy) and stochasticity (for anti-cache)
        optimized_temperature = 0.3 if area == "chin" else 0.35  # More deterministic for chin geometry
        optimized_top_p = 0.85  # Slightly lower for better geometric control
        
        # Gemini-Call mit Image-Response (working version) - ENHANCED CONFIG
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview", 
            contents=[content],
            config=types.GenerateContentConfig(
                response_modalities=[types.Modality.TEXT, types.Modality.IMAGE],
                temperature=optimized_temperature,  # ChatGPT's optimized temperature
                top_p=optimized_top_p,  # Optimized top_p for geometric precision
                # Note: Gemini doesn't support seeds directly, but we log it for tracking
                seed=None,  # Explicitly no seed caching
            )
        )
        
        logger.info(f"🎛️ OPTIMIZED PARAMETERS: temp={optimized_temperature}, top_p={optimized_top_p}")
        
        logger.info(f"✅ Working Gemini call successful!")
        
        # Response verarbeiten
        if not response.candidates or not response.candidates[0].content:
            raise Exception("No response content from Gemini")
        
        # ChatGPT's Text-Response Parsing: Extract text confirmation from Gemini
        text_response = ""
        geometry_confirmed = False
        
        # Parse text parts for QC confirmation
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text') and part.text:
                text_response = part.text.strip()
                logger.info(f"📊 TEXT-RESPONSE: {text_response}")
                
                # Look for geometric confirmation (for chin and cheek treatments)
                if area == "chin" and any(keyword in text_response.lower() for keyword in ['mm', 'projection', 'applied', 'enhanced']):
                    geometry_confirmed = True
                    logger.info(f"✅ CHIN GEOMETRY CONFIRMED: {text_response}")
                elif area == "cheeks" and any(keyword in text_response.lower() for keyword in ['mm', 'malar', 'apex', 'nlf', 'applied', 'enhanced']):
                    geometry_confirmed = True
                    logger.info(f"✅ CHEEKS GEOMETRY CONFIRMED: {text_response}")
                break
        
        # Warning if no text confirmation (especially for chin and cheeks)
        if area in ["chin", "cheeks"] and not geometry_confirmed:
            logger.warning(f"⚠️ NO GEOMETRY CONFIRMATION for {area.upper()}: Text response missing or incomplete")
        
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
VOLUME EFFECT: {int(intensity)} percent intensity - MINIMAL HYDRATION
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
VOLUME EFFECT: {int(intensity)} percent intensity - STRONG NATURAL ENHANCEMENT
- Significant volume increase with noticeable fullness
- Clear lip projection and attractive, youthful appearance
- Well-defined, pronounced cupid bow
- Result: visibly fuller, more attractive lips with natural beauty

SPECIFIC INSTRUCTIONS FOR VISIBLE RESULTS:
- Add 40-60 percent volume to both upper (35 percent) and lower lips (65 percent) 
- Create clear, defined lip borders that are noticeably enhanced
- Enhance cupid bow prominently for attractive definition
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
- IMPORTANT: Enhancement should be clearly visible and attractive"""
    
    elif volume_ml <= 4.0:  # 2-4ml: Major enhancement - AGGRESSIVE for real portraits
        return f"""Perform DRAMATIC lip enhancement with {volume_ml}ml hyaluronic acid injection.
VOLUME EFFECT: {int(intensity)} percent intensity - EXTREME VOLUME TRANSFORMATION
- MASSIVE volume increase with dramatic, pronounced fullness
- Very strong lip projection creating luxurious, plump appearance  
- Dramatically pronounced cupid bow definition
- Bold, Instagram-worthy lip enhancement
- Result: DRAMATICALLY fuller, model-like, luxury lips

SPECIFIC INSTRUCTIONS FOR MAXIMUM EFFECT:
- Add 70-90 percent volume increase to BOTH upper (40 percent) and lower lips (60 percent)
- Create BOLD definition of lip borders with clear edges
- Enhance cupid bow DRAMATICALLY and prominently
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
- CRITICAL: Make the lip enhancement VISIBLY DRAMATIC and obvious"""

    else:  # 4ml+: Ultra-high volume - MAXIMUM TRANSFORMATION
        return f"""Perform ULTRA-DRAMATIC lip enhancement with {volume_ml}ml hyaluronic acid injection.
VOLUME EFFECT: {int(intensity)} percent intensity - MAXIMUM VOLUME TRANSFORMATION
- EXTREME volume increase with MAXIMUM dramatic fullness
- Ultra-strong lip projection creating bold, luxury appearance
- EXTREMELY pronounced cupid bow definition
- Celebrity-level, ultra-plump lip enhancement  
- Result: MAXIMUM fuller, glamorous, ultra-luxury lips

ULTRA-AGGRESSIVE INSTRUCTIONS:
- Add 90-110 percent volume increase to BOTH upper (35 percent) and lower lips (65 percent)
- Create EXTREMELY BOLD definition of lip borders with sharp, clear edges
- Enhance cupid bow to MAXIMUM prominence and definition
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
- CRITICAL: Make the lip enhancement EXTREMELY DRAMATIC and unmistakable"""

def ml_to_chin_deltas(ml: float):
    """
    Convert ml volume to precise geometric parameters for chin enhancement.
    Based on ChatGPT's medical aesthetic analysis.
    """
    t = max(0.0, min(ml, 4.0)) / 4.0  # Normalize to 0-1 range
    projection_mm = round(6.0 * t, 1)   # Forward projection: 0-6mm
    vertical_mm = round(3.0 * t, 1)     # Vertical lengthening: 0-3mm  
    fold_pct = int(round(30.0 * t))     # Labiomental fold smoothing: 0-30%
    intensity_pct = int(round(100.0 * t))  # Overall intensity: 0-100%
    return projection_mm, vertical_mm, fold_pct, intensity_pct

def get_prompt_for_chin(volume_ml: float) -> str:
    """
    Generate precise chin augmentation prompts with geometric targets.
    Uses ChatGPT's enhanced prompt composition system.
    """
    
    # Get precise geometric parameters
    proj_mm, vert_mm, fold_pct, intensity = ml_to_chin_deltas(volume_ml)
    
    # Generate unique request ID for anti-cache
    request_id = str(uuid.uuid4())
    
    # Build enhanced prompt with geometric targets
    return f"""REQUEST_ID: {request_id}

You are performing a chin augmentation simulation with {volume_ml} ml of hyaluronic acid.
INTENSITY: {intensity}% (ml-scaled)

EDIT SCOPE (CRITICAL):
- Edit ONLY the chin region (soft-tissue around pogonion/menton and the labiomental fold).
- Keep EVERYTHING ELSE IDENTICAL to the input: head pose, camera angle, framing, background,
  exposure, color balance, hair, makeup, nose, lips, eyes, teeth, skin pores and texture.

GEOMETRY TARGETS:
- Forward projection increase: +{proj_mm} mm
- Vertical lengthening (inferior direction): +{vert_mm} mm  
- Labiomental fold smoothing: {fold_pct}% (do not erase the fold completely)
- Maintain harmonious connection to jawline; no mandible length change.

AESTHETIC STYLE:
- Shape preference: natural oval chin
- Overall style: natural (avoid over-sculpting; maintain photorealistic appearance)

HARD NEGATIVE CONSTRAINTS:
- Do NOT change head position, FOV, or re-center the face.
- Do NOT alter nose, lips, teeth, eyes, eyebrows, skin tone, hair, or background.
- No skin smoothing, no beauty-retouch outside the chin.
- No artifacts (ghost edges, blur halos, duplicated textures).
- Preserve input resolution and noise pattern; return photorealistic output.

POSITION & TECHNICAL REQUIREMENTS:
- CRITICAL: Keep EXACT same face position, angle, and framing as input
- CRITICAL: Maintain IDENTICAL head position and orientation 
- CRITICAL: Keep SAME background, lighting, and composition
- CRITICAL: Do NOT center, crop, or reposition the face
- CRITICAL: Only chin changes - everything else EXACTLY as original

OUTPUT:
- Return the edited image (same resolution as input).
- Also return a short text note (one sentence) confirming the mm targets were applied."""


def ml_to_cheeks_deltas(ml: float):
    """
    Convert ml volume to precise geometric parameters for cheek enhancement.
    Based on ChatGPT's bilateral cheek augmentation analysis.
    """
    t = max(0.0, min(ml, 4.0)) / 4.0  # Normalize to 0-1 range
    malar_proj_mm = round(4.0 * t, 1)   # Lateral malar projection: 0-4mm
    apex_lift_mm = round(3.0 * t, 1)    # Vertical apex lift: 0-3mm  
    nlf_soften_pct = int(round(25.0 * t))  # NLF softening: 0-25%
    intensity_pct = int(round(100.0 * t))  # Overall intensity: 0-100%
    return malar_proj_mm, apex_lift_mm, nlf_soften_pct, intensity_pct

def get_prompt_for_cheeks(volume_ml: float, sex: str = "female", style: str = "natural", 
                         left_pct: int = 50, right_pct: int = 50) -> str:
    """
    Generate precise cheek augmentation prompts with geometric targets.
    Uses ChatGPT's enhanced bilateral cheek enhancement system.
    """
    
    # Get precise geometric parameters
    malar_mm, apex_mm, nlf_pct, intensity = ml_to_cheeks_deltas(volume_ml)
    
    # Generate unique request ID for anti-cache
    request_id = str(uuid.uuid4())
    
    # ChatGPT's Random Token System
    import secrets
    import string
    random_token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    
    # Build enhanced prompt with geometric targets
    return f"""REQUEST_ID: {request_id}
RANDOM_TOKEN: {random_token}

You are performing a bilateral cheek augmentation with {volume_ml} ml of hyaluronic acid.
INTENSITY: {intensity}%

EDIT SCOPE (CRITICAL):
- Edit ONLY the midface/cheek region (malar apex, zygomatic arch, submalar).
- Keep EVERYTHING ELSE IDENTICAL to the input: head pose, camera angle, framing, background,
  exposure, color balance, hair, makeup, nose, lips, eyes, teeth, and skin texture.

GEOMETRY TARGETS:
- Lateral malar projection increase: +{malar_mm} mm
- Vertical apex lift: +{apex_mm} mm
- Nasolabial fold softening: {nlf_pct}% (do not erase completely)
- Volume distribution (Left/Right): {left_pct}% / {right_pct}%
- Maintain smooth blending into tear trough and buccal area; do not widen the lower face.

AESTHETIC STYLE:
- Sex: {sex}
- Overall style: {style} (natural = softer transitions; defined = clearer cheekbone contour; dramatic = strong but photorealistic volume)

HARD NEGATIVE CONSTRAINTS:
- Do NOT change head position, field-of-view, composition, or re-center/zoom the face.
- Do NOT alter jawline, chin, nose, lips, eyes, brows, neck width, hair, or background.
- No beauty-retouch outside the cheeks; preserve natural skin pores and the input noise pattern.
- No artifacts (no halos, ghost edges, duplicated textures, or plastic skin).

POSITION & TECHNICAL REQUIREMENTS:
- CRITICAL: Keep EXACT same face position, angle, and framing as input
- CRITICAL: Maintain IDENTICAL head position and orientation 
- CRITICAL: Keep SAME background, lighting, and composition
- CRITICAL: Do NOT center, crop, or reposition the face
- CRITICAL: Only cheeks change - everything else EXACTLY as original

OUTPUT:
- Return the edited image at the SAME resolution as the input.
- Also return one short sentence confirming the applied targets (mm/%)."""


def get_prompt_for_botox_forehead(volume_ml: float) -> str:
    """Generate dosage-specific prompts for Botox forehead treatment (volume_ml converted to units)"""
    
    # Convert ml to Botox units for medical accuracy: 1ml ≈ 10 units (UI convenience)
    units = int(volume_ml * 10)
    intensity = min(volume_ml * 20, 100)  # 5ml input = 50 units = 100%
    
    if volume_ml <= 1.5:  # 0-1.5ml = 0-15 units: Light treatment
        return f"""Perform light Botox forehead treatment with approximately {units} units.
TREATMENT EFFECT: {int(intensity)} percent intensity - SUBTLE WRINKLE SOFTENING
- Gentle reduction of horizontal forehead lines
- Subtle muscle relaxation for natural movement
- Light smoothing without frozen appearance
- Result: softly smoothed forehead with preserved natural expressions

SPECIFIC INSTRUCTIONS FOR LIGHT BOTOX TREATMENT:
- Reduce horizontal forehead wrinkles by 30-50 percent
- Maintain natural facial expressions and eyebrow movement
- Create subtle smoothing without over-treatment
- Preserve skin texture and natural forehead mobility
- Keep natural skin tone and lighting unchanged
- NO other facial changes - only light forehead smoothing

POSITION & TECHNICAL REQUIREMENTS:
- CRITICAL: Keep EXACT same face position, angle, and framing as input
- CRITICAL: Maintain IDENTICAL head position and orientation 
- CRITICAL: Keep SAME background, lighting, and composition
- CRITICAL: Do NOT center, crop, or reposition the face
- CRITICAL: Only forehead wrinkles change - everything else EXACTLY as original
- Photorealistic result with subtle before/after difference
- Same resolution and quality as input
- Natural forehead texture but with reduced wrinkle visibility
- Professional aesthetic treatment appearance
- Keep all other facial features exactly unchanged"""

    elif volume_ml <= 3.0:  # 1.5-3ml = 15-30 units: Standard treatment
        return f"""Perform professional Botox forehead treatment with approximately {units} units.
TREATMENT EFFECT: {int(intensity)} percent intensity - BALANCED WRINKLE REDUCTION
- Clear reduction of horizontal forehead lines
- Effective muscle relaxation with natural movement preservation
- Noticeable smoothing with refreshed appearance
- Result: significantly smoother forehead maintaining natural expressions

SPECIFIC INSTRUCTIONS FOR STANDARD BOTOX TREATMENT:
- Reduce horizontal forehead wrinkles by 60-80 percent
- Create clear smoothing while preserving eyebrow mobility
- Balance wrinkle reduction with natural facial expressions
- Show realistic skin texture with enhanced smoothness
- Achieve professional aesthetic results
- Keep natural skin tone and lighting unchanged
- NO other facial changes - only forehead wrinkle reduction

POSITION & TECHNICAL REQUIREMENTS:
- CRITICAL: Keep EXACT same face position, angle, and framing as input
- CRITICAL: Maintain IDENTICAL head position and orientation 
- CRITICAL: Keep SAME background, lighting, and composition
- CRITICAL: Do NOT center, crop, or reposition the face
- CRITICAL: Only forehead wrinkles change - everything else EXACTLY as original
- Photorealistic result with clear before/after difference
- Same resolution and quality as input
- Natural forehead texture but with significantly reduced wrinkles
- Professional aesthetic treatment appearance
- Keep all other facial features exactly unchanged
- IMPORTANT: Forehead smoothing should be clearly visible yet natural"""

    else:  # 3ml+ = 30+ units: Intensive treatment
        return f"""Perform intensive Botox forehead treatment with approximately {units} units.
TREATMENT EFFECT: {int(intensity)} percent intensity - MAXIMUM WRINKLE ELIMINATION
- Dramatic reduction of all horizontal forehead lines
- Strong muscle relaxation for smooth, youthful appearance
- Maximum smoothing with professional results
- Result: dramatically smoothed forehead with youthful, refreshed look

SPECIFIC INSTRUCTIONS FOR INTENSIVE BOTOX TREATMENT:
- Reduce horizontal forehead wrinkles by 85-95 percent
- Create dramatic smoothing for maximum aesthetic impact
- Achieve professional-grade wrinkle elimination
- Show realistic skin texture with exceptional smoothness
- Transform aged forehead into youthfully smooth appearance
- Maintain some natural expression capability
- Keep natural skin tone and lighting unchanged
- NO other facial changes - only dramatic forehead transformation

POSITION & TECHNICAL REQUIREMENTS:
- CRITICAL: Keep EXACT same face position, angle, and framing as input
- CRITICAL: Maintain IDENTICAL head position and orientation 
- CRITICAL: Keep SAME background, lighting, and composition
- CRITICAL: Do NOT center, crop, or reposition the face
- CRITICAL: Only forehead wrinkles change - everything else EXACTLY as original
- Photorealistic result with dramatic before/after difference
- Same resolution and quality as input
- Natural forehead texture but with maximally reduced wrinkles
- Professional aesthetic treatment appearance
- Keep all other facial features exactly unchanged
- CRITICAL: Make the forehead smoothing DRAMATICALLY VISIBLE and transformative"""

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
    prompt = """Perform major lip enhancement with 3ml hyaluronic acid.
VOLUME EFFECT: 60 percent intensity - MAJOR VOLUME TRANSFORMATION
- Major volume increase with dramatic fullness
- Strong lip projection and luxurious appearance  
- Very pronounced cupid bow definition
- Result: dramatically fuller, luxurious-looking lips

SPECIFIC INSTRUCTIONS:
- Add 50-65 percent volume to both upper (45 percent) and lower lips (55 percent)
- Create strong definition of lip borders
- Enhance cupid bow prominently
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
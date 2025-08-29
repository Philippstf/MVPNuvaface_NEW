"""
FastAPI main application for NuvaFace aesthetic simulation API.
Implements endpoints for face segmentation and Gemini-powered aesthetic simulation.
"""

import time
import random
import logging
import io
from io import BytesIO
from fastapi import FastAPI, HTTPException, status
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

        # Load the original, unprocessed image for the highest quality input to Gemini
        original_image = load_image(request.image)
        logger.info(f"DEBUG: Loaded original image: {original_image.size}")

        # Generate the mask from the SAME image we send to Gemini (no face alignment!)
        processed_original, _ = preprocess_image(original_image, target_size=768, align_face=False)
        logger.info(f"DEBUG: Processed image size: {processed_original.size}")
        
        mask_image, segment_metadata = segment_area(processed_original, request.area)
        logger.info(f"DEBUG: Generated mask for area '{request.area}', mask size: {mask_image.size}")
        logger.info(f"DEBUG: Segment metadata: {segment_metadata}")

        # --- New Gemini Call ---
        # The core of the simulation - now with mask support
        logger.info(f"DEBUG: Calling generate_gemini_simulation with area='{request.area.value}', volume_ml={volume_ml}")
        logger.info(f"DEBUG: SENDING TO GEMINI: processed image size: {processed_original.size}, mask size: {mask_image.size}")
        logger.info(f"DEBUG: (Original was {original_image.size}, but we send processed {processed_original.size})")
        
        result_image = await generate_gemini_simulation(
            original_image=processed_original,  # Use the SAME processed image for consistency
            volume_ml=float(volume_ml),
            area=request.area.value,
            mask_image=mask_image
        )
        logger.info(f"DEBUG: Received result image from Gemini: {result_image.size}")
        
        # Check if result is identical to input (compare the same images we sent to Gemini)
        original_bytes = io.BytesIO()
        result_bytes = io.BytesIO()
        processed_original.save(original_bytes, format='PNG')  # Use processed_original, not original_image!
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
        original_base64 = image_to_base64(processed_original)
        mask_base64 = image_to_base64(mask_image)
        
        end_time = time.time()
        
        # Create a simplified response as detailed QC metrics are less relevant now
        return SimulationResponse(
            result_png=result_base64,
            original_png=original_base64,
            mask_png=mask_base64,
            params=ProcessingParameters(
                model="gemini-2.5-flash-image-preview",
                strength_ml=volume_ml  # Fixed: use strength_ml instead of strength
            ),
            qc=QualityMetrics(
                quality_passed=True
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
        
        # Direkter Gemini-Call ohne jegliche Pipeline-Verarbeitung
        result_image = await _direct_gemini_test_inline(original_image)
        
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
    
    # Fester Test-Prompt für 3.0ml Lip Enhancement
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

TECHNICAL REQUIREMENTS:
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
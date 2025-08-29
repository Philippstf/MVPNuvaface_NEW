# engine/test_gemini.py
"""
Direkter Gemini Test - ohne Pipeline-Komplexität
Upload -> Direkter Gemini Call mit festem 3.0ml Lip Enhancement
"""
import os
import sys
from pathlib import Path
from PIL import Image
from io import BytesIO
import base64

# Google Gemini imports
try:
    from google import genai
    from google.genai import types
    print("✅ Using google-genai SDK", file=sys.stderr)
except ImportError:
    print("❌ ERROR: google-genai package not found", file=sys.stderr)
    raise

async def direct_gemini_test(input_image: Image.Image) -> Image.Image:
    """
    Direkter Gemini-Call ohne Pipeline-Verarbeitung
    Testprompt: 3.0ml Lip Enhancement
    """
    
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

    print(f"🔍 DEBUG: Using test prompt for 3.0ml lips", file=sys.stderr)
    print(f"🔍 DEBUG: Input image size: {input_image.size}", file=sys.stderr)
    
    # Bild in JPEG konvertieren (für bessere Kompatibilität)
    if input_image.mode != 'RGB':
        input_image = input_image.convert('RGB')
    
    # Bild zu Bytes
    img_buffer = BytesIO()
    input_image.save(img_buffer, format='JPEG', quality=95)
    img_bytes = img_buffer.getvalue()
    
    try:
        print(f"🔍 DEBUG: Calling Gemini 2.5 Flash Image directly...", file=sys.stderr)
        
        # Content für multimodalen Input
        content = types.Content(
            parts=[
                types.Part.from_text(prompt),
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
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
        
        print(f"✅ Gemini call successful!", file=sys.stderr)
        
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
            print("🔍 DEBUG: Got RAW BYTES from Gemini - using directly! ✅", file=sys.stderr)
            image_bytes = image_data
        elif isinstance(image_data, str):
            print("🔍 DEBUG: Got Base64 string - decoding...", file=sys.stderr)
            image_bytes = base64.b64decode(image_data)
        else:
            raise Exception(f"Unexpected image data type: {type(image_data)}")
        
        # Bytes zu PIL Image
        result_image = Image.open(BytesIO(image_bytes))
        
        print(f"🔍 DEBUG: Result image size: {result_image.size}", file=sys.stderr)
        print(f"✅ Direct Gemini test completed successfully!", file=sys.stderr)
        
        return result_image
        
    except Exception as e:
        print(f"❌ ERROR: Direct Gemini call failed: {e}", file=sys.stderr)
        raise Exception(f"Direct Gemini test failed: {e}")
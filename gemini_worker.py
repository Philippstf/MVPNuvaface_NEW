# gemini_worker_simplified.py
"""
VEREINFACHTER Gemini Worker für NuvaFace
Direkter Image-to-Image Workflow ohne Komplexität
"""
import os
import sys
import argparse
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
from io import BytesIO
import base64

# Force UTF-8 encoding for Windows
if sys.platform.startswith('win'):
    import codecs
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')

# Using the new google-genai package
try:
    from google import genai
    from google.genai import types
    print("✅ Using google-genai SDK", file=sys.stderr)
except ImportError:
    print("❌ ERROR: google-genai package not found. Install with: pip install google-genai", file=sys.stderr)
    sys.exit(1)

# --- PROMPT SYSTEM (UNVERÄNDERT) ---
def get_prompt_for_lips(volume_ml: float) -> str:
    """Generate volume-specific prompts with consistent progression from 0-5ml"""
    
    # Calculate intensity percentage (0-100%) based on volume
    intensity = min(volume_ml * 20, 100)  # 5ml = 100%
    
    if volume_ml <= 0.5:  # 0-0.5ml: Minimal hydration and tightening
        return f"""Perform minimal lip hydration treatment with {volume_ml}ml hyaluronic acid.

VOLUME EFFECT: {intensity:.0f}% intensity - MINIMAL CHANGE ONLY
- Effect should be BARELY VISIBLE to naked eye
- Primary goal: slight skin tightening and hydration
- NO volume increase, only subtle texture improvement
- Result: lips look slightly more moisturized and defined

SPECIFIC INSTRUCTIONS:
- Minimal skin tightening effect around lip edges
- Slight definition of natural lip border (very subtle)
- NO volume addition to lip body
- Preserve exact original lip size and shape
- Effect should be like professional lip care, not enhancement

TECHNICAL REQUIREMENTS:
- CRITICAL: Preserve exact original lip color - no changes whatsoever
- AVOID: Any visible volume increase or shape change
- AVOID: Lip borders, outlines, or color transitions  
- Ensure natural skin texture and lighting"""

    elif volume_ml <= 1.0:  # 0.5-1ml: Light tightening + minimal volume
        return f"""Perform light lip enhancement with {volume_ml}ml hyaluronic acid.

VOLUME EFFECT: {intensity:.0f}% intensity - SUBTLE TIGHTENING + MINIMAL VOLUME
- Visible skin tightening effect
- Minimal volume increase (just noticeable)
- Better lip definition and border clarity
- Result: naturally refreshed, slightly fuller lips

SPECIFIC INSTRUCTIONS:
- Clear tightening effect on lip skin
- Add 10-15% volume to both upper and lower lips
- Enhance natural cupid's bow definition
- Improve vermillion border clarity
- Lips should look refreshed and naturally enhanced

TECHNICAL REQUIREMENTS:
- CRITICAL: Preserve exact original lip color
- Show clear but subtle improvement over original
- AVOID: Lip borders, outlines, color transitions
- Maintain natural proportions"""

    elif volume_ml <= 1.5:  # 1-1.5ml: Clear volume increase
        return f"""Perform moderate lip enhancement with {volume_ml}ml hyaluronic acid.

VOLUME EFFECT: {intensity:.0f}% intensity - NOTICEABLE VOLUME INCREASE
- Clear, visible volume addition
- Enhanced lip projection and fullness
- Well-defined cupid's bow
- Result: attractively fuller, naturally enhanced lips

SPECIFIC INSTRUCTIONS:
- Add 20-30% volume to both upper (40%) and lower lips (60%)
- Create noticeable cupid's bow enhancement
- Increase lip projection and forward fullness
- Enhance vermillion border definition
- Result should be clearly fuller than original

TECHNICAL REQUIREMENTS:
- CRITICAL: Preserve exact original lip color
- Show significant improvement that's clearly visible
- AVOID: Lip borders, outlines, color transitions
- Maintain facial harmony and natural proportions"""

    elif volume_ml <= 2.0:  # 1.5-2ml: Significant volume increase
        return f"""Perform significant lip enhancement with {volume_ml}ml hyaluronic acid.

VOLUME EFFECT: {intensity:.0f}% intensity - SIGNIFICANT FULLNESS INCREASE
- Substantial volume addition clearly visible
- Enhanced lip projection and attractive fullness
- Pronounced cupid's bow definition
- Result: notably fuller, more attractive lips

SPECIFIC INSTRUCTIONS:
- Add 35-45% volume to both upper (45%) and lower lips (55%)
- Create pronounced cupid's bow with clear peaks
- Significant increase in lip projection and fullness
- Enhanced vermillion borders with clear definition
- Result should show major improvement over original

TECHNICAL REQUIREMENTS:
- CRITICAL: Preserve exact original lip color
- Show dramatic but natural-looking enhancement
- AVOID: Lip borders, outlines, color transitions
- Maintain attractive facial proportions"""

    elif volume_ml <= 3.0:  # 2-3ml: Major enhancement
        return f"""Perform major lip enhancement with {volume_ml}ml hyaluronic acid.

VOLUME EFFECT: {intensity:.0f}% intensity - MAJOR VOLUME TRANSFORMATION
- Major volume increase with dramatic fullness
- Strong lip projection and luxurious appearance
- Very pronounced cupid's bow definition
- Result: dramatically fuller, luxurious-looking lips

SPECIFIC INSTRUCTIONS:
- Add 50-65% volume to both upper (45%) and lower lips (55%)
- Create very pronounced cupid's bow with sharp definition
- Major increase in lip projection and overall fullness
- Strong vermillion border enhancement
- Add subtle lip eversion for natural fullness effect

TECHNICAL REQUIREMENTS:
- CRITICAL: Preserve exact original lip color
- Show major transformation while maintaining naturalness
- AVOID: Lip borders, outlines, color transitions
- Balance enhancement with facial harmony"""

    elif volume_ml <= 4.0:  # 3-4ml: Dramatic enhancement
        return f"""Perform dramatic lip enhancement with {volume_ml}ml hyaluronic acid.

VOLUME EFFECT: {intensity:.0f}% intensity - DRAMATIC TRANSFORMATION
- Dramatic volume increase with luxury fullness
- Maximum projection and premium appearance
- Extremely pronounced cupid's bow definition
- Result: dramatically enhanced, premium-looking lips

SPECIFIC INSTRUCTIONS:
- Add 70-85% volume to both upper (45%) and lower lips (55%)
- Create extremely pronounced cupid's bow with sharp peaks
- Maximum safe projection and overall fullness
- Strong vermillion border enhancement with clear definition
- Add noticeable lip eversion for maximum natural effect

TECHNICAL REQUIREMENTS:
- CRITICAL: Preserve exact original lip color
- Show premium transformation with expert-level results
- AVOID: Lip borders, outlines, color transitions
- Maintain facial balance despite dramatic change"""

    else:  # 4-5ml: Maximum enhancement
        return f"""Perform maximum lip enhancement with {volume_ml}ml hyaluronic acid.

VOLUME EFFECT: {intensity:.0f}% intensity - MAXIMUM TRANSFORMATION
- Maximum safe volume increase
- Ultimate lip projection and fullness
- Extremely bold cupid's bow definition  
- Result: maximum enhancement, bold luxury appearance

SPECIFIC INSTRUCTIONS:
- Add 85-100% maximum volume to both upper (45%) and lower lips (55%)
- Create maximum cupid's bow definition with dramatic peaks
- Ultimate projection and overall lip fullness
- Maximum vermillion border enhancement
- Add significant lip eversion for bold natural effect
- Slight philtral column enhancement for balance

TECHNICAL REQUIREMENTS:
- CRITICAL: Preserve exact original lip color
- Show maximum transformation with expert precision
- AVOID: Lip borders, outlines, color transitions
- Maintain facial harmony despite bold enhancement"""

def get_prompt_for_cheeks(volume_ml: float) -> str:
    """Generate specific prompts for cheek filler treatments"""
    if volume_ml <= 1.0:
        return f"Subtle cheek contouring using {volume_ml}ml hyaluronic acid filler. Add minimal volume to the mid-cheek area, enhance natural cheekbone projection slightly, create subtle lifting effect, preserve natural facial contours. Maintain original skin texture and lighting, no artificial shine or over-smoothing, keep natural facial proportions."
    elif volume_ml <= 3.0:
        return f"Moderate cheek enhancement using {volume_ml}ml hyaluronic acid filler. Add moderate volume to mid-cheek and cheekbone area, create visible but natural cheek projection, enhance facial contours with subtle lifting, improve cheekbone definition. Maintain original skin texture and lighting, create balanced, proportional enhancement, avoid over-smoothing or artificial appearance."
    else:
        return f"Significant cheek enhancement using {volume_ml}ml hyaluronic acid filler. Add substantial volume to cheekbone and mid-cheek area, create pronounced cheek projection and definition, significant facial contouring and lifting effect, enhance overall facial structure. Maintain original skin texture and lighting, create dramatic but natural-looking enhancement, balance enhancement with overall facial harmony."

def get_prompt_for_chin(volume_ml: float) -> str:
    """Generate specific prompts for chin filler treatments"""
    if volume_ml <= 1.0:
        return f"Subtle chin projection enhancement using {volume_ml}ml hyaluronic acid filler. Add minimal forward projection to chin, create subtle rounding and definition, enhance jawline slightly, maintain natural chin proportions. Preserve original skin texture, keep natural facial balance, avoid artificial or overdone appearance."
    elif volume_ml <= 2.5:
        return f"Moderate chin enhancement using {volume_ml}ml hyaluronic acid filler. Add moderate forward projection to chin, create noticeable but natural chin definition, enhance jawline and lower face balance, improve overall facial profile. Maintain original skin texture and lighting, create balanced facial enhancement, keep natural proportions."
    else:
        return f"Significant chin enhancement using {volume_ml}ml hyaluronic acid filler. Add substantial forward projection to chin, create pronounced chin definition and structure, dramatically improve jawline and facial profile, enhance overall lower face architecture. Maintain original skin texture, create dramatic but balanced enhancement, preserve facial harmony."

def get_prompt_for_forehead(volume_ml: float) -> str:
    """Generate prompts for forehead/botox treatments"""
    return "Reduce horizontal forehead wrinkles and lines. Smooth out horizontal forehead lines, reduce expression wrinkles, maintain natural forehead texture, keep natural facial expressions. Preserve skin pores and natural texture, maintain original lighting, avoid over-smoothing or artificial appearance, keep natural skin variations."

# --- VEREINFACHTER GEMINI CLIENT ---
def create_gemini_client():
    """Create simplified Gemini client"""
    api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        raise ValueError("❌ No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")
    
    print(f"✅ API key loaded (length: {len(api_key)})", file=sys.stderr)
    
    # Simplified client - let Gemini handle the complexity
    return genai.Client(api_key=api_key)

# --- EINFACHE BILDGENERIERUNG ---
def generate_image_edit(client, prompt, input_image):
    """Vereinfachte Bildbearbeitung mit Gemini 2.5 Flash Image"""
    
    # Bild für Gemini vorbereiten (kleinere Größe für bessere Performance)
    if input_image.size[0] > 768 or input_image.size[1] > 768:
        # Proportionales Resize
        input_image.thumbnail((768, 768), Image.Resampling.LANCZOS)
        print(f"📏 Image resized to {input_image.size}", file=sys.stderr)
    
    # Bild zu bytes konvertieren
    img_buffer = BytesIO()
    input_image.save(img_buffer, format='JPEG', quality=90)
    img_bytes = img_buffer.getvalue()
    
    # Direkte Parts für Gemini
    image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
    
    # Expliziter Prompt für Bildbearbeitung
    edit_prompt = f"""{prompt}

IMPORTANT: Please edit and return the modified image showing the aesthetic treatment result. 
The output must be a visual image, not a text description."""
    
    print(f"🎯 Prompt length: {len(edit_prompt)} chars", file=sys.stderr)
    print(f"📸 Image size: {len(img_bytes)} bytes", file=sys.stderr)
    
    # Modelle zum Probieren (vom neuesten zum ältesten)
    models_to_try = [
        "gemini-2.5-flash-image-preview",  # Hauptmodell für Bildbearbeitung
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro-latest",
        "gemini-1.5-flash-latest"
    ]
    
    for model_name in models_to_try:
        try:
            print(f"🚀 Trying {model_name}...", file=sys.stderr)
            
            # Einfache Konfiguration
            config = types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.8,
                max_output_tokens=8192
                # Lass Gemini automatisch entscheiden: TEXT oder IMAGE output
            )
            
            # API-Aufruf
            response = client.models.generate_content(
                model=model_name,
                contents=[edit_prompt, image_part],
                config=config
            )
            
            # Response verarbeiten
            if response and response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        # Schaue nach Bilddaten
                        if hasattr(part, 'inline_data') and part.inline_data and part.inline_data.data:
                            print(f"✅ SUCCESS with {model_name}!", file=sys.stderr)
                            
                            # 🔍 DEBUG: Analysiere Datenformat
                            data = part.inline_data.data
                            print(f"🔍 DEBUG: Data type = {type(data)}", file=sys.stderr)
                            print(f"🔍 DEBUG: Data length = {len(data)}", file=sys.stderr)
                            
                            if isinstance(data, str):
                                print(f"🔍 DEBUG: First 50 chars = {data[:50]}", file=sys.stderr)
                                print(f"🔍 DEBUG: Last 50 chars = {data[-50:]}", file=sys.stderr)
                                
                                # Test if base64
                                import re
                                if re.match(r'^[A-Za-z0-9+/]*={0,2}$', data[:100]):
                                    print("🔍 DEBUG: Looks like Base64! ✅", file=sys.stderr)
                                else:
                                    print("🔍 DEBUG: Does NOT look like Base64! ❌", file=sys.stderr)
                            
                            elif isinstance(data, bytes):
                                print(f"🔍 DEBUG: First 20 bytes (hex) = {data[:20].hex()}", file=sys.stderr)
                                
                                # Check image signatures
                                if data.startswith(b'\xff\xd8\xff'):
                                    print("🔍 DEBUG: Raw JPEG signature detected! ✅", file=sys.stderr)
                                elif data.startswith(b'\x89PNG\r\n\x1a\n'):
                                    print("🔍 DEBUG: Raw PNG signature detected! ✅", file=sys.stderr)
                                else:
                                    print("🔍 DEBUG: Unknown raw format ❓", file=sys.stderr)
                            
                            return part.inline_data.data, model_name
            
            print(f"⚠️ No image data from {model_name}, trying next...", file=sys.stderr)
            
        except Exception as e:
            print(f"❌ {model_name} failed: {str(e)[:100]}...", file=sys.stderr)
            continue
    
    # Alle Modelle fehlgeschlagen
    raise Exception("💥 All Gemini models failed to generate image")

def main():
    """Hauptfunktion - vereinfacht"""
    print("🚀 SIMPLIFIED Gemini Worker Starting", file=sys.stderr)
    
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Simplified Gemini Worker for NuvaFace')
    parser.add_argument('--input', required=True, help='Input image path')
    parser.add_argument('--output', required=True, help='Output image path') 
    parser.add_argument('--volume', type=float, required=True, help='Filler volume in ml')
    parser.add_argument('--area', required=True, help='Treatment area')
    parser.add_argument('--mask', help='Mask image path (optional - currently not used)')
    
    args = parser.parse_args()
    
    try:
        # Input laden
        if not os.path.exists(args.input):
            raise FileNotFoundError(f"❌ Input not found: {args.input}")
            
        input_image = Image.open(args.input)
        if input_image.mode != 'RGB':
            input_image = input_image.convert('RGB')
        
        print(f"📷 Loaded image: {input_image.size}, mode: {input_image.mode}", file=sys.stderr)
        
        # Prompt generieren (UNVERÄNDERT)
        print(f"📝 Generating prompt for {args.area} with {args.volume}ml", file=sys.stderr)
        
        if args.area.lower() == 'lips':
            prompt = get_prompt_for_lips(args.volume)
        elif args.area.lower() == 'cheeks':
            prompt = get_prompt_for_cheeks(args.volume)
        elif args.area.lower() == 'chin':
            prompt = get_prompt_for_chin(args.volume)
        elif args.area.lower() == 'forehead':
            prompt = get_prompt_for_forehead(args.volume)
        else:
            raise ValueError(f"❌ Unsupported area: {args.area}")
        
        # Gemini Client erstellen
        client = create_gemini_client()
        
        # Bildbearbeitung
        print("🎨 Starting image edit with Gemini...", file=sys.stderr)
        result_base64, used_model = generate_image_edit(client, prompt, input_image)
        
        # Bild-Daten verarbeiten (Gemini gibt RAW BYTES zurück, nicht Base64!)
        print(f"🔍 DEBUG: Processing image data, type = {type(result_base64)}", file=sys.stderr)
        
        if isinstance(result_base64, bytes):
            # Gemini gibt RAW BYTES zurück - direkt verwenden!
            print("🔍 DEBUG: Got RAW BYTES from Gemini - using directly! ✅", file=sys.stderr)
            image_bytes = result_base64
        elif isinstance(result_base64, str):
            # Falls es doch Base64 ist
            print("🔍 DEBUG: Got Base64 string - decoding...", file=sys.stderr)
            image_bytes = base64.b64decode(result_base64)
        else:
            raise ValueError(f"Unexpected data type: {type(result_base64)}")
        
        print(f"🔍 DEBUG: Final image bytes length = {len(image_bytes)}", file=sys.stderr)
        print(f"🔍 DEBUG: First 20 bytes (hex) = {image_bytes[:20].hex()}", file=sys.stderr)
        
        # Check image signature
        if image_bytes.startswith(b'\xff\xd8\xff'):
            print("🔍 DEBUG: Image has JPEG signature! ✅", file=sys.stderr)
        elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
            print("🔍 DEBUG: Image has PNG signature! ✅", file=sys.stderr)
        else:
            print("🔍 DEBUG: Unknown image format ❓", file=sys.stderr)
        
        try:
            result_image = Image.open(BytesIO(image_bytes))
            print(f"🔍 DEBUG: PIL Image.open() SUCCESS! Size: {result_image.size} ✅", file=sys.stderr)
        except Exception as pil_error:
            print(f"🔍 DEBUG: PIL Image.open() FAILED: {pil_error}", file=sys.stderr)
            raise
        
        # Zu RGB konvertieren falls nötig
        if result_image.mode != 'RGB':
            result_image = result_image.convert('RGB')
        
        # Speichern
        result_image.save(args.output, 'PNG')
        print(f"💾 Saved result: {args.output}", file=sys.stderr)
        
        # Für edit_gemini.py: Base64 Output auf stdout
        final_buffer = BytesIO()
        result_image.save(final_buffer, format='PNG')
        final_base64 = base64.b64encode(final_buffer.getvalue()).decode('utf-8')
        
        print("IMAGE_DATA_START:" + final_base64 + ":IMAGE_DATA_END")
        
        print(f"🔍 DEBUG: Final output base64 length = {len(final_base64)}", file=sys.stderr)
        
        print(f"✅ Success with {used_model}")
        
    except Exception as e:
        print(f"💥 FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
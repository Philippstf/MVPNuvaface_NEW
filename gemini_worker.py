# gemini_worker.py
"""
A dedicated, isolated worker script to call the Gemini API.
This script is intended to be called from a separate process to avoid
dependency conflicts between mediapipe and google-generativeai.
"""
import os
import sys
import argparse
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
from io import BytesIO

# Using the new google-genai package for Gemini 2.5 Flash Image
try:
    from google import genai
    print("Using google-genai SDK")
except ImportError:
    print("Error: google-genai package not found. Please install it with: pip install google-genai", file=sys.stderr)
    sys.exit(1)

# --- Advanced Prompt Templates based on area and volume ---
def get_prompt_for_lips(volume_ml: float) -> str:
    """Generate specific prompts for lip filler treatments"""
    
    if volume_ml <= 0.5:
        return """Perform a subtle lip hydration enhancement using {volume_ml}ml hyaluronic acid filler. 
        
SPECIFIC INSTRUCTIONS:
- Add minimal volume to BOTH upper and lower lips
- Slightly define the cupid's bow edge
- Enhance natural lip border definition
- Keep lips looking naturally hydrated, not enlarged
- Maintain original lip proportions exactly
- Result should look like well-moisturized, healthy lips
        
TECHNICAL REQUIREMENTS:
- Preserve all facial features except lips
- Maintain original lighting and skin texture
- No glossy or artificial appearance
- Keep lip color natural and unchanged"""

    elif volume_ml <= 1.5:
        return """Perform a conservative lip enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- Add modest volume to BOTH upper lip (40%) and lower lip (60%)
- Enhance the cupid's bow definition noticeably
- Create subtle lip border enhancement
- Upper lip should gain visible fullness, not just the lower lip
- Add gentle projection to the vermillion border
- Result should look like naturally full, attractive lips
        
TECHNICAL REQUIREMENTS:
- Preserve all facial features except lips
- Maintain original lighting and skin texture
- Create balanced, proportional enhancement
- No artificial shine or unrealistic texture"""

    elif volume_ml <= 2.5:
        return """Perform a moderate lip enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- Add significant volume to BOTH upper lip (45%) and lower lip (55%)
- Create pronounced cupid's bow definition with clear peaks
- Enhance both the upper and lower vermillion borders substantially
- Upper lip should show clear volume increase and better projection
- Lower lip should be noticeably fuller and more projected
- Create attractive, full lips that look naturally plump
- Add subtle eversion to the lip edges for natural fullness
        
TECHNICAL REQUIREMENTS:
- Preserve all facial features except lips
- Maintain original lighting and skin texture
- Create balanced, attractive enhancement
- Result should look like naturally very attractive lips"""

    elif volume_ml <= 4.0:
        return """Perform a significant lip enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- Add substantial volume to BOTH upper lip (45%) and lower lip (55%)
- Create very pronounced cupid's bow with sharp, defined peaks
- Significantly enhance both upper and lower vermillion borders
- Upper lip must show dramatic volume increase and strong projection
- Lower lip should be significantly fuller with enhanced projection
- Create luxurious, full lips with excellent definition
- Add noticeable eversion to create natural-looking fullness
- Enhance the philtral columns slightly for balance
        
TECHNICAL REQUIREMENTS:
- Preserve all facial features except lips
- Maintain original lighting and skin texture
- Create dramatic but balanced enhancement
- Result should look like expertly enhanced, luxurious lips"""

    else:  # 4.0ml+
        return """Perform a maximum lip enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- Add maximum safe volume to BOTH upper lip (45%) and lower lip (55%)
- Create extremely pronounced cupid's bow with sharp, dramatic peaks
- Dramatically enhance both upper and lower vermillion borders
- Upper lip must show maximum volume increase with strong projection
- Lower lip should be maximally full with significant projection
- Create bold, voluptuous lips with excellent definition
- Add significant eversion for maximum natural-looking fullness
- Enhance the philtral columns for facial balance
- Result should look like premium cosmetic enhancement
        
TECHNICAL REQUIREMENTS:
- Preserve all facial features except lips
- Maintain original lighting and skin texture
- Create maximum dramatic but still natural enhancement
- Result should look like high-end cosmetic procedure results"""

def get_prompt_for_chin(volume_ml: float) -> str:
    """Generate specific prompts for chin filler treatments (typical range: 2-5ml)"""
    
    if volume_ml <= 1.0:
        return """IMPORTANT: Focus ONLY on the CHIN area. Do NOT modify lips, cheeks, forehead, or any other facial features.

Perform a subtle chin enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- ONLY edit the chin area (the bottom part of the face below the lower lip)
- Add minimal forward projection to the chin tip area
- Slightly improve the chin-to-neck line definition  
- Create subtle forward projection of the mentolabial fold
- Enhance the chin's natural contour without changing facial balance
- ABSOLUTELY DO NOT touch the lips, nose, cheeks, or forehead
- Result should look like natural chin definition improvement
        
TECHNICAL REQUIREMENTS:
- Preserve ALL facial features except the chin area specifically
- DO NOT modify lips or mouth area at all
- Maintain original lighting and skin texture
- Keep jawline natural and proportional
- No artificial or overdone appearance"""

    elif volume_ml <= 2.5:
        return """IMPORTANT: Focus ONLY on the CHIN area. Do NOT modify lips, cheeks, forehead, or any other facial features.

Perform a moderate chin augmentation using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- ONLY edit the chin area (the bottom part of the face below the lower lip)
- Add noticeable forward projection to the chin
- Improve chin-to-neck angle and definition significantly
- Enhance the mentolabial fold and chin tip projection
- Create better facial profile balance and proportion
- Slightly widen the chin base for stability
- ABSOLUTELY DO NOT touch the lips, nose, cheeks, or forehead
- Result should show clear improvement in facial harmony
        
TECHNICAL REQUIREMENTS:
- Preserve ALL facial features except the chin area specifically
- DO NOT modify lips or mouth area at all
- Maintain original lighting and skin texture
- Create balanced, proportional enhancement
- Result should look naturally stronger and more defined"""

    elif volume_ml <= 4.0:
        return """IMPORTANT: Focus ONLY on the CHIN area. Do NOT modify lips, cheeks, forehead, or any other facial features.

Perform a significant chin augmentation using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- ONLY edit the chin area (the bottom part of the face below the lower lip)
- Add substantial forward projection to create strong chin presence
- Dramatically improve chin-to-neck angle and jawline definition
- Enhance both chin tip projection and lateral chin width
- Create pronounced improvement in facial profile and balance
- Add definition to the pre-jowl sulcus area
- ABSOLUTELY DO NOT touch the lips, nose, cheeks, or forehead
- Result should show dramatic improvement in chin strength and definition
        
TECHNICAL REQUIREMENTS:
- Preserve ALL facial features except the chin area specifically
- DO NOT modify lips or mouth area at all
- Maintain original lighting and skin texture
- Create strong, masculine/confident enhancement
- Result should look expertly augmented and balanced"""

    else:  # 4.0ml+
        return """IMPORTANT: Focus ONLY on the CHIN area. Do NOT modify lips, cheeks, forehead, or any other facial features.

Perform a maximum chin augmentation using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- ONLY edit the chin area (the bottom part of the face below the lower lip)
- Add maximum safe forward projection for dramatic chin enhancement
- Create strong, defined chin-to-neck angle and sharp jawline
- Substantially enhance chin tip projection and lateral width
- Add significant definition to pre-jowl area and jawline
- Create bold, confident facial profile transformation
- ABSOLUTELY DO NOT touch the lips, nose, cheeks, or forehead
- Result should show premium cosmetic enhancement results
        
TECHNICAL REQUIREMENTS:
- Preserve ALL facial features except the chin area specifically
- DO NOT modify lips or mouth area at all
- Maintain original lighting and skin texture
- Create maximum dramatic but natural enhancement
- Result should look like high-end cosmetic procedure"""

def get_prompt_for_cheeks(volume_ml: float) -> str:
    """Generate specific prompts for cheek filler treatments (typical range: 1-4ml per side)"""
    
    if volume_ml <= 1.0:
        return """IMPORTANT: Focus ONLY on the CHEEK area. Do NOT modify lips, chin, forehead, or any other facial features.

Perform a subtle cheek enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- ONLY edit the cheek area (the mid-face region with cheekbones)
- Add minimal volume to the mid-cheek area (malar region)
- Slightly enhance cheekbone definition and contour
- Create subtle lift to the cheek area without obvious volume
- Restore natural youthful cheek fullness
- ABSOLUTELY DO NOT touch the lips, chin, nose, or forehead
- Maintain natural facial proportions exactly
- Result should look like naturally healthy, rested cheeks
        
TECHNICAL REQUIREMENTS:
- Preserve ALL facial features except cheek area specifically
- DO NOT modify lips, chin, or mouth area at all
- Maintain original lighting and skin texture
- Keep enhancement very natural and subtle
- No artificial or overdone appearance"""

    elif volume_ml <= 2.5:
        return """IMPORTANT: Focus ONLY on the CHEEK area. Do NOT modify lips, chin, forehead, or any other facial features.

Perform a moderate cheek enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- ONLY edit the cheek area (the mid-face region with cheekbones)
- Add noticeable volume to both mid-cheek (malar) and higher cheekbone areas
- Enhance cheekbone definition and create attractive contour
- Lift the cheek area to create youthful fullness
- Improve the ogee curve (S-curve from temple to cheek)
- Create balanced, proportional enhancement to both sides
- ABSOLUTELY DO NOT touch the lips, chin, nose, or forehead
- Result should show clear cheek definition and attractive contour
        
TECHNICAL REQUIREMENTS:
- Preserve ALL facial features except cheek area specifically
- DO NOT modify lips, chin, or mouth area at all
- Maintain original lighting and skin texture
- Create balanced, attractive enhancement
- Result should look naturally full and well-contoured"""

    elif volume_ml <= 4.0:
        return """IMPORTANT: Focus ONLY on the CHEEK area. Do NOT modify lips, chin, forehead, or any other facial features.

Perform a significant cheek enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- ONLY edit the cheek area (the mid-face region with cheekbones)
- Add substantial volume to create pronounced cheekbone definition
- Enhance both malar prominence and lateral cheek projection
- Create dramatic lift and contour to the entire cheek area
- Improve facial width and create model-like cheekbone structure
- Add definition to the ogee curve for photogenic results
- ABSOLUTELY DO NOT touch the lips, chin, nose, or forehead
- Result should show luxurious, high-cheekbone appearance
        
TECHNICAL REQUIREMENTS:
- Preserve ALL facial features except cheek area specifically
- DO NOT modify lips, chin, or mouth area at all
- Maintain original lighting and skin texture
- Create dramatic but balanced enhancement
- Result should look like expert cosmetic enhancement"""

    else:  # 4.0ml+
        return """IMPORTANT: Focus ONLY on the CHEEK area. Do NOT modify lips, chin, forehead, or any other facial features.

Perform a maximum cheek enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- ONLY edit the cheek area (the mid-face region with cheekbones)
- Add maximum safe volume to create bold, sculpted cheekbones
- Dramatically enhance malar prominence and lateral projection
- Create striking cheekbone definition and facial contour
- Add significant width and structure to the mid-face
- Create premium, model-like facial architecture
- ABSOLUTELY DO NOT touch the lips, chin, nose, or forehead
- Result should show maximum cosmetic cheek enhancement
        
TECHNICAL REQUIREMENTS:
- Preserve ALL facial features except cheek area specifically
- DO NOT modify lips, chin, or mouth area at all
- Maintain original lighting and skin texture
- Create maximum dramatic but natural enhancement
- Result should look like high-end cosmetic procedure"""

def get_prompt_for_botox_forehead(units: float) -> str:
    """Generate specific prompts for Botox forehead treatments (typical range: 10-30 units)"""
    
    if units <= 10:
        return """IMPORTANT: Focus ONLY on the FOREHEAD area. Do NOT modify lips, chin, cheeks, or any other facial features.

Perform a subtle Botox treatment using {units} units for forehead wrinkles.
        
SPECIFIC INSTRUCTIONS:
- ONLY edit the forehead area (horizontal wrinkles above the eyebrows)
- Reduce horizontal forehead lines minimally while preserving natural movement
- Smooth only the deepest static wrinkles slightly
- Maintain natural eyebrow position and expression
- Keep forehead movement mostly intact
- ABSOLUTELY DO NOT touch the lips, cheeks, chin, or nose
- Result should look refreshed but completely natural
        
TECHNICAL REQUIREMENTS:
- Preserve ALL facial features except forehead wrinkles specifically
- DO NOT modify lips, cheeks, or chin area at all
- Maintain original lighting and skin texture
- Keep natural skin pores and texture visible
- No frozen or artificial appearance"""

    elif units <= 20:
        return """IMPORTANT: Focus ONLY on the FOREHEAD area. Do NOT modify lips, chin, cheeks, or any other facial features.

Perform a moderate Botox treatment using {units} units for forehead wrinkles.
        
SPECIFIC INSTRUCTIONS:
- ONLY edit the forehead area (horizontal wrinkles above the eyebrows)
- Significantly reduce horizontal forehead lines and wrinkles
- Smooth both dynamic and static wrinkles noticeably
- Slightly lift and relax the forehead area
- Reduce but don't eliminate natural forehead movement
- Create smoother, more youthful forehead appearance
- ABSOLUTELY DO NOT touch the lips, cheeks, chin, or nose
- Result should show clear wrinkle improvement with natural look
        
TECHNICAL REQUIREMENTS:
- Preserve ALL facial features except forehead wrinkles specifically
- DO NOT modify lips, cheeks, or chin area at all
- Maintain original lighting and skin texture
- Keep skin pores and natural texture intact
- Result should look naturally refreshed and smoother"""

    else:  # 20+ units
        return """IMPORTANT: Focus ONLY on the FOREHEAD area. Do NOT modify lips, chin, cheeks, or any other facial features.

Perform a comprehensive Botox treatment using {units} units for forehead wrinkles.
        
SPECIFIC INSTRUCTIONS:
- ONLY edit the forehead area (horizontal wrinkles above the eyebrows)
- Dramatically reduce all horizontal forehead lines and wrinkles
- Smooth both dynamic and static wrinkles completely
- Create very smooth, wrinkle-free forehead appearance
- Eliminate most visible forehead creases and lines
- ABSOLUTELY DO NOT touch the lips, cheeks, chin, or nose
- Result should show maximum wrinkle reduction while maintaining natural skin texture
        
TECHNICAL REQUIREMENTS:
- Preserve ALL facial features except forehead wrinkles specifically
- DO NOT modify lips, cheeks, or chin area at all
- Maintain original lighting and skin texture
- Keep natural skin pores and texture visible
- Result should look expertly treated but not frozen"""

def get_prompt_for_area(area: str, volume_ml: float) -> str:
    """Route to appropriate prompt function based on treatment area"""
    
    if area.lower() == "lips":
        return get_prompt_for_lips(volume_ml)
    elif area.lower() == "chin":
        return get_prompt_for_chin(volume_ml)
    elif area.lower() == "cheeks":
        return get_prompt_for_cheeks(volume_ml)
    elif area.lower() == "forehead":
        # For Botox, convert ml to units (rough conversion: 1ml ≈ 20-25 units)
        units = volume_ml * 22  # average conversion
        return get_prompt_for_botox_forehead(units).replace("{units}", str(int(units)))
    else:
        # Fallback to lips if unknown area
        return get_prompt_for_lips(volume_ml)

def run_gemini_process(input_path: str, output_path: str, volume_ml: float, area: str = "lips", mask_path: str = None):
    """
    Loads an image, calls the Gemini 2.5 Flash Image API, and saves the result.
    Following the official pattern from promptangemini.md
    """
    try:
        print(f"DEBUG: Worker started with parameters:")
        print(f"DEBUG: - input_path: {input_path}")
        print(f"DEBUG: - output_path: {output_path}")
        print(f"DEBUG: - volume_ml: {volume_ml}")
        print(f"DEBUG: - area: '{area}'")
        print(f"DEBUG: - mask_path: {mask_path}")
        
        # --- Configuration ---
        load_dotenv(Path(__file__).parent / '.env')
        gemini_api_key = os.getenv("GOOGLE_API_KEY")
        if not gemini_api_key:
            # Try GEMINI_API_KEY as fallback
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                raise ValueError("GOOGLE_API_KEY or GEMINI_API_KEY not found in .env file.")
        
        print(f"DEBUG: API key found: {gemini_api_key[:10]}...")
        
        # Initialize client with API key
        client = genai.Client(api_key=gemini_api_key)
        
        # --- Generate specific prompt based on area and volume ---
        print(f"DEBUG: Calling get_prompt_for_area with area='{area}', volume={volume_ml}")
        base_prompt = get_prompt_for_area(area, volume_ml).format(volume_ml=volume_ml)
        print(f"DEBUG: Generated base prompt (first 200 chars): {base_prompt[:200]}...")
        
        # Add mask instruction if mask is provided
        if mask_path and Path(mask_path).exists():
            print(f"DEBUG: Mask file exists at: {mask_path}")
            prompt = f"""{base_prompt}

IMPORTANT MASK INSTRUCTION:
A second image (mask) is provided showing EXACTLY which area to edit:
- WHITE areas in the mask = areas to modify
- BLACK areas in the mask = areas to keep unchanged
- ONLY edit the white regions of the mask
- Leave all black regions completely untouched"""
            print(f"DEBUG: Added mask instructions to prompt")
        else:
            print(f"DEBUG: No mask file found or provided")
            prompt = base_prompt
        
        # --- Image Loading ---
        if not Path(input_path).exists():
            raise FileNotFoundError(f"Input image not found at: {input_path}")
        
        # Load image using PIL
        img = Image.open(input_path)
        print(f"DEBUG: Loaded input image: mode={img.mode}, size={img.size}")
        
        # Load mask if provided
        contents = [prompt, img]
        if mask_path and Path(mask_path).exists():
            mask_img = Image.open(mask_path)
            contents.append(mask_img)
            print(f"DEBUG: Loaded mask image: mode={mask_img.mode}, size={mask_img.size}")
            print(f"DEBUG: Contents array length: {len(contents)} (prompt + image + mask)")
        else:
            print(f"DEBUG: Contents array length: {len(contents)} (prompt + image only)")
        
        # --- API Call following the exact pattern from promptangemini.md ---
        print(f"DEBUG: About to send request to Gemini 2.5 Flash Image API...")
        print(f"Worker: Sending request to Gemini 2.5 Flash Image API with {volume_ml}ml...")
        
        resp = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=contents,  # Text + Image + optional Mask as input
        )
        
        # --- Extract image from response (ignore text) ---
        image_found = False
        
        if resp.candidates and len(resp.candidates) > 0:
            # Look through ALL parts to find the image
            for part in resp.candidates[0].content.parts:
                if getattr(part, "inline_data", None):
                    # Found the image data!
                    print(f"Worker: Found image data, extracting...")
                    try:
                        image_data = part.inline_data.data
                        
                        # Save to file AND output via stdout as backup
                        with open(output_path, 'wb') as f:
                            f.write(image_data)
                            
                        # Also output the image data as base64 to stdout
                        import base64
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                        print(f"IMAGE_DATA_START:{base64_data}:IMAGE_DATA_END")
                        print(f"Worker: Successfully saved output to {output_path}")
                        image_found = True
                        return  # Exit successfully
                        
                    except Exception as e:
                        print(f"Worker Error processing image: {e}", file=sys.stderr)
        
        if not image_found:
            raise RuntimeError(f"Gemini 2.5 Flash Image API did not return an image in the response.")
            
    except Exception as e:
        # Print error to stderr so the main process can capture it
        print(f"Gemini Worker Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini API Worker")
    parser.add_argument("--input", required=True, help="Path to the input image.")
    parser.add_argument("--output", required=True, help="Path to save the output image.")
    parser.add_argument("--volume", required=True, type=float, help="Volume in ml.")
    parser.add_argument("--area", default="lips", help="Treatment area (lips, chin, cheeks, forehead).")
    parser.add_argument("--mask", help="Path to the mask image (optional).")
    
    args = parser.parse_args()
    
    run_gemini_process(args.input, args.output, args.volume, args.area, args.mask)
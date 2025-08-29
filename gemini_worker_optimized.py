# gemini_worker_optimized.py
# Optimized prompts for Gemini 2.5 Flash Image

import os
import sys
import argparse
import base64
import io
from PIL import Image
import logging

# Configure logging to stderr so it doesn't interfere with stdout image data
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

# Import Google Genai SDK
try:
    from google import genai
    from google.genai import types
    print("✅ Using google-genai SDK", file=sys.stderr)
except ImportError:
    print("❌ ERROR: google-genai package not found. Install with: pip install google-genai", file=sys.stderr)
    sys.exit(1)

def get_prompt_for_lips(volume_ml: float) -> str:
    """Generate volume-specific prompts optimized for Gemini 2.5 Flash Image"""
    
    # Calculate intensity percentage (0-100%) based on volume
    intensity = min(volume_ml * 20, 100)  # 5ml = 100%
    
    if volume_ml <= 0.5:  # 0-0.5ml: Minimal hydration and tightening
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid lip treatment. 

TRANSFORMATION REQUIRED: Apply {intensity:.0f}% enhancement intensity to show minimal but visible lip improvement. The lips should appear slightly more hydrated and defined, as if professionally treated.

SPECIFIC VISUAL CHANGES:
- Enhance lip texture to appear more moisturized and smooth
- Add subtle definition to the natural lip border
- Create slight skin tightening effect around lip edges
- NO volume increase to lip body - maintain exact original size and shape
- Result should look like professional lip care, not enhancement

CRITICAL PRESERVATION:
- Keep identical lip color, undertones, and pigmentation
- Maintain original lighting, shadows, and image composition
- Preserve all facial proportions and natural skin texture
- Keep the same background and camera angle

The output should demonstrate the subtle but professional result of minimal aesthetic lip treatment."""

    elif volume_ml <= 1.0:  # 0.5-1ml: Light tightening + minimal volume
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid lip enhancement treatment.

TRANSFORMATION REQUIRED: Apply {intensity:.0f}% enhancement intensity to create visible but natural lip improvement. The lips should show clear tightening effect plus minimal volume increase.

SPECIFIC VISUAL CHANGES:
- Transform lips to show 10-15% volume increase in both upper and lower lips
- Add visible skin tightening effect creating better lip definition
- Enhance the natural cupid's bow with subtle definition
- Improve vermillion border clarity and sharpness
- Create the appearance of naturally refreshed, slightly fuller lips

CRITICAL PRESERVATION:
- Keep identical lip color, undertones, and pigmentation
- Maintain original lighting, shadows, and image composition
- Preserve all facial proportions and natural skin texture
- Keep the same background and camera angle

The output should demonstrate a clear but natural aesthetic enhancement result."""

    elif volume_ml <= 1.5:  # 1-1.5ml: Clear volume increase
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid lip enhancement treatment.

TRANSFORMATION REQUIRED: Apply {intensity:.0f}% enhancement intensity to create noticeable lip volume increase. The transformation should show clear, visible improvement that's attractively fuller yet natural.

SPECIFIC VISUAL CHANGES:
- Transform lips to show 20-30% volume increase (upper lip 40%, lower lip 60%)
- Add enhanced lip projection and forward fullness
- Create well-defined cupid's bow with noticeable peaks
- Enhance vermillion border definition for clearer lip outline
- Result should be clearly fuller and more attractive than the original

CRITICAL PRESERVATION:
- Keep identical lip color, undertones, and pigmentation
- Maintain original lighting, shadows, and image composition
- Preserve all facial proportions and natural skin texture
- Keep the same background and camera angle

The output should demonstrate significant but natural aesthetic enhancement with clearly visible improvement."""

    elif volume_ml <= 2.0:  # 1.5-2ml: Significant volume increase
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid lip enhancement treatment.

TRANSFORMATION REQUIRED: Apply {intensity:.0f}% enhancement intensity to create substantial lip volume increase. The transformation should show dramatic but natural-looking enhancement with major improvement over the original.

SPECIFIC VISUAL CHANGES:
- Transform lips to show 35-45% volume increase (upper lip 45%, lower lip 55%)
- Add significant lip projection and attractive fullness
- Create pronounced cupid's bow with clear, defined peaks
- Enhance vermillion borders with sharp definition
- Result should show notable fullness and attractiveness

CRITICAL PRESERVATION:
- Keep identical lip color, undertones, and pigmentation
- Maintain original lighting, shadows, and image composition
- Preserve all facial proportions and natural skin texture
- Keep the same background and camera angle

The output should demonstrate dramatic but professional aesthetic enhancement with substantial visual improvement."""

    elif volume_ml <= 3.0:  # 2-3ml: Major enhancement
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid lip enhancement treatment.

TRANSFORMATION REQUIRED: Apply {intensity:.0f}% enhancement intensity to create major lip transformation. The enhancement should show significant volume increase with pronounced projection while maintaining naturalness.

SPECIFIC VISUAL CHANGES:
- Transform lips to show 50-65% volume increase (upper lip 45%, lower lip 55%)
- Add major lip projection and enhanced eversion
- Create dramatic cupid's bow with pronounced, well-defined peaks
- Enhance vermillion borders with strong definition
- Add subtle philtral column enhancement for facial balance
- Result should be significantly enhanced yet naturally beautiful

CRITICAL PRESERVATION:
- Keep identical lip color, undertones, and pigmentation
- Maintain original lighting, shadows, and image composition
- Preserve all facial proportions and natural skin texture
- Keep the same background and camera angle

The output should demonstrate major aesthetic transformation while maintaining facial harmony and natural beauty."""

    else:  # 3ml+: Maximum transformation
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid lip enhancement treatment.

TRANSFORMATION REQUIRED: Apply {intensity:.0f}% enhancement intensity to create maximum lip transformation. This should represent the ultimate aesthetic enhancement with expert precision while maintaining facial harmony.

SPECIFIC VISUAL CHANGES:
- Transform lips to show 85-100% maximum volume increase (upper lip 45%, lower lip 55%)
- Add ultimate lip projection and overall fullness
- Create maximum cupid's bow definition with dramatic, sculpted peaks
- Enhance vermillion borders to maximum definition
- Add significant lip eversion for bold yet natural effect
- Include subtle philtral column enhancement for facial balance
- Result should show luxury-level aesthetic enhancement

CRITICAL PRESERVATION:
- Keep identical lip color, undertones, and pigmentation
- Maintain original lighting, shadows, and image composition
- Preserve all facial proportions and natural skin texture
- Keep the same background and camera angle

The output should demonstrate maximum professional aesthetic transformation with expert precision and maintained facial harmony."""

def get_prompt_for_cheeks(volume_ml: float) -> str:
    """Generate specific prompts for cheek filler treatments optimized for Gemini 2.5 Flash Image"""
    if volume_ml <= 1.0:
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid cheek filler treatment.

TRANSFORMATION REQUIRED: Apply subtle cheek contouring enhancement to show minimal but visible improvement in mid-cheek volume and natural cheekbone projection.

SPECIFIC VISUAL CHANGES:
- Add minimal volume to the mid-cheek area for subtle enhancement
- Enhance natural cheekbone projection slightly
- Create subtle lifting effect in the cheek region
- Improve facial contours while preserving natural appearance

CRITICAL PRESERVATION:
- Maintain original skin texture, pores, and natural facial details
- Keep identical lighting, shadows, and image composition
- Preserve natural facial proportions and bone structure
- Avoid artificial shine or over-smoothing effects

The output should demonstrate professional subtle cheek enhancement with natural-looking results."""
    elif volume_ml <= 3.0:
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid cheek filler treatment.

TRANSFORMATION REQUIRED: Apply moderate cheek enhancement to create visible but natural cheek projection and improved facial contours.

SPECIFIC VISUAL CHANGES:
- Add moderate volume to mid-cheek and cheekbone area
- Create visible but natural cheek projection
- Enhance facial contours with subtle lifting effect
- Improve cheekbone definition and overall facial structure

CRITICAL PRESERVATION:
- Maintain original skin texture, pores, and natural facial details
- Keep identical lighting, shadows, and image composition
- Preserve natural facial proportions and harmony
- Create balanced, proportional enhancement

The output should demonstrate professional moderate cheek enhancement with balanced, natural results."""
    else:
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid cheek filler treatment.

TRANSFORMATION REQUIRED: Apply significant cheek enhancement to create pronounced cheek projection and dramatic facial contouring while maintaining natural beauty.

SPECIFIC VISUAL CHANGES:
- Add substantial volume to cheekbone and mid-cheek area
- Create pronounced cheek projection and definition
- Apply significant facial contouring and lifting effect
- Enhance overall facial structure and cheekbone prominence

CRITICAL PRESERVATION:
- Maintain original skin texture, pores, and natural facial details
- Keep identical lighting, shadows, and image composition
- Balance dramatic enhancement with overall facial harmony
- Preserve natural beauty while showing clear improvement

The output should demonstrate professional significant cheek enhancement with dramatic but natural-looking results."""

def get_prompt_for_chin(volume_ml: float) -> str:
    """Generate specific prompts for chin filler treatments optimized for Gemini 2.5 Flash Image"""
    if volume_ml <= 1.0:
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid chin filler treatment.

TRANSFORMATION REQUIRED: Apply subtle chin projection enhancement to show minimal but visible improvement in chin definition and facial balance.

SPECIFIC VISUAL CHANGES:
- Add minimal forward projection to the chin area
- Create slight improvement in jawline definition
- Enhance chin-to-neck angle subtly
- Preserve natural chin shape while improving proportions

CRITICAL PRESERVATION:
- Maintain original skin texture, pores, and natural facial details
- Keep identical lighting, shadows, and image composition
- Preserve natural facial proportions and bone structure
- Create natural-looking enhancement without over-projection

The output should demonstrate professional subtle chin enhancement with improved facial balance."""
    elif volume_ml <= 2.5:
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid chin filler treatment.

TRANSFORMATION REQUIRED: Apply moderate chin enhancement to create visible improvement in chin projection and jawline definition.

SPECIFIC VISUAL CHANGES:
- Add moderate forward projection and slight vertical lengthening
- Improve jawline definition and chin prominence
- Enhance chin-to-neck angle for better facial proportions
- Create balanced enhancement for improved facial harmony

CRITICAL PRESERVATION:
- Maintain original skin texture, pores, and natural facial details
- Keep identical lighting, shadows, and image composition
- Preserve natural beauty while showing clear improvement
- Balance enhancement with overall facial harmony

The output should demonstrate professional moderate chin enhancement with balanced, natural results."""
    else:
        return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of a {volume_ml}ml hyaluronic acid chin filler treatment.

TRANSFORMATION REQUIRED: Apply significant chin enhancement to create substantial improvement in chin projection and facial profile transformation.

SPECIFIC VISUAL CHANGES:
- Add substantial forward projection and vertical lengthening
- Create pronounced jawline definition and chin prominence
- Significantly improve chin-to-neck angle and facial proportions
- Transform facial profile while maintaining natural beauty

CRITICAL PRESERVATION:
- Maintain original skin texture, pores, and natural facial details
- Keep identical lighting, shadows, and image composition
- Create dramatic but natural-looking transformation
- Balance bold enhancement with facial harmony

The output should demonstrate professional significant chin enhancement with dramatic but natural profile transformation."""

def get_prompt_for_forehead(volume_ml: float) -> str:
    """Generate specific prompts for forehead/botox treatments optimized for Gemini 2.5 Flash Image"""
    # Forehead treatments are typically botox (wrinkle reduction) rather than volume
    return f"""Using the provided facial photograph, create a photorealistic visualization showing the result of professional botox forehead treatment.

TRANSFORMATION REQUIRED: Apply forehead wrinkle reduction to simulate expert botox treatment results, showing significant improvement in horizontal forehead lines.

SPECIFIC VISUAL CHANGES:
- Reduce horizontal forehead lines and wrinkles significantly
- Smooth forehead skin while preserving natural texture and pores
- Maintain natural forehead contours and subtle muscle definition
- Preserve capability for natural facial expressions
- Keep eyebrow position and natural arch unchanged

CRITICAL PRESERVATION:
- Maintain original skin tone, texture, and natural facial details
- Keep identical lighting, shadows, and image composition
- Preserve natural facial expressions and muscle capability
- Avoid frozen or artificial appearance
- Maintain natural forehead bone structure

The output should demonstrate professional botox treatment results with natural-looking wrinkle reduction that appears expertly treated."""

def main():
    parser = argparse.ArgumentParser(description='Generate aesthetic simulation using Gemini 2.5 Flash Image')
    parser.add_argument('--input', required=True, help='Input image path')
    parser.add_argument('--output', required=True, help='Output image path')
    parser.add_argument('--mask', required=False, help='Mask image path (optional)')
    parser.add_argument('--volume', type=float, required=True, help='Treatment volume in ml')
    parser.add_argument('--area', required=True, choices=['lips', 'cheeks', 'chin', 'forehead'], help='Treatment area')
    
    args = parser.parse_args()
    
    # Configure Google API
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    
    # Configure client
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
    
    # Load and process input image
    try:
        print(f"🔄 Loading input image from: {args.input}", file=sys.stderr)
        input_image = Image.open(args.input).convert('RGB')
        print(f"✅ Input image loaded: {input_image.size} pixels", file=sys.stderr)
    except Exception as e:
        print(f"❌ Error loading input image: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Generate area-specific prompt
    area_prompts = {
        'lips': get_prompt_for_lips,
        'cheeks': get_prompt_for_cheeks, 
        'chin': get_prompt_for_chin,
        'forehead': get_prompt_for_forehead
    }
    
    volume_prompt = area_prompts[args.area](args.volume)
    
    # Prepare content for multimodal API call
    content_parts = [volume_prompt, input_image]
    
    # Add mask if provided
    if args.mask:
        try:
            mask_image = Image.open(args.mask).convert('RGB')
            content_parts.append("MASK IMAGE (shows treatment area):")
            content_parts.append(mask_image)
            print(f"✅ Mask image loaded: {mask_image.size} pixels", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ Warning: Could not load mask image: {e}", file=sys.stderr)
    
    # Create the optimized prompt for Gemini 2.5 Flash Image
    final_prompt = f"""MEDICAL AESTHETIC VISUALIZATION REQUEST:

{volume_prompt}

MASK GUIDANCE: The provided mask indicates the treatment area. Focus all changes strictly within this masked region while preserving everything outside it completely unchanged.

OUTPUT REQUIREMENTS:
- Generate a photorealistic result showing the immediate post-treatment appearance
- The image should look like a professional clinical "after" photograph
- Maintain the same photographic quality, resolution, and technical properties as the input
- NO visible treatment marks, injection sites, swelling, or medical artifacts

This is for educational and consultation visualization purposes only."""
    
    print(f"🎯 OPTIMIZED PROMPT FOR GEMINI 2.5 FLASH IMAGE:", file=sys.stderr)
    print(f"{final_prompt[:300]}...", file=sys.stderr)  # Truncate for readability
    
    try:
        print("🚀 Calling Gemini 2.5 Flash Image API...", file=sys.stderr)
        
        # Make the API call with optimized configuration
        response = client.models.generate_content(
            model='gemini-2.5-flash-image-preview',
            contents=content_parts,
            config=types.GenerateContentConfig(
                response_modalities=[types.Modality.TEXT, types.Modality.IMAGE],
                temperature=0.3,  # Lower temperature for more consistent results
                top_p=0.8,
                candidate_count=1,
                max_output_tokens=2048
            )
        )
        
        print("✅ Success with gemini-2.5-flash-image-preview", file=sys.stderr)
        
        # Extract image data from response
        if hasattr(response, 'candidates') and len(response.candidates) > 0:
            candidate = response.candidates[0]
            print(f"🔍 DEBUG: Candidate parts count: {len(candidate.content.parts)}", file=sys.stderr)
            
            image_found = False
            for i, part in enumerate(candidate.content.parts):
                print(f"🔍 DEBUG: Part {i} type: {type(part)}", file=sys.stderr)
                
                if hasattr(part, 'inline_data'):
                    print(f"🔍 DEBUG: Found inline_data in part {i}", file=sys.stderr)
                    result_data = part.inline_data.data
                    
                    # Handle both raw bytes and base64 data
                    if isinstance(result_data, bytes):
                        print("🔍 DEBUG: Got RAW BYTES from Gemini - using directly! ✅", file=sys.stderr)
                        image_bytes = result_data
                    elif isinstance(result_data, str):
                        print("🔍 DEBUG: Got Base64 string - decoding...", file=sys.stderr)
                        image_bytes = base64.b64decode(result_data)
                    else:
                        print(f"🔍 DEBUG: Unexpected data type: {type(result_data)}", file=sys.stderr)
                        continue
                    
                    # Convert to PIL Image
                    result_image = Image.open(io.BytesIO(image_bytes))
                    print(f"✅ Successfully loaded result image: {result_image.size}, mode: {result_image.mode}", file=sys.stderr)
                    
                    # Convert to RGB if needed and compress for stdout transmission
                    if result_image.mode != 'RGB':
                        result_image = result_image.convert('RGB')
                    
                    # Compress to JPEG for efficient transmission
                    final_buffer = io.BytesIO()
                    result_image.save(final_buffer, format='JPEG', quality=85, optimize=True)
                    final_image_bytes = final_buffer.getvalue()
                    print(f"📦 Compressed image size: {len(final_image_bytes)/1024:.1f} KB", file=sys.stderr)
                    
                    # Encode as base64 for stdout transmission
                    result_base64 = base64.b64encode(final_image_bytes).decode('utf-8')
                    
                    # Output the base64 data with markers
                    print("✅ Gemini successfully generated aesthetic simulation", file=sys.stderr)
                    print(f"IMAGE_DATA_START:{result_base64}:IMAGE_DATA_END")
                    sys.stdout.flush()
                    image_found = True
                    break
            
            if not image_found:
                print("❌ No image data found in response", file=sys.stderr)
                sys.exit(1)
        else:
            print("❌ No candidates in response", file=sys.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ ERROR in Gemini API call: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
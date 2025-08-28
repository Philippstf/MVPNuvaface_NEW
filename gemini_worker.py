# gemini_worker.py
"""
A dedicated, isolated worker script to call the Gemini API.
This script is intended to be called from a separate process to avoid
dependency conflicts between mediapipe and google-generativeai.
"""
import os
import sys
import time
import argparse
from pathlib import Path
from PIL import Image
from dotenv import load_dotenv
from io import BytesIO

# Force UTF-8 encoding for Windows
if sys.platform.startswith('win'):
    import codecs
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')

# Using the new google-genai package for Gemini 2.5 Flash Image
try:
    from google import genai
    from google.genai import types
    print("Using google-genai SDK")
except ImportError:
    print("Error: google-genai package not found. Please install it with: pip install google-genai", file=sys.stderr)
    sys.exit(1)


# --- Precise Volume-Based Prompt System for Consistent Results ---
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
        return """Subtle cheek contouring using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- Add minimal volume to the mid-cheek area
- Enhance natural cheekbone projection slightly
- Create subtle lifting effect
- Preserve natural facial contours

TECHNICAL REQUIREMENTS:
- Maintain original skin texture and lighting
- No artificial shine or over-smoothing
- Keep natural facial proportions"""
    
    elif volume_ml <= 3.0:
        return """Moderate cheek enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:  
- Add moderate volume to mid-cheek and cheekbone area
- Create visible but natural cheek projection
- Enhance facial contours with subtle lifting
- Improve cheekbone definition
        
TECHNICAL REQUIREMENTS:
- Maintain original skin texture and lighting
- Create balanced, proportional enhancement
- Avoid over-smoothing or artificial appearance"""
        
    else:
        return """Significant cheek enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- Add substantial volume to cheekbone and mid-cheek area
- Create pronounced cheek projection and definition
- Significant facial contouring and lifting effect
- Enhance overall facial structure
        
TECHNICAL REQUIREMENTS:
- Maintain original skin texture and lighting
- Create dramatic but natural-looking enhancement
- Balance enhancement with overall facial harmony"""

def get_prompt_for_chin(volume_ml: float) -> str:
    """Generate specific prompts for chin filler treatments"""
    if volume_ml <= 1.0:
        return """Subtle chin projection enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- Add minimal forward projection to chin
- Create subtle rounding and definition
- Enhance jawline slightly
- Maintain natural chin proportions
        
TECHNICAL REQUIREMENTS:
- Preserve original skin texture
- Keep natural facial balance
- Avoid artificial or overdone appearance"""
        
    elif volume_ml <= 2.5:
        return """Moderate chin enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- Add moderate forward projection to chin
- Create noticeable but natural chin definition
- Enhance jawline and lower face balance
- Improve overall facial profile
        
TECHNICAL REQUIREMENTS:
- Maintain original skin texture and lighting
- Create balanced facial enhancement
- Keep natural proportions"""
        
    else:
        return """Significant chin enhancement using {volume_ml}ml hyaluronic acid filler.
        
SPECIFIC INSTRUCTIONS:
- Add substantial forward projection to chin
- Create pronounced chin definition and structure
- Dramatically improve jawline and facial profile
- Enhance overall lower face architecture
        
TECHNICAL REQUIREMENTS:
- Maintain original skin texture
- Create dramatic but balanced enhancement
- Preserve facial harmony"""

def get_prompt_for_forehead(volume_ml: float) -> str:
    """Generate prompts for forehead/botox treatments"""
    return """Reduce horizontal forehead wrinkles and lines.
    
SPECIFIC INSTRUCTIONS:
- Smooth out horizontal forehead lines
- Reduce expression wrinkles
- Maintain natural forehead texture
- Keep natural facial expressions
    
TECHNICAL REQUIREMENTS:
- Preserve skin pores and natural texture
- Maintain original lighting
- Avoid over-smoothing or artificial appearance
- Keep natural skin variations"""

# Model hierarchy for fallback system
GEMINI_MODELS = [
    "gemini-2.5-flash-image-preview",
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro-latest", 
    "gemini-1.5-flash-latest"
]

def create_gemini_client():
    """Create Gemini client with API key and timeout"""
    # Check for API keys
    google_key = os.getenv('GOOGLE_API_KEY')
    gemini_key = os.getenv('GEMINI_API_KEY')
    
    print(f"DEBUG: GOOGLE_API_KEY present: {google_key is not None}")
    print(f"DEBUG: GEMINI_API_KEY present: {gemini_key is not None}")
    if google_key:
        print(f"DEBUG: GOOGLE_API_KEY length: {len(google_key)}")
        print(f"DEBUG: GOOGLE_API_KEY starts with: {google_key[:20]}...")
    
    api_key = google_key or gemini_key
    
    if not api_key:
        raise ValueError("No API key found. Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")
    
    if google_key and gemini_key:
        print("Both GOOGLE_API_KEY and GEMINI_API_KEY are set. Using GOOGLE_API_KEY.")
    
    # Add HTTP timeout based on latest Aug 26 docs: SDK has 60s hard limit, 30s is optimal
    # Gemini 2.5 Flash Image requires v1alpha (not v1 stable yet)
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=30_000,  # 30 seconds - optimal based on Aug 26 docs
            api_version='v1alpha'  # Gemini 2.5 Flash Image only available in v1alpha
        )
    )


def generate_with_fallback(client, prompt, image_data, mask_data=None):
    """Try multiple Gemini models with fallback logic"""
    last_error = None
    
    print(f"DEBUG: generate_with_fallback started", file=sys.stderr)
    print(f"DEBUG: Client type: {type(client)}", file=sys.stderr)
    print(f"DEBUG: Available models to try: {GEMINI_MODELS}", file=sys.stderr)
    
    for model_name in GEMINI_MODELS:
        try:
            print(f"========== TRYING MODEL: {model_name} ==========", file=sys.stderr)
            print(f"DEBUG: Image data type: {type(image_data)}", file=sys.stderr)
            print(f"DEBUG: Mask provided: {mask_data is not None}", file=sys.stderr)
            if mask_data:
                print(f"DEBUG: Mask data type: {type(mask_data)}", file=sys.stderr)
            print(f"DEBUG: Prompt length: {len(prompt)} chars", file=sys.stderr)
            print(f"DEBUG: First 100 chars of prompt: {prompt[:100]}...", file=sys.stderr)
            
            # Prepare the content for new google-genai SDK using correct format
            print(f"DEBUG: Preparing Gemini API call...", file=sys.stderr)
            
            # Create the content parts list
            contents = [prompt, image_data]
            if mask_data:
                contents.append(mask_data)
            print(f"DEBUG: Contents list has {len(contents)} parts", file=sys.stderr)
            
            # Use proper config object with thinking disabled for speed
            print(f"DEBUG: Creating GenerateContentConfig...", file=sys.stderr)
            config = types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.8,
                max_output_tokens=8192,
                response_modalities=[types.Modality.TEXT, types.Modality.IMAGE],
                thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disable thinking for speed!
            )
            print(f"DEBUG: Config created: temp={config.temperature}, top_p={config.top_p}", file=sys.stderr)
            
            # Wrap API call with timeout handling (SDK has 60s hard limit)
            print(f"DEBUG: About to call client.models.generate_content...", file=sys.stderr)
            print(f"DEBUG: Model: {model_name}", file=sys.stderr)
            print(f"DEBUG: API endpoint will be: v1alpha/models/{model_name}:generateContent", file=sys.stderr)
            
            try:
                import time
                start_time = time.time()
                print(f"DEBUG: API CALL START at {start_time}", file=sys.stderr)
                
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config
                )
                
                elapsed = time.time() - start_time
                print(f"DEBUG: API CALL COMPLETED in {elapsed:.2f} seconds", file=sys.stderr)
                
            except Exception as api_error:
                elapsed = time.time() - start_time
                print(f"ERROR: API call failed after {elapsed:.2f} seconds", file=sys.stderr)
                print(f"ERROR Type: {type(api_error).__name__}", file=sys.stderr)
                print(f"ERROR Details: {api_error}", file=sys.stderr)
                
                error_msg = str(api_error).lower()
                if "timeout" in error_msg or "disconnected" in error_msg or "remotprotocol" in error_msg:
                    print(f"WARNING: {model_name} timed out (SDK 60s limit), trying next model...", file=sys.stderr)
                    last_error = f"Timeout with {model_name}: {api_error}"
                    continue
                elif "api key" in error_msg or "invalid_argument" in error_msg:
                    print(f"CRITICAL: API Key issue detected!", file=sys.stderr)
                    raise api_error
                else:
                    print(f"WARNING: Unknown error, trying next model...", file=sys.stderr)
                    last_error = api_error
                    continue
            
            print(f"DEBUG: Got response from {model_name}", file=sys.stderr)
            print(f"DEBUG: Response type: {type(response)}", file=sys.stderr)
            
            if response and response.candidates and len(response.candidates) > 0:
                print(f"DEBUG: Response has {len(response.candidates)} candidates", file=sys.stderr)
                candidate = response.candidates[0]
                print(f"DEBUG: Candidate has content: {candidate.content is not None}")
                if candidate.content and candidate.content.parts:
                    print(f"DEBUG: Content has {len(candidate.content.parts)} parts")
                    for i, part in enumerate(candidate.content.parts):
                        print(f"DEBUG: Part {i}: has inline_data = {hasattr(part, 'inline_data') and part.inline_data is not None}")
                        if hasattr(part, 'inline_data') and part.inline_data:
                            data_size = len(part.inline_data.data) if part.inline_data.data else 0
                            print(f"DEBUG: Part {i} data size: {data_size} bytes")
                            
                            # Validate that we got actual data
                            if not part.inline_data.data or len(part.inline_data.data) < 100:
                                print(f"ERROR: {model_name} returned empty or too small image data, trying next model...")
                                last_error = f"Empty image data from {model_name}"
                                break
                            
                            # Try to validate the image data by decoding it
                            try:
                                test_bytes = base64.b64decode(part.inline_data.data)
                                test_image = Image.open(BytesIO(test_bytes))
                                # Validate dimensions
                                if test_image.size[0] < 10 or test_image.size[1] < 10:
                                    raise ValueError(f"Invalid dimensions: {test_image.size}")
                                print(f"SUCCESS: Using model {model_name}")
                                return part.inline_data.data, model_name
                            except Exception as validation_error:
                                print(f"ERROR: {model_name} returned corrupt image data: {validation_error}")
                                print(f"ERROR: Trying next model...")
                                last_error = f"Corrupt image data from {model_name}: {validation_error}"
                                break
                        else:
                            print(f"DEBUG: Part {i} has text: {hasattr(part, 'text') and part.text}")
                else:
                    print(f"DEBUG: Candidate content is None or has no parts")
                
                print(f"ERROR: No valid image data in response from {model_name}")
                last_error = f"No valid image data in response from {model_name}"
            else:
                print(f"DEBUG: No response or no candidates from {model_name}")
                last_error = f"No response from {model_name}"
                
        except Exception as model_error:
            error_str = str(model_error).lower()
            if "quota" in error_str or "rate" in error_str or "limit" in error_str:
                print(f"ERROR QUOTA/RATE LIMIT: {model_name} - {model_error}")
                if "try again" in error_str:
                    print(f"GEMINI {model_name} nicht verfügbar, weiter mit nächstem Modell...")
            elif "not found" in error_str or "does not exist" in error_str:
                print(f"ERROR MODEL NOT FOUND: {model_name} - {model_error}")
                print(f"GEMINI {model_name} nicht verfügbar, weiter mit nächstem Modell...")
            else:
                print(f"ERROR UNKNOWN: {model_name} - {model_error}")
                print(f"GEMINI {model_name} nicht verfügbar, weiter mit nächstem Modell...")
            
            last_error = model_error
            continue
    
    # All models failed
    raise Exception(f"All Gemini models failed. Last error: {last_error}")

def main():
    """Main worker function"""
    print("WORKER: Starting gemini_worker.py", file=sys.stderr)
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Gemini Worker for NuvaFace')
    parser.add_argument('--input', required=True, help='Input image path')
    parser.add_argument('--output', required=True, help='Output image path') 
    parser.add_argument('--volume', type=float, required=True, help='Filler volume in ml')
    parser.add_argument('--area', required=True, help='Treatment area')
    parser.add_argument('--mask', help='Mask image path (optional)')
    
    args = parser.parse_args()
    print(f"WORKER: Args parsed - area={args.area}, volume={args.volume}", file=sys.stderr)
    
    try:
        # Load input image
        print(f"WORKER: Loading input image from {args.input}", file=sys.stderr)
        if not os.path.exists(args.input):
            print(f"ERROR: Input file does not exist: {args.input}", file=sys.stderr)
            raise FileNotFoundError(f"Input file not found: {args.input}")
            
        input_image = Image.open(args.input)
        print(f"WORKER: Image loaded, mode={input_image.mode}, size={input_image.size}", file=sys.stderr)
        
        if input_image.mode != 'RGB':
            print(f"WORKER: Converting image from {input_image.mode} to RGB", file=sys.stderr)
            input_image = input_image.convert('RGB')
        
        # Prepare image data for Gemini using correct google-genai format
        # Reduce image size to prevent payload issues
        if input_image.size[0] > 512 or input_image.size[1] > 512:
            print(f"WORKER: Resizing image from {input_image.size} to 512x512 for faster processing", file=sys.stderr)
            input_image = input_image.resize((512, 512), Image.Resampling.LANCZOS)
        
        img_byte_array = BytesIO()
        input_image.save(img_byte_array, format='JPEG', quality=85)  # Use JPEG for smaller size
        img_bytes = img_byte_array.getvalue()
        print(f"WORKER: Image encoded as JPEG, size={len(img_bytes)} bytes", file=sys.stderr)
        
        image_data = types.Part.from_bytes(
            data=img_bytes,
            mime_type="image/jpeg"
        )
        print(f"WORKER: Created types.Part for image", file=sys.stderr)
        
        # Load mask if provided
        mask_data = None
        if args.mask:
            print(f"WORKER: Checking mask at {args.mask}", file=sys.stderr)
            if os.path.exists(args.mask):
                print(f"WORKER: Loading mask image", file=sys.stderr)
                mask_image = Image.open(args.mask)
                print(f"WORKER: Mask loaded, mode={mask_image.mode}, size={mask_image.size}", file=sys.stderr)
                
                if mask_image.mode != 'L':
                    print(f"WORKER: Converting mask from {mask_image.mode} to L", file=sys.stderr)
                    mask_image = mask_image.convert('L')
                
                mask_byte_array = BytesIO()
                mask_image.save(mask_byte_array, format='PNG')
                mask_bytes = mask_byte_array.getvalue()
                print(f"WORKER: Mask encoded as PNG, size={len(mask_bytes)} bytes", file=sys.stderr)
                
                mask_data = types.Part.from_bytes(
                    data=mask_bytes,
                    mime_type="image/png"
                )
                print(f"WORKER: Created types.Part for mask", file=sys.stderr)
            else:
                print(f"WARNING: Mask file not found: {args.mask}", file=sys.stderr)
        else:
            print(f"WORKER: No mask provided", file=sys.stderr)
        
        # Generate appropriate prompt based on area
        print(f"WORKER: Generating prompt for area='{args.area}', volume={args.volume}ml", file=sys.stderr)
        
        if args.area.lower() == 'lips':
            prompt = get_prompt_for_lips(args.volume)
            print(f"WORKER: Generated lips prompt", file=sys.stderr)
        elif args.area.lower() == 'cheeks':
            prompt = get_prompt_for_cheeks(args.volume)
            print(f"WORKER: Generated cheeks prompt", file=sys.stderr)
        elif args.area.lower() == 'chin':
            prompt = get_prompt_for_chin(args.volume)
            print(f"WORKER: Generated chin prompt", file=sys.stderr)
        elif args.area.lower() == 'forehead':
            prompt = get_prompt_for_forehead(args.volume)
            print(f"WORKER: Generated forehead prompt", file=sys.stderr)
        else:
            print(f"ERROR: Unsupported area: {args.area}", file=sys.stderr)
            raise ValueError(f"Unsupported area: {args.area}")
        
        print(f"WORKER: Prompt length: {len(prompt)} chars", file=sys.stderr)
        
        # Create client and generate image
        print("WORKER: Creating Gemini client...", file=sys.stderr)
        client = create_gemini_client()
        print("WORKER: Gemini client created successfully", file=sys.stderr)
        
        try:
            print("WORKER: Calling generate_with_fallback...", file=sys.stderr)
            result_data, used_model = generate_with_fallback(client, prompt, image_data, mask_data)
            print(f"WORKER: Successfully generated with {used_model}", file=sys.stderr)
        except Exception as e:
            error_str = str(e).lower()
            print(f"ERROR: All Gemini models failed: {e}", file=sys.stderr)
            
            # Check for regional restriction
            if "not available in your country" in error_str or "failed_precondition" in error_str:
                print("DETECTED: Regional restriction for image generation", file=sys.stderr)
                print("SOLUTION: Please use a VPN to connect from a supported region (US, Canada, etc.)", file=sys.stderr)
                print("ALTERNATIVE: Deploy to Google Cloud Run in us-central1 region", file=sys.stderr)
                
                # For now, return original image with a clear message
                print("FALLBACK: Returning original image due to regional restrictions", file=sys.stderr)
                original_bytes = BytesIO()
                input_image.save(original_bytes, format='PNG')
                result_data = base64.b64encode(original_bytes.getvalue()).decode('utf-8')
                used_model = "regional-fallback-original"
            else:
                print("SERVER_OVERLOAD_MESSAGE: Entschuldigung! :( Die Server sind aktuell überlastet, Ergebnisse können schlechter ausfallen als sonst", file=sys.stderr)
                # Don't fallback to original - let the error propagate
                raise Exception(f"All Gemini models failed or returned corrupt data: {e}")
        
        # Decode and save result
        print(f"WORKER: Decoding result image...", file=sys.stderr)
        import base64
        image_bytes = base64.b64decode(result_data)
        print(f"WORKER: Decoded {len(image_bytes)} bytes", file=sys.stderr)
        
        result_image = Image.open(BytesIO(image_bytes))
        print(f"WORKER: Result image: mode={result_image.mode}, size={result_image.size}", file=sys.stderr)
        
        # Convert to RGB if needed
        if result_image.mode != 'RGB':
            print(f"WORKER: Converting result from {result_image.mode} to RGB", file=sys.stderr)
            result_image = result_image.convert('RGB')
        
        # Save output
        print(f"WORKER: Saving to {args.output}", file=sys.stderr)
        result_image.save(args.output, 'PNG')
        print(f"WORKER: Successfully saved output image", file=sys.stderr)
        
        # Compare images to detect API issues
        print(f"WORKER DEBUG: Starting image comparison...")
        
        # Compare image data
        original_bytes = BytesIO()
        result_bytes = BytesIO()
        input_image.save(original_bytes, format='PNG')
        result_image.save(result_bytes, format='PNG')
        
        original_data = original_bytes.getvalue()
        result_data_bytes = result_bytes.getvalue()
        
        identical = original_data == result_data_bytes
        print(f"WORKER DEBUG: Images are identical: {identical}")
        print(f"WORKER DEBUG: Original size: {len(original_data)} bytes")
        print(f"WORKER DEBUG: Result size: {len(result_data_bytes)} bytes")
        print(f"WORKER DEBUG: Used model: {used_model}")
        print(f"WORKER DEBUG: Volume: {args.volume}ml, Area: {args.area}")
        
        if identical:
            print(f"WORKER WARNING: Gemini returned identical image! API degradation detected.")
        else:
            print(f"WORKER SUCCESS: Gemini returned different image as expected!")
        
        # Always output the image data via stdout for the engine to process
        final_bytes = BytesIO()
        result_image.save(final_bytes, format='PNG')
        final_data = final_bytes.getvalue()
        final_base64 = base64.b64encode(final_data).decode('utf-8')
        
        print("IMAGE_DATA_START:" + final_base64)
        print("IMAGE_DATA_END")
        
        print(f"Image generation completed successfully using {used_model}")
        
    except Exception as e:
        import traceback
        print(f"WORKER FATAL ERROR: {e}", file=sys.stderr)
        print(f"ERROR Type: {type(e).__name__}", file=sys.stderr)
        print(f"ERROR Traceback:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        print(f"Gemini Worker Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    print("="*60, file=sys.stderr)
    print("GEMINI WORKER STARTING", file=sys.stderr)
    print("="*60, file=sys.stderr)
    main()
    print("="*60, file=sys.stderr)
    print("GEMINI WORKER COMPLETED", file=sys.stderr)
    print("="*60, file=sys.stderr)
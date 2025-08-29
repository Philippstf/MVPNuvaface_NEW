#!/usr/bin/env python3
"""Test specific image with direct Gemini call - exactly like the app"""

import asyncio
import os
from PIL import Image
from google import genai
from google.genai import types
import base64
from io import BytesIO

async def test_specific_image():
    # Load the specific image
    img = Image.open(r'c:\Users\phlpp\Downloads\nuvaface_lips_1756486022176.png')
    print(f'Testing with specific image: {img.size} mode: {img.mode}')
    
    # Convert to RGB and JPEG like the app does
    if img.mode != 'RGB':
        img = img.convert('RGB')
        print(f'Converted to RGB: {img.mode}')
    
    # Convert to bytes (same as app)
    img_buffer = BytesIO()
    img.save(img_buffer, format='JPEG', quality=95)
    img_bytes = img_buffer.getvalue()
    print(f'JPEG bytes length: {len(img_bytes)}')
    
    # Same prompt as app
    prompt = """Perform major lip enhancement with 3.0ml hyaluronic acid.
VOLUME EFFECT: 60% intensity - MAJOR VOLUME TRANSFORMATION
- Major volume increase with dramatic fullness
- Strong lip projection and luxurious appearance  
- Very pronounced cupids bow definition
- Result: dramatically fuller, luxurious-looking lips

SPECIFIC INSTRUCTIONS:
- Add 50-65% volume to both upper (45%) and lower lips (55%)
- Create strong definition of lip borders
- Enhance cupids bow prominently
- Show realistic skin texture with enhanced fullness
- Maintain natural skin tone and lighting
- NO other facial changes - only lip enhancement

TECHNICAL REQUIREMENTS:
- Photorealistic result
- Same resolution and quality as input
- Natural lip texture and color
- Professional aesthetic treatment appearance
- Keep all other facial features exactly unchanged"""

    # Check API Key
    api_key = "AIzaSyBW518XAe55P8lmMDRwpYWPWUdQ0D_jMkQ"  # Direct from .env file
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set!")
        return
    
    print(f"API Key found: {api_key[:10]}...")
    
    # Initialize Gemini client
    client = genai.Client(api_key=api_key)
    
    print('Calling Gemini 2.5 Flash Image with exact same setup as app...')
    
    try:
        # Same call as app
        content = types.Content(
            parts=[
                types.Part(text=prompt),
                types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=img_bytes))
            ]
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview", 
            contents=[content],
            config=types.GenerateContentConfig(
                response_modalities=[types.Modality.TEXT, types.Modality.IMAGE],
                temperature=0.3,
            )
        )
        
        print('Gemini call completed successfully!')
        
        # Process response like app
        if not response.candidates or not response.candidates[0].content:
            print("ERROR: No response content from Gemini")
            return
        
        # Find image part
        image_part = None
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_part = part
                break
        
        if not image_part:
            print("ERROR: No image data in Gemini response")
            return
        
        # Extract image data
        image_data = image_part.inline_data.data
        
        if isinstance(image_data, bytes):
            print('Got RAW BYTES from Gemini - using directly!')
            image_bytes = image_data
        elif isinstance(image_data, str):
            print('Got Base64 string - decoding...')
            image_bytes = base64.b64decode(image_data)
        else:
            print(f'ERROR: Unexpected image data type: {type(image_data)}')
            return
        
        # Create result image
        result_image = Image.open(BytesIO(image_bytes))
        
        # Save results for comparison
        result_image.save('direct_test_result.jpg', 'JPEG', quality=85)
        img.save('direct_test_original.jpg', 'JPEG', quality=85)
        
        print(f'SUCCESS! Files saved:')
        print(f'- Original: {img.size}')  
        print(f'- Result: {result_image.size}')
        
        # Compare byte-wise
        original_bytes = BytesIO()
        result_bytes = BytesIO()
        img.save(original_bytes, format='PNG')
        result_image.save(result_bytes, format='PNG')
        
        identical = original_bytes.getvalue() == result_bytes.getvalue()
        print(f'Images byte-identical: {identical}')
        
        if identical:
            print('*** PROBLEM CONFIRMED: Even direct local test gives identical results! ***')
            print('This means Gemini 2.5 Flash Image Preview is not working properly.')
        else:
            print('*** SUCCESS: Direct test shows transformation! ***')
            print('This means the problem is in the app setup, not Gemini itself.')
            
    except Exception as e:
        print(f'ERROR during Gemini call: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_specific_image())
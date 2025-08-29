#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test script to check Gemini 2.5 Flash Image response format
"""
import os
import sys
from PIL import Image
from io import BytesIO
import base64

# Fix encoding for Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    sys.stderr.reconfigure(encoding='utf-8', errors='ignore')

# Use google-genai SDK directly like our worker
try:
    from google import genai
    from google.genai import types
    print("OK Using google-genai SDK")
except ImportError:
    print("ERROR: google-genai package not found")
    exit(1)

def test_gemini_response_format():
    """Test what format Gemini returns image data in"""
    
    # Get API key
    api_key = "AIzaSyBW518XAe55P8lmMDRwpYWPWUdQ0D_jMkQ"
    
    # Create client
    client = genai.Client(api_key=api_key)
    
    # Create a small test image (100x100)
    test_image = Image.new('RGB', (100, 100), color='red')
    img_buffer = BytesIO()
    test_image.save(img_buffer, format='JPEG', quality=80)
    img_bytes = img_buffer.getvalue()
    
    print(f"Test image size: {len(img_bytes)} bytes")
    
    # Create image part
    image_part = types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
    
    # Simple prompt
    prompt = "Make this image slightly brighter. Return the edited image."
    
    print("Making API request...")
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image-preview",
            contents=[prompt, image_part],
            config=types.GenerateContentConfig(
                temperature=0.1,
                top_p=0.8,
                max_output_tokens=8192
            )
        )
        
        print("✅ API request successful!")
        
        if response and response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            
            if candidate.content and candidate.content.parts:
                print(f"🧩 Found {len(candidate.content.parts)} parts in response")
                
                for i, part in enumerate(candidate.content.parts):
                    print(f"\n📝 Part {i}:")
                    
                    # Check for text
                    if hasattr(part, 'text') and part.text:
                        print(f"   📄 Text: {part.text[:100]}...")
                    
                    # Check for inline_data
                    if hasattr(part, 'inline_data') and part.inline_data:
                        print("   🖼️  Has inline_data!")
                        
                        if hasattr(part.inline_data, 'mime_type'):
                            print(f"   📋 MIME type: {part.inline_data.mime_type}")
                        
                        if hasattr(part.inline_data, 'data') and part.inline_data.data:
                            data = part.inline_data.data
                            print(f"   📏 Data type: {type(data)}")
                            print(f"   📏 Data length: {len(data)}")
                            
                            # Show first 50 characters/bytes
                            if isinstance(data, str):
                                print(f"   🔤 First 50 chars: {data[:50]}")
                                print(f"   🔤 Last 50 chars: {data[-50:]}")
                                
                                # Test if it looks like base64
                                import re
                                if re.match(r'^[A-Za-z0-9+/]*={0,2}$', data[:100]):
                                    print("   ✅ Looks like Base64 string!")
                                    
                                    # Try to decode
                                    try:
                                        decoded = base64.b64decode(data)
                                        print(f"   ✅ Base64 decoded: {len(decoded)} bytes")
                                        
                                        # Check if decoded bytes look like image
                                        if decoded.startswith(b'\xff\xd8\xff'):
                                            print("   ✅ Decoded data starts with JPEG signature!")
                                        elif decoded.startswith(b'\x89PNG\r\n\x1a\n'):
                                            print("   ✅ Decoded data starts with PNG signature!")
                                        else:
                                            print(f"   ❓ Unknown format, starts with: {decoded[:10].hex()}")
                                        
                                        # Try to open as image
                                        try:
                                            result_image = Image.open(BytesIO(decoded))
                                            print(f"   ✅ Valid image: {result_image.size} {result_image.mode}")
                                            result_image.save("test_gemini_output.png")
                                            print("   💾 Saved as test_gemini_output.png")
                                            
                                        except Exception as e:
                                            print(f"   ❌ Cannot open as image: {e}")
                                    
                                    except Exception as e:
                                        print(f"   ❌ Base64 decode failed: {e}")
                                else:
                                    print("   ❌ Does NOT look like Base64!")
                                    print(f"   🔍 Hex dump: {data[:32].encode().hex()}")
                            
                            elif isinstance(data, bytes):
                                print(f"   🔤 First 50 bytes (hex): {data[:50].hex()}")
                                print(f"   🔤 Last 50 bytes (hex): {data[-50:].hex()}")
                                
                                # Check if raw bytes look like image
                                if data.startswith(b'\xff\xd8\xff'):
                                    print("   ✅ Raw bytes start with JPEG signature!")
                                elif data.startswith(b'\x89PNG\r\n\x1a\n'):
                                    print("   ✅ Raw bytes start with PNG signature!")
                                else:
                                    print(f"   ❓ Unknown format, starts with: {data[:10].hex()}")
                                
                                # Try to open directly as image
                                try:
                                    result_image = Image.open(BytesIO(data))
                                    print(f"   ✅ Valid raw image: {result_image.size} {result_image.mode}")
                                    result_image.save("test_gemini_output_raw.png")
                                    print("   💾 Saved as test_gemini_output_raw.png")
                                    
                                except Exception as e:
                                    print(f"   ❌ Cannot open raw bytes as image: {e}")
                            
                            else:
                                print(f"   ❓ Unknown data type: {type(data)}")
            else:
                print("❌ No content parts in response")
        else:
            print("❌ No candidates in response")
    
    except Exception as e:
        print(f"❌ API request failed: {e}")

if __name__ == "__main__":
    print("🔍 TESTING GEMINI 2.5 FLASH IMAGE RESPONSE FORMAT")
    print("=" * 60)
    test_gemini_response_format()
    print("=" * 60)
    print("🏁 Test complete!")
#!/usr/bin/env python3
"""
Save the test image for debugging segmentation issues.
"""

import base64
from PIL import Image
import io

# This is the base64 data from the image you uploaded previously
# You'll need to paste the actual base64 string here
test_image_base64 = """
# Paste your test image base64 data here
# Example: iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==
"""

def save_test_image():
    """Save the test image from base64 data."""
    
    if "iVBORw0KGgoAAAANSUhEUgAAAAE" in test_image_base64:
        print("❌ Please replace the placeholder with your actual test image base64 data")
        return False
    
    try:
        # Remove any whitespace/newlines
        clean_base64 = test_image_base64.strip().replace('\n', '').replace(' ', '')
        
        # Decode base64
        image_bytes = base64.b64decode(clean_base64)
        
        # Open with PIL
        image = Image.open(io.BytesIO(image_bytes))
        
        # Save as test_face.jpg
        image.save("test_face.jpg", "JPEG", quality=95)
        
        print(f"✅ Test image saved as test_face.jpg")
        print(f"   Size: {image.size}")
        print(f"   Mode: {image.mode}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving test image: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("SAVE TEST IMAGE FOR DEBUGGING")
    print("=" * 50)
    
    success = save_test_image()
    
    if success:
        print("\n🎉 Ready to run debug script!")
        print("Run: python debug_segmentation.py test_face.jpg")
    else:
        print("\n⚠️  Please:")
        print("1. Upload your test image again in the web UI")
        print("2. Copy the base64 data from the browser network tab")
        print("3. Replace the placeholder in save_test_image.py")
        print("4. Run this script again")
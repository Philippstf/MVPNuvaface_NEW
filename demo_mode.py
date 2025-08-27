#!/usr/bin/env python3
"""
NuvaFace Demo Mode - Test segmentation without heavy ML models
"""

import sys
import os
import base64
import io
from PIL import Image, ImageDraw
import numpy as np

# Add project path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine.parsing import segment_area
from engine.utils import load_image, image_to_base64

def create_demo_result(original: Image.Image, mask: np.ndarray, area: str) -> Image.Image:
    """Create a demo visualization showing the mask overlay."""
    
    # Simple numpy-based overlay
    img_array = np.array(original)
    
    # Create red overlay where mask is active
    red_overlay = np.zeros_like(img_array)
    red_overlay[:, :, 0] = 255  # Red channel
    
    # Apply mask with transparency
    mask_3d = np.stack([mask, mask, mask], axis=2) / 255.0
    alpha = 0.3  # 30% transparency
    
    result_array = img_array * (1 - alpha * mask_3d) + red_overlay * alpha * mask_3d
    result_array = np.clip(result_array, 0, 255).astype(np.uint8)
    
    return Image.fromarray(result_array)

def test_segmentation_demo(image_path: str):
    """Test segmentation and create demo visualization."""
    
    print(f"Loading image: {image_path}")
    
    try:
        # Load image
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
            base64_str = base64.b64encode(image_bytes).decode('utf-8')
        
        # Load with our utils
        img = load_image(base64_str)
        print(f"Image loaded: {img.size}")
        
        # Test all areas
        areas = ['lips', 'forehead', 'chin', 'cheeks']
        
        for area in areas:
            print(f"\nTesting {area} segmentation...")
            
            try:
                mask_img, metadata = segment_area(img, area, feather_px=3)
                
                if metadata.get('error'):
                    print(f"  Error: {metadata['error']}")
                    continue
                
                print(f"  Success! Mask coverage: {metadata['mask_coverage']:.1%}")
                print(f"  Landmarks: {metadata['landmarks_count']}")
                print(f"  Bbox: {metadata['bbox']}")
                
                # Create demo result
                demo_result = create_demo_result(img, mask_img, area)
                
                # Save result
                output_path = f"demo_{area}_result.jpg"
                demo_result.save(output_path, quality=95)
                print(f"  Demo result saved: {output_path}")
                
            except Exception as e:
                print(f"  Failed: {e}")
        
        print(f"\nDemo complete! Check the demo_*_result.jpg files.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 60)
    print("NUVAFACE SEGMENTATION DEMO")
    print("=" * 60)
    
    # Test with the uploaded image
    test_image = "C:\\Users\\phlpp\\Downloads\\NuvaFace_MVPneu\\0.0ml.png"
    
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
    
    if os.path.exists(test_image):
        test_segmentation_demo(test_image)
    else:
        print(f"Image not found: {test_image}")
        print("Usage: python demo_mode.py <path_to_image>")
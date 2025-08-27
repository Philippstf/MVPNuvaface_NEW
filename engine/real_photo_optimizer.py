"""
Real Photo Optimization Pipeline
Specialized handling for real human photographs vs AI-generated images.
"""

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from typing import Dict, Tuple, Optional
import cv2

from .utils import pil_to_numpy, numpy_to_pil


class RealPhotoProcessor:
    """Specialized processor for real human photographs."""
    
    def __init__(self):
        self.ai_detection_threshold = 0.7  # Threshold for AI vs real photo detection
    
    def detect_photo_type(self, image: Image.Image) -> str:
        """
        Detect if image is AI-generated or real photo.
        
        Args:
            image: Input PIL Image
            
        Returns:
            'real' or 'ai' classification
        """
        # Convert to numpy for analysis
        img_array = pil_to_numpy(image)
        
        # Simple heuristics for AI vs real detection
        # Real photos have more noise, varied skin texture, natural imperfections
        
        # 1. Noise analysis - real photos have more high-frequency noise
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # 2. Skin smoothness analysis (if we can detect face region)
        # Real skin has natural texture variations
        
        # 3. Color distribution analysis
        # AI images often have more saturated, uniform colors
        
        # Simple threshold-based classification for now
        # Higher laplacian variance = more texture/noise = likely real photo
        if laplacian_var > 500:  # Adjust threshold based on testing
            return 'real'
        else:
            return 'ai'
    
    def preprocess_real_photo(self, image: Image.Image) -> Image.Image:
        """
        Preprocess real photo for better diffusion model compatibility.
        
        Args:
            image: Input real photo
            
        Returns:
            Preprocessed image optimized for diffusion
        """
        # 1. Gentle noise reduction while preserving skin texture
        # Use bilateral filter to smooth noise but keep edges
        img_array = pil_to_numpy(image)
        
        # Bilateral filter - reduces noise while preserving edges
        filtered = cv2.bilateralFilter(img_array, 9, 75, 75)
        
        # 2. Subtle contrast enhancement for better model understanding
        enhanced_img = numpy_to_pil(filtered)
        
        # Slight contrast boost
        enhancer = ImageEnhance.Contrast(enhanced_img)
        enhanced_img = enhancer.enhance(1.1)
        
        # 3. Subtle saturation adjustment
        enhancer = ImageEnhance.Color(enhanced_img)
        enhanced_img = enhancer.enhance(1.05)
        
        return enhanced_img
    
    def get_real_photo_sd_params(self, strength: int) -> Dict[str, float]:
        """
        Get SD-Inpainting parameters optimized for real photos.
        
        Args:
            strength: Effect strength 0-100
            
        Returns:
            Optimized parameters for real photos
        """
        s = max(0, min(100, strength))
        
        # COMPLETELY NEW APPROACH: High guidance + low denoising + variable controlnet
        # Philosophy: Strong prompt following, minimal pixel destruction, adaptive structure control
        if s < 30:  # SUBTLE (0-30%): High structure preservation, minimal change
            params = {
                'denoising_strength': 0.08 + 0.003 * s,        # 0.08 - 0.17 (very minimal pixel changes)
                'guidance_scale': 7.0 + 0.1 * s,               # 7.0 - 10.0 (very strong prompt following)
                'controlnet_scale': 0.90 - 0.003 * s,          # 0.90 - 0.81 (very strong structure preservation)
                'mask_feather': 15,                             # Very soft blending
                'num_inference_steps': 35                       # More steps for quality
            }
        elif s < 70:  # MODERATE (30-70%): Balanced but strong guidance
            params = {
                'denoising_strength': 0.18 + 0.004 * (s-30),   # 0.18 - 0.34 (progressive change)
                'guidance_scale': 10.0 + 0.15 * (s-30),        # 10.0 - 16.0 (very strong guidance)
                'controlnet_scale': 0.80 - 0.004 * (s-30),     # 0.80 - 0.64 (decreasing structure)
                'mask_feather': 12,                             # Large feather
                'num_inference_steps': 40                       # High quality
            }
        else:  # ENHANCED (70-100%): Maximum prompt power, minimal structure restriction
            params = {
                'denoising_strength': 0.35 + 0.005 * (s-70),   # 0.35 - 0.50 (strong change)
                'guidance_scale': 16.0 + 0.2 * (s-70),         # 16.0 - 22.0 (extreme guidance)
                'controlnet_scale': 0.60 - 0.005 * (s-70),     # 0.60 - 0.45 (minimal structure restriction)
                'mask_feather': 10,                             # Defined but soft
                'num_inference_steps': 45                       # Maximum quality
            }
        
        return params
    
    def get_real_photo_ip2p_params(self, strength: int) -> Dict[str, float]:
        """
        Get IP2P parameters optimized for real photos.
        
        Args:
            strength: Effect strength 0-100
            
        Returns:
            Optimized IP2P parameters for real photos
        """
        s = max(0, min(100, strength))
        
        # Much more conservative IP2P parameters for real photos
        if s < 30:
            params = {
                'image_guidance_scale': 1.4 + 0.003 * s,       # 1.4 - 1.49 (strong adherence to original)
                'guidance_scale': 5.0 + 0.02 * s,              # 5.0 - 5.6 (gentle text guidance)
                'controlnet_scale': 0.40 - 0.001 * s,          # 0.40 - 0.37 (minimal control interference)
                'strength': 0.15 + 0.002 * s,                  # 0.15 - 0.21 (very conservative)
                'num_inference_steps': 50,                     # High quality
                'mask_feather': 10                              # Very soft blending
            }
        elif s < 70:
            params = {
                'image_guidance_scale': 1.3 + 0.002 * (s-30),  # 1.3 - 1.38 (preserve original)
                'guidance_scale': 5.5 + 0.03 * (s-30),         # 5.5 - 6.7 (moderate text)
                'controlnet_scale': 0.35 - 0.001 * (s-30),     # 0.35 - 0.31 (light control)
                'strength': 0.22 + 0.003 * (s-30),             # 0.22 - 0.34 (moderate)
                'num_inference_steps': 55,                     # Higher quality
                'mask_feather': 8                               # Good blending
            }
        else:
            params = {
                'image_guidance_scale': 1.2 + 0.001 * (s-70),  # 1.2 - 1.23 (balanced)
                'guidance_scale': 6.8 + 0.02 * (s-70),         # 6.8 - 7.4 (stronger text)
                'controlnet_scale': 0.30 - 0.001 * (s-70),     # 0.30 - 0.27 (minimal control)
                'strength': 0.35 + 0.003 * (s-70),             # 0.35 - 0.44 (still conservative)
                'num_inference_steps': 60,                     # Premium quality
                'mask_feather': 6                               # Defined blending
            }
        
        return params
    
    def postprocess_real_photo_result(self, original: Image.Image, 
                                     result: Image.Image, 
                                     mask: Image.Image) -> Image.Image:
        """
        Post-process result for real photos with enhanced blending.
        
        Args:
            original: Original real photo
            result: AI-generated result
            mask: Blending mask
            
        Returns:
            Enhanced blended result
        """
        # Enhanced blending for real photos
        # 1. Create softer mask with multiple feather levels
        mask_array = pil_to_numpy(mask.convert('L')).astype(np.float32) / 255.0
        
        # Apply multiple levels of Gaussian blur for ultra-soft transitions
        soft_mask1 = cv2.GaussianBlur(mask_array, (15, 15), 5.0)
        soft_mask2 = cv2.GaussianBlur(mask_array, (25, 25), 8.0)
        
        # Combine masks for gradient blending
        final_mask = (soft_mask1 * 0.6 + soft_mask2 * 0.4)
        
        # 2. Color matching between generated and original
        orig_array = pil_to_numpy(original).astype(np.float32)
        result_array = pil_to_numpy(result).astype(np.float32)
        
        # Simple color matching in mask region
        mask_3d = np.stack([final_mask] * 3, axis=2)
        
        # Blend with enhanced smoothing
        blended = orig_array * (1 - mask_3d) + result_array * mask_3d
        
        # 3. Final sharpening only in the enhanced region
        blended_pil = numpy_to_pil(blended.astype(np.uint8))
        
        # Subtle sharpening
        sharpener = ImageFilter.UnsharpMask(radius=1, percent=110, threshold=2)
        sharpened = blended_pil.filter(sharpener)
        
        # Apply sharpening only in mask region
        final_mask_pil = numpy_to_pil((final_mask * 255).astype(np.uint8))
        
        # Final blend between sharpened and unsharpened
        from .utils import blend_images_with_mask
        final_result = blend_images_with_mask(blended_pil, sharpened, final_mask_pil)
        
        return final_result


# Global processor instance
_real_photo_processor = None

def get_real_photo_processor() -> RealPhotoProcessor:
    """Get singleton real photo processor."""
    global _real_photo_processor
    if _real_photo_processor is None:
        _real_photo_processor = RealPhotoProcessor()
    return _real_photo_processor
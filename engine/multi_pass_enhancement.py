"""
Multi-pass lip enhancement for professional-grade results.
Combines geometric enhancement with texture refinement.
"""

import torch
import numpy as np
from PIL import Image
from typing import Dict, Tuple, List

from .edit_sd import SDInpaintingEditor
from .parsing import segment_area
from .controls import preprocess_for_inpainting


class MultiPassLipEnhancer:
    """Advanced multi-pass lip enhancement system."""
    
    def __init__(self):
        self.sd_editor = SDInpaintingEditor()
    
    def enhance_lips_multi_pass(self, image: Image.Image, strength: int, 
                               seed: int) -> Tuple[Image.Image, Dict]:
        """
        Multi-pass lip enhancement for professional results.
        
        Args:
            image: Input PIL Image
            strength: Enhancement strength (0-100)
            seed: Random seed
            
        Returns:
            Tuple of (enhanced_image, metadata)
        """
        # Pass 1: Volume enhancement with lower control
        pass1_result, pass1_params = self._pass1_volume_enhancement(
            image, strength, seed
        )
        
        # Pass 2: Texture and definition refinement
        if strength > 50:
            pass2_result, pass2_params = self._pass2_texture_refinement(
                pass1_result, image, strength, seed + 1
            )
            final_result = pass2_result
            final_params = {**pass1_params, 'pass2': pass2_params}
        else:
            final_result = pass1_result
            final_params = pass1_params
        
        return final_result, final_params
    
    def _pass1_volume_enhancement(self, image: Image.Image, strength: int, 
                                 seed: int) -> Tuple[Image.Image, Dict]:
        """First pass: Focus on volume and shape enhancement."""
        
        # Create enhanced mask for volume
        mask_image, _ = segment_area(image, "lips")
        
        # Generate control maps with reduced influence
        control_maps = preprocess_for_inpainting(image)
        
        # Volume-focused prompt
        if strength < 30:
            prompt = "naturally fuller lips, improved shape and volume, soft texture"
        elif strength < 70:
            prompt = "significantly fuller plump lips, enhanced volume and definition, beautiful shape"
        else:
            prompt = "dramatically enhanced lip volume, perfect fullness and shape, professional aesthetic result"
        
        # Modified parameters for volume focus
        params = self.sd_editor.map_slider_to_params(strength)
        params['controlnet_scale'] *= 0.7  # Reduce control for more freedom
        params['denoising_strength'] = min(0.9, params['denoising_strength'] * 1.2)
        
        result, result_params = self.sd_editor.simulate_inpaint(
            image, mask_image, control_maps, strength, seed, prompt,
            num_inference_steps=params.get('num_inference_steps', 45)
        )
        
        return result, {**result_params, 'pass': 'volume_enhancement'}
    
    def _pass2_texture_refinement(self, enhanced_image: Image.Image, 
                                 original_image: Image.Image, strength: int,
                                 seed: int) -> Tuple[Image.Image, Dict]:
        """Second pass: Focus on texture smoothing and final refinement."""
        
        # Create precise mask for texture work
        mask_image, _ = segment_area(enhanced_image, "lips")
        
        # Generate fresh control maps from enhanced image
        control_maps = preprocess_for_inpainting(enhanced_image)
        
        # Texture-focused prompt
        prompt = "ultra-smooth lip texture, perfect skin quality, natural healthy glow, flawless surface, professional finish"
        
        # Conservative parameters for texture refinement
        texture_params = {
            'denoising_strength': 0.35 + 0.002 * strength,  # Conservative
            'guidance_scale': 7.0 + 0.02 * strength,        # Gentle guidance
            'controlnet_scale': 0.65,                        # Preserve structure
            'mask_feather': 5,                               # Soft transitions
            'num_inference_steps': 35                        # Quality focus
        }
        
        result, result_params = self.sd_editor.simulate_inpaint(
            enhanced_image, mask_image, control_maps, 
            min(60, strength), seed, prompt,  # Cap strength for refinement
            num_inference_steps=texture_params['num_inference_steps']
        )
        
        return result, {**result_params, 'pass': 'texture_refinement'}


# Integration function for API
def enhance_lips_professional(image: Image.Image, strength: int, 
                            seed: int) -> Tuple[Image.Image, Dict]:
    """
    Professional-grade lip enhancement using multi-pass approach.
    
    Args:
        image: Input PIL Image
        strength: Enhancement strength (0-100)
        seed: Random seed
        
    Returns:
        Tuple of (enhanced_image, parameters)
    """
    if strength > 60:  # Use multi-pass for high strength
        enhancer = MultiPassLipEnhancer()
        return enhancer.enhance_lips_multi_pass(image, strength, seed)
    else:  # Use standard single-pass for lower strength
        from .edit_sd import simulate_sd_inpaint
        from .controls import preprocess_for_inpainting
        
        mask_image, _ = segment_area(image, "lips")
        control_maps = preprocess_for_inpainting(image)
        
        # Use adaptive prompts
        from api.schemas import get_adaptive_prompt_for_area, AreaType
        prompt = get_adaptive_prompt_for_area(AreaType.LIPS, strength)
        
        return simulate_sd_inpaint(image, mask_image, control_maps, 
                                 strength, seed, prompt)
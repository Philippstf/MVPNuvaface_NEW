"""
InstructPix2Pix editing with ControlNet guidance as alternative to SD inpainting.
Provides instruction-based image editing with masked blending for localized changes.
"""

import time
import torch
import numpy as np
from PIL import Image
from typing import Dict, Tuple, Optional
from diffusers import StableDiffusionInstructPix2PixPipeline, ControlNetModel

from .utils import set_seed, pil_to_numpy, numpy_to_pil, blend_images_with_mask
from .controls import preprocess_for_ip2p
from models import get_device


class IP2PEditor:
    """InstructPix2Pix editor with ControlNet guidance."""
    
    def __init__(self):
        self._pipeline = None
        self._controlnets = None
        self.device = get_device()
    
    def get_pipeline(self) -> StableDiffusionInstructPix2PixPipeline:
        """Load and cache the InstructPix2Pix pipeline with ControlNets."""
        if self._pipeline is None:
            # Load ControlNet models optimized for IP2P
            canny_controlnet = ControlNetModel.from_pretrained(
                "lllyasviel/sd-controlnet-canny",
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32
            )
            depth_controlnet = ControlNetModel.from_pretrained(
                "lllyasviel/sd-controlnet-depth",
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32
            )
            
            self._controlnets = [canny_controlnet, depth_controlnet]
            
            # Load InstructPix2Pix pipeline with ControlNets
            self._pipeline = StableDiffusionInstructPix2PixPipeline.from_pretrained(
                "timbrooks/instruct-pix2pix",
                controlnet=self._controlnets,
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
                safety_checker=None,
                requires_safety_checker=False
            )
            
            self._pipeline = self._pipeline.to(self.device)
            
            # Enable optimizations
            if self.device.type == "cuda":
                try:
                    self._pipeline.enable_xformers_memory_efficient_attention()
                except ImportError:
                    print("Warning: xformers not available for IP2P")
                
                if hasattr(self._pipeline, "enable_model_cpu_offload"):
                    self._pipeline.enable_model_cpu_offload()
        
        return self._pipeline
    
    def map_slider_to_params(self, strength: int) -> Dict[str, float]:
        """
        Map slider value (0-100) to IP2P parameters.
        Uses same mapping as SD inpainting for consistency.
        
        Args:
            strength: Slider value 0-100
            
        Returns:
            Dictionary with mapped parameters
        """
        s = max(0, min(100, strength))  # Clamp to valid range
        
        # Optimized IP2P parameters for natural lip enhancement
        if s < 30:  # Subtle (0-30%)
            params = {
                'image_guidance_scale': 1.0 + 0.007 * s,       # 1.0 - 1.21 (gentle from original)
                'guidance_scale': 6.0 + 0.03 * s,              # 6.0 - 6.9 (gentle text guidance)
                'controlnet_scale': 0.20 - 0.001 * s,          # 0.20 - 0.17 (minimal restriction)
                'strength': 0.25 + 0.003 * s,                  # 0.25 - 0.34 (conservative change)
                'num_inference_steps': 35,                     # Quality steps
                'mask_feather': 6                               # Soft blending
            }
        elif s < 70:  # Moderate (30-70%)
            params = {
                'image_guidance_scale': 0.9 + 0.005 * (s-30),  # 0.9 - 1.1 (balanced)
                'guidance_scale': 7.0 + 0.05 * (s-30),         # 7.0 - 9.0 (stronger text)
                'controlnet_scale': 0.15 - 0.002 * (s-30),     # 0.15 - 0.07 (less control)
                'strength': 0.35 + 0.006 * (s-30),             # 0.35 - 0.59 (more change)
                'num_inference_steps': 40,                     # Higher quality
                'mask_feather': 5                               # Defined blending
            }
        else:  # Strong (70-100%)
            params = {
                'image_guidance_scale': 0.7 + 0.003 * (s-70),  # 0.7 - 0.79 (more creative freedom)
                'guidance_scale': 9.0 + 0.07 * (s-70),         # 9.0 - 11.1 (strong text guidance)
                'controlnet_scale': max(0.02, 0.06 - 0.001 * (s-70)), # 0.06 - 0.02 (minimal control)
                'strength': 0.60 + 0.008 * (s-70),             # 0.60 - 0.84 (dramatic change)
                'num_inference_steps': 45,                     # Premium quality
                'mask_feather': 4                               # Sharp definition
            }
        
        return params
    
    def create_instruction_prompt(self, base_prompt: str, area: str, strength: int = 50) -> str:
        """
        Create optimized instruction prompts for IP2P based on area and strength.
        
        Args:
            base_prompt: Base prompt for the area
            area: Facial area being edited
            strength: Enhancement strength (0-100)
            
        Returns:
            Optimized instruction-formatted prompt
        """
        if area == 'lips':
            if strength < 30:
                return "Make the lips slightly fuller and more defined with natural texture"
            elif strength < 70:
                return "Transform the lips to be noticeably fuller, plumper, and beautifully shaped with smooth texture"
            else:
                return "Dramatically enhance the lips to be very full, perfectly sculpted, and voluminous with ultra-smooth professional quality"
        
        elif area == 'chin':
            if strength < 30:
                return f"Subtly enhance the chin to be {base_prompt}"
            elif strength < 70:
                return f"Improve the chin projection and definition to be {base_prompt}"
            else:
                return f"Dramatically enhance the chin structure to be {base_prompt}"
        
        elif area == 'cheeks':
            if strength < 30:
                return f"Gently enhance the cheeks to have {base_prompt}"
            elif strength < 70:
                return f"Improve the cheek volume and contour to have {base_prompt}"
            else:
                return f"Dramatically enhance the cheek structure to have {base_prompt}"
        
        elif area == 'forehead':
            if strength < 30:
                return f"Smooth the forehead lines to be {base_prompt}"
            elif strength < 70:
                return f"Significantly reduce forehead wrinkles to be {base_prompt}"
            else:
                return f"Completely eliminate all forehead lines to be {base_prompt}"
        
        return f"Edit the {area} to be {base_prompt}"
    
    def masked_blend(self, original: Image.Image, edited: Image.Image, 
                    mask: Image.Image) -> Image.Image:
        """
        Blend edited image with original using mask to preserve off-target areas.
        
        Args:
            original: Original input image
            edited: Edited image from IP2P
            mask: Area mask for blending
            
        Returns:
            Masked blend result
        """
        # Ensure mask is grayscale
        if mask.mode != 'L':
            mask = mask.convert('L')
        
        # Apply feathering to mask for smoother blending
        mask_array = pil_to_numpy(mask).astype(np.float32) / 255.0
        
        # Optional: Apply Gaussian blur for softer edges
        import cv2
        kernel_size = 5
        blurred_mask = cv2.GaussianBlur(mask_array, (kernel_size, kernel_size), 2.0)
        blurred_mask_pil = numpy_to_pil((blurred_mask * 255).astype(np.uint8))
        
        # Blend using the feathered mask
        result = blend_images_with_mask(original, edited, blurred_mask_pil)
        
        return result
    
    def simulate_ip2p(self, image: Image.Image, mask: Image.Image,
                     control_maps: Dict[str, Image.Image], strength: int,
                     seed: int, prompt: str, area: str = None,
                     num_inference_steps: int = 28) -> Tuple[Image.Image, Dict]:
        """
        Perform IP2P editing with ControlNet guidance and masked blending.
        
        Args:
            image: Input PIL Image
            mask: Area mask for blending (not directly used by IP2P)
            control_maps: Dictionary with 'softedge' and 'depth' control images
            strength: Slider value (0-100)
            seed: Random seed for reproducibility
            prompt: Base text prompt for conditioning
            area: Facial area being edited (for instruction formatting)
            num_inference_steps: Number of diffusion steps
            
        Returns:
            Tuple of (result_image, parameters_dict)
        """
        start_time = time.time()
        
        # Set seed for reproducibility
        set_seed(seed)
        
        # Get pipeline
        pipeline = self.get_pipeline()
        
        # Map slider to parameters
        params = self.map_slider_to_params(strength)
        
        # Create optimized instruction prompt with strength awareness
        instruction = self.create_instruction_prompt(prompt, area, strength) if area else prompt
        
        # Prepare control images (using canny instead of softedge)
        control_images = [control_maps['canny'], control_maps['depth']]
        controlnet_scales = [params['controlnet_scale']] * len(control_images)
        
        # Run IP2P inference
        with torch.no_grad():
            result = pipeline(
                prompt=instruction,
                image=image,
                control_image=control_images,
                controlnet_conditioning_scale=controlnet_scales,
                image_guidance_scale=params['image_guidance_scale'],
                guidance_scale=params['guidance_scale'],
                num_inference_steps=params.get('num_inference_steps', num_inference_steps),
                generator=torch.Generator(device=self.device).manual_seed(seed),
                return_dict=True
            )
        
        edited_image = result.images[0]
        
        # Apply masked blending to preserve off-target areas
        final_image = self.masked_blend(image, edited_image, mask)
        
        end_time = time.time()
        
        # Return parameters and timing info
        output_params = {
            # Required API fields
            'denoising_strength': params.get('strength', 0.5),  # Map IP2P strength to API expected field
            'guidance_scale': params['guidance_scale'],
            'controlnet_scale': params['controlnet_scale'],
            'mask_feather': params['mask_feather'],
            'seed': seed,
            'prompt': instruction,  # Use the generated instruction
            'negative_prompt': "artificial, fake, plastic, oversaturated, blurry, low quality",
            'num_inference_steps': params.get('num_inference_steps', num_inference_steps),
            'inference_time_ms': int((end_time - start_time) * 1000),
            # IP2P specific fields
            'image_guidance_scale': params['image_guidance_scale'],
            'original_prompt': prompt,
            'instruction': instruction,
            'area': area,
            **params  # Include all other params
        }
        
        return final_image, output_params
    
    def simulate_ip2p_with_params(self, image: Image.Image, mask: Image.Image,
                                 control_maps: Dict[str, Image.Image], strength: int,
                                 seed: int, prompt: str, area: str = None,
                                 custom_params: Dict[str, float] = None,
                                 num_inference_steps: int = 28) -> Tuple[Image.Image, Dict]:
        """
        IP2P simulation with custom parameter override (for real photo optimization).
        
        Args:
            image: Input PIL Image
            mask: Area mask for blending
            control_maps: Control maps
            strength: Slider value (0-100)
            seed: Random seed
            prompt: Text prompt
            area: Facial area
            custom_params: Custom parameters to override defaults
            num_inference_steps: Number of steps
            
        Returns:
            Tuple of (result_image, parameters_dict)
        """
        start_time = time.time()
        
        # Set seed for reproducibility
        set_seed(seed)
        
        # Get pipeline
        pipeline = self.get_pipeline()
        
        # Use custom parameters if provided, otherwise use standard mapping
        if custom_params:
            params = custom_params
        else:
            params = self.map_slider_to_params(strength)
        
        # Create optimized instruction prompt with strength awareness
        instruction = self.create_instruction_prompt(prompt, area, strength) if area else prompt
        
        # Prepare control images (using canny instead of softedge)
        control_images = [control_maps['canny'], control_maps['depth']]
        controlnet_scales = [params['controlnet_scale']] * len(control_images)
        
        # Run IP2P inference with custom parameters
        with torch.no_grad():
            result = pipeline(
                prompt=instruction,
                image=image,
                control_image=control_images,
                controlnet_conditioning_scale=controlnet_scales,
                image_guidance_scale=params['image_guidance_scale'],
                guidance_scale=params['guidance_scale'],
                num_inference_steps=params.get('num_inference_steps', num_inference_steps),
                generator=torch.Generator(device=self.device).manual_seed(seed),
                return_dict=True
            )
        
        edited_image = result.images[0]
        
        # Apply masked blending to preserve off-target areas
        final_image = self.masked_blend(image, edited_image, mask)
        
        end_time = time.time()
        
        # Return parameters and timing info with custom params
        output_params = {
            # Required API fields
            'denoising_strength': params.get('strength', 0.5),
            'guidance_scale': params['guidance_scale'],
            'controlnet_scale': params['controlnet_scale'],
            'mask_feather': params['mask_feather'],
            'seed': seed,
            'prompt': instruction,
            'negative_prompt': "artificial, fake, plastic, oversaturated, blurry, low quality",
            'num_inference_steps': params.get('num_inference_steps', num_inference_steps),
            'inference_time_ms': int((end_time - start_time) * 1000),
            # IP2P specific fields
            'image_guidance_scale': params['image_guidance_scale'],
            'original_prompt': prompt,
            'instruction': instruction,
            'area': area,
            'photo_optimized': True,  # Flag for real photo optimization
            **params
        }
        
        return final_image, output_params


# Global editor instance
_ip2p_editor = None

def get_ip2p_editor() -> IP2PEditor:
    """Get singleton IP2P editor instance."""
    global _ip2p_editor
    if _ip2p_editor is None:
        _ip2p_editor = IP2PEditor()
    return _ip2p_editor


def simulate_ip2p(image: Image.Image, mask: Image.Image,
                 control_maps: Dict[str, Image.Image], strength: int,
                 seed: int, prompt: str, area: str = None) -> Tuple[Image.Image, Dict]:
    """
    Convenience function for IP2P simulation.
    This is the main entry point used by the API.
    
    Args:
        image: Input PIL Image
        mask: Area mask for blending
        control_maps: Control maps from controls.py (softedge, depth)
        strength: Slider value (0-100)
        seed: Random seed
        prompt: Text prompt
        area: Facial area for instruction formatting
        
    Returns:
        Tuple of (result_image, parameters_dict)
    """
    editor = get_ip2p_editor()
    return editor.simulate_ip2p(image, mask, control_maps, strength, seed, prompt, area)


def validate_ip2p_inputs(image: Image.Image, mask: Image.Image,
                        control_maps: Dict[str, Image.Image]) -> bool:
    """
    Validate inputs for IP2P editing.
    
    Args:
        image: Input image
        mask: Mask image
        control_maps: Control maps
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    # Check image sizes match
    if image.size != mask.size:
        raise ValueError(f"Image size {image.size} doesn't match mask size {mask.size}")
    
    # Check required control maps for IP2P
    required_controls = ['softedge', 'depth']
    for control in required_controls:
        if control not in control_maps:
            raise ValueError(f"Missing required control map for IP2P: {control}")
        
        if control_maps[control].size != image.size:
            raise ValueError(f"Control map '{control}' size doesn't match image size")
    
    return True


def get_instruction_examples() -> Dict[str, Dict[str, str]]:
    """
    Get example instructions for different areas and languages.
    Used for prompt template development and testing.
    """
    return {
        'lips': {
            'en': 'Make the lips slightly fuller and smoother',
            'de': 'Mache die Lippen etwas voller und glatter'
        },
        'chin': {
            'en': 'Enhance the chin projection subtly',
            'de': 'Verbessere die Kinnprojektion dezent'
        },
        'cheeks': {
            'en': 'Add subtle volume to the cheek area',
            'de': 'Füge subtiles Volumen zum Wangenbereich hinzu'
        },
        'forehead': {
            'en': 'Smooth the forehead wrinkles naturally',
            'de': 'Glätte die Stirnfalten natürlich'
        }
    }


def compare_with_inpainting(image: Image.Image, mask: Image.Image,
                           prompt: str, strength: int, seed: int) -> Dict[str, Image.Image]:
    """
    Compare IP2P and SD inpainting results side by side.
    Useful for evaluation and method selection.
    
    Args:
        image: Input image
        mask: Area mask
        prompt: Text prompt
        strength: Slider value
        seed: Random seed
        
    Returns:
        Dictionary with both results
    """
    from .edit_sd import simulate_sd_inpaint
    from .controls import preprocess_for_inpainting, preprocess_for_ip2p
    
    # Generate appropriate control maps for each method
    sd_controls = preprocess_for_inpainting(image)
    ip2p_controls = preprocess_for_ip2p(image)
    
    # Run both methods
    sd_result, sd_params = simulate_sd_inpaint(image, mask, sd_controls, strength, seed, prompt)
    ip2p_result, ip2p_params = simulate_ip2p(image, mask, ip2p_controls, strength, seed, prompt)
    
    return {
        'sd_inpainting': sd_result,
        'instruct_pix2pix': ip2p_result,
        'sd_params': sd_params,
        'ip2p_params': ip2p_params
    }


def adaptive_method_selection(image: Image.Image, mask: Image.Image, 
                             area: str) -> str:
    """
    Automatically select between SD inpainting and IP2P based on area and image characteristics.
    This is a heuristic that can be refined based on evaluation results.
    
    Args:
        image: Input image
        mask: Area mask
        area: Facial area
        
    Returns:
        Recommended method: 'sd_inpaint' or 'ip2p'
    """
    # Calculate mask properties
    mask_array = pil_to_numpy(mask.convert('L'))
    mask_coverage = np.sum(mask_array > 0) / mask_array.size
    
    # Heuristic rules (can be refined with evaluation data)
    if area == 'forehead':
        # Forehead wrinkles: prefer inpainting for texture preservation
        return 'sd_inpaint'
    elif area == 'lips' and mask_coverage < 0.05:
        # Small lip adjustments: IP2P might be gentler
        return 'ip2p'
    elif mask_coverage > 0.15:
        # Large areas: inpainting typically more stable
        return 'sd_inpaint'
    else:
        # Default to inpainting
        return 'sd_inpaint'
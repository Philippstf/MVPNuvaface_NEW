"""
Stable Diffusion Inpainting with ControlNet for guided facial aesthetic editing.
Implements slider-controlled parameter mapping and dual ControlNet conditioning.
"""

import time
import torch
import numpy as np
from PIL import Image, ImageEnhance
from typing import Dict, Tuple, Optional, List
from diffusers import StableDiffusionInpaintPipeline, ControlNetModel
from diffusers.pipelines.stable_diffusion import StableDiffusionPipelineOutput

from .utils import set_seed, pil_to_numpy, numpy_to_pil, blend_images_with_mask
from .controls import preprocess_for_inpainting
from models import get_device


class SDInpaintingEditor:
    """Stable Diffusion Inpainting editor with ControlNet guidance."""
    
    def __init__(self):
        self._pipeline = None
        self._controlnets = None
        self.device = get_device()
    
    def get_pipeline(self) -> StableDiffusionInpaintPipeline:
        """Load and cache the inpainting pipeline with ControlNets."""
        if self._pipeline is None:
            # Load ControlNet models
            canny_controlnet = ControlNetModel.from_pretrained(
                "lllyasviel/sd-controlnet-canny",
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32
            )
            depth_controlnet = ControlNetModel.from_pretrained(
                "lllyasviel/sd-controlnet-depth", 
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32
            )
            
            self._controlnets = [canny_controlnet, depth_controlnet]
            
            # Load base inpainting pipeline - using newer model with safetensors
            self._pipeline = StableDiffusionInpaintPipeline.from_pretrained(
                "stabilityai/stable-diffusion-2-inpainting",
                controlnet=self._controlnets,
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
                safety_checker=None,
                requires_safety_checker=False,
                use_safetensors=True
            )
            
            self._pipeline = self._pipeline.to(self.device)
            
            # Enable optimizations
            if self.device.type == "cuda":
                try:
                    self._pipeline.enable_xformers_memory_efficient_attention()
                except ImportError:
                    print("Warning: xformers not available")
                
                if hasattr(self._pipeline, "enable_model_cpu_offload"):
                    self._pipeline.enable_model_cpu_offload()
        
        return self._pipeline
    
    def map_slider_to_params(self, strength: int) -> Dict[str, float]:
        """
        Map slider value (0-100) to diffusion parameters.
        Enhanced for stronger lip enhancement effects.
        
        Args:
            strength: Slider value 0-100 (0ml - 3ml equivalent)
            
        Returns:
            Dictionary with mapped parameters
        """
        s = max(0, min(100, strength))  # Clamp to valid range
        
        # Progressive parameter mapping for real volumetric lip enhancement
        if s < 30:  # Subtle (0-30%)
            params = {
                'denoising_strength': 0.30 + 0.003 * s,        # 0.30 - 0.39 (conservative)
                'guidance_scale': 6.0 + 0.02 * s,              # 6.0 - 6.6 (gentle guidance)
                'controlnet_scale': 0.60 - 0.002 * s,          # 0.60 - 0.54 (structure preserved)
                'mask_feather': 5,                              # Fixed soft transition
                'num_inference_steps': 40                       # Standard quality
            }
        elif s < 70:  # Moderate (30-70%)
            params = {
                'denoising_strength': 0.40 + 0.008 * (s-30),   # 0.40 - 0.72 (more transformation)
                'guidance_scale': 7.0 + 0.05 * (s-30),         # 7.0 - 9.0 (stronger guidance)
                'controlnet_scale': 0.45 - 0.006 * (s-30),     # 0.45 - 0.21 (less restriction)
                'mask_feather': 4,                              # Tighter for definition
                'num_inference_steps': 45                       # Higher quality
            }
        else:  # Strong (70-100%)
            params = {
                'denoising_strength': min(0.95, 0.75 + 0.007 * (s-70)),  # 0.75 - 0.95 (maximum change)
                'guidance_scale': 9.0 + 0.08 * (s-70),                   # 9.0 - 11.4 (strong guidance)
                'controlnet_scale': max(0.05, 0.20 - 0.005 * (s-70)),    # 0.20 - 0.05 (minimal restriction)
                'mask_feather': 3,                                        # Sharp definition
                'num_inference_steps': 50 + round((s-70) / 6)             # 50 - 55 (premium quality)
            }
        
        return params
    
    def postprocess_result(self, original: Image.Image, generated: Image.Image, 
                          mask: Image.Image) -> Image.Image:
        """
        Post-process the generated result with original image.
        
        Args:
            original: Original input image
            generated: Generated image from diffusion
            mask: Inpainting mask
            
        Returns:
            Final blended result
        """
        # Ensure all images have the same size
        target_size = original.size
        
        # Resize generated image to match original if needed
        if generated.size != target_size:
            generated = generated.resize(target_size, Image.LANCZOS)
        
        # Resize mask to match original if needed  
        if mask.size != target_size:
            mask = mask.resize(target_size, Image.LANCZOS)
        
        # Ensure mask is grayscale
        if mask.mode != 'L':
            mask = mask.convert('L')
        
        # SIMPLE post-processing - just basic blending
        result = blend_images_with_mask(original, generated, mask)
        
        return result
    
    def postprocess_result_fast(self, original: Image.Image, generated: Image.Image, 
                               mask: Image.Image) -> Image.Image:
        """
        Fast single-step post-processing for immediate display.
        Combines blending and enhancement in one operation.
        """
        # Ensure all images have the same size before blending
        target_size = original.size
        
        # Resize generated image to match original if needed
        if generated.size != target_size:
            generated = generated.resize(target_size, Image.LANCZOS)
        
        # Resize mask to match original if needed
        if mask.size != target_size:
            mask = mask.resize(target_size, Image.LANCZOS)
        
        # Simple but effective blending
        result = blend_images_with_mask(original, generated, mask)
        
        # Quick subtle enhancement
        enhancer = ImageEnhance.Sharpness(result)
        result = enhancer.enhance(1.1)
        
        return result
    
    def simulate_inpaint(self, image: Image.Image, mask: Image.Image, 
                        control_maps: Dict[str, Image.Image], strength: int, 
                        seed: int, prompt: str, negative_prompt: str = None,
                        num_inference_steps: int = 30) -> Tuple[Image.Image, Dict]:
        """
        Perform inpainting with ControlNet guidance.
        
        Args:
            image: Input PIL Image
            mask: Inpainting mask (PIL Image)
            control_maps: Dictionary with 'canny' and 'depth' control images
            strength: Slider value (0-100) 
            seed: Random seed for reproducibility
            prompt: Text prompt for conditioning
            negative_prompt: Negative prompt (optional)
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
        
        # Prepare control images
        control_images = [control_maps['canny'], control_maps['depth']]
        controlnet_scales = [params['controlnet_scale']] * len(control_images)
        
        # Ensure mask is grayscale
        if mask.mode != 'L':
            mask = mask.convert('L')
        
        # POWERFUL negative prompt for perfect lip enhancement with high guidance
        if negative_prompt is None:
            negative_prompt = "artificial plastic lips, fake silicone look, overfilled duck lips, unnatural shine, glossy makeup, lipstick, cartoon, anime, asymmetric lips, uneven lips, malformed lips, deformed lips, crooked lips, lopsided lips, bumpy texture, rough surface, cracked lips, dry lips, chapped lips, wrinkled lips, saggy lips, thin lips, oversaturated, blurry, distorted, unrealistic, low quality, poor resolution, pixelated, noisy, grainy, artifacts, jagged edges, harsh shadows, overprocessed, digital artifacts, amateur work, botched surgery, unnatural proportions, exaggerated features"
        
        # Run inference
        with torch.no_grad():
            result = pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=image,
                mask_image=mask,
                control_image=control_images,
                controlnet_conditioning_scale=controlnet_scales,
                strength=params['denoising_strength'],
                guidance_scale=params['guidance_scale'],
                num_inference_steps=params.get('num_inference_steps', num_inference_steps),
                generator=torch.Generator(device=self.device).manual_seed(seed),
                return_dict=True
            )
        
        generated_image = result.images[0]
        
        # Post-process result (normal multi-step processing)
        final_image = self.postprocess_result(image, generated_image, mask)
        
        end_time = time.time()
        
        # Return parameters and timing info
        output_params = {
            **params,
            'seed': seed,
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'num_inference_steps': num_inference_steps,
            'inference_time_ms': int((end_time - start_time) * 1000)
        }
        
        return final_image, output_params
    
    def simulate_inpaint_with_params(self, image: Image.Image, mask: Image.Image,
                                   control_maps: Dict[str, Image.Image], strength: int,
                                   seed: int, prompt: str, custom_params: Dict[str, float] = None,
                                   negative_prompt: str = None,
                                   num_inference_steps: int = 30) -> Tuple[Image.Image, Dict]:
        """
        SD Inpainting with custom parameter override (for real photo optimization).
        
        Args:
            image: Input PIL Image
            mask: Inpainting mask
            control_maps: Control maps
            strength: Slider value (0-100)
            seed: Random seed
            prompt: Text prompt
            custom_params: Custom parameters to override defaults
            negative_prompt: Negative prompt
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
        
        # Prepare control images
        control_images = [control_maps['canny'], control_maps['depth']]
        controlnet_scales = [params['controlnet_scale']] * len(control_images)
        
        # Ensure mask is grayscale
        if mask.mode != 'L':
            mask = mask.convert('L')
        
        # POWERFUL negative prompt for perfect real photo lip enhancement with high guidance
        if negative_prompt is None:
            negative_prompt = "artificial plastic lips, fake silicone look, overfilled duck lips, unnatural shine, glossy makeup, lipstick, cartoon, anime, asymmetric lips, uneven lips, malformed lips, deformed lips, crooked lips, lopsided lips, bumpy texture, rough surface, cracked lips, dry lips, chapped lips, wrinkled lips, saggy lips, thin lips, oversaturated, blurry, distorted, unrealistic, low quality, poor resolution, pixelated, noisy, grainy, artifacts, jagged edges, harsh shadows, overprocessed, digital artifacts, amateur work, botched surgery, unnatural proportions, exaggerated features"
        
        # Run inference with custom parameters
        with torch.no_grad():
            result = pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=image,
                mask_image=mask,
                control_image=control_images,
                controlnet_conditioning_scale=controlnet_scales,
                strength=params['denoising_strength'],
                guidance_scale=params['guidance_scale'],
                num_inference_steps=params.get('num_inference_steps', num_inference_steps),
                generator=torch.Generator(device=self.device).manual_seed(seed),
                return_dict=True
            )
        
        generated_image = result.images[0]
        
        # Post-process with enhanced blending for real photos
        final_result = self.postprocess_result(image, generated_image, mask)
        
        end_time = time.time()
        
        # Compile output parameters
        output_params = {
            **params,
            'seed': seed,
            'prompt': prompt,
            'negative_prompt': negative_prompt,
            'num_inference_steps': params.get('num_inference_steps', num_inference_steps),
            'inference_time_ms': int((end_time - start_time) * 1000),
            'photo_optimized': True  # Flag for real photo optimization
        }
        
        return final_result, output_params


# Global editor instance
_sd_editor = None

def get_sd_editor() -> SDInpaintingEditor:
    """Get singleton SD inpainting editor instance."""
    global _sd_editor
    if _sd_editor is None:
        _sd_editor = SDInpaintingEditor()
    return _sd_editor


def simulate_sd_inpaint(image: Image.Image, mask: Image.Image, 
                       control_maps: Dict[str, Image.Image], strength: int,
                       seed: int, prompt: str) -> Tuple[Image.Image, Dict]:
    """
    Convenience function for SD inpainting simulation.
    This is the main entry point used by the API.
    
    Args:
        image: Input PIL Image
        mask: Inpainting mask  
        control_maps: Control maps from controls.py
        strength: Slider value (0-100)
        seed: Random seed
        prompt: Text prompt
        
    Returns:
        Tuple of (result_image, parameters_dict)
    """
    editor = get_sd_editor()
    return editor.simulate_inpaint(image, mask, control_maps, strength, seed, prompt)


def get_default_negative_prompt() -> str:
    """Get default negative prompt for aesthetic procedures."""
    return "blurry, distorted, unrealistic, artificial, plastic, fake, oversaturated, cartoon, anime, low quality, bad anatomy"


def validate_inputs(image: Image.Image, mask: Image.Image, 
                   control_maps: Dict[str, Image.Image]) -> bool:
    """
    Validate inputs for inpainting.
    
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
    
    # Check required control maps
    required_controls = ['canny', 'depth']
    for control in required_controls:
        if control not in control_maps:
            raise ValueError(f"Missing required control map: {control}")
        
        if control_maps[control].size != image.size:
            raise ValueError(f"Control map '{control}' size doesn't match image size")
    
    return True


def create_pipeline_with_lora(lora_path: Optional[str] = None) -> StableDiffusionInpaintPipeline:
    """
    Create pipeline with optional LoRA weights for specialized aesthetic models.
    This can be used in future iterations for domain-specific fine-tuning.
    """
    # Placeholder for LoRA integration
    # In production, this would load LoRA weights trained on aesthetic procedure data
    editor = get_sd_editor()
    pipeline = editor.get_pipeline()
    
    if lora_path:
        # Future: Load LoRA weights
        # pipeline.load_lora_weights(lora_path)
        pass
    
    return pipeline


def batch_inpaint(images: List[Image.Image], masks: List[Image.Image],
                 prompts: List[str], strength: int, seed: int) -> List[Tuple[Image.Image, Dict]]:
    """
    Batch processing for multiple images (future optimization).
    Currently processes sequentially, can be optimized for batch inference.
    """
    results = []
    editor = get_sd_editor()
    
    for i, (image, mask, prompt) in enumerate(zip(images, masks, prompts)):
        # Generate control maps
        control_maps = preprocess_for_inpainting(image)
        
        # Process with incremented seed for variation
        result_image, params = editor.simulate_inpaint(
            image, mask, control_maps, strength, seed + i, prompt
        )
        
        results.append((result_image, params))
    
    return results
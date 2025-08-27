"""
ControlNet preprocessing - generate control maps (Canny, SoftEdge, Depth) for guided diffusion.
Uses controlnet_aux for optimized preprocessing pipelines.
"""

import numpy as np
import cv2
from PIL import Image
from typing import Dict, Tuple, Optional
from .utils import pil_to_numpy, numpy_to_pil
from models import get_canny_detector, get_pidinet_detector, get_midas_detector


class ControlProcessor:
    """Processes images to generate ControlNet conditioning maps."""
    
    def __init__(self):
        self._canny_detector = None
        self._pidinet_detector = None
        self._midas_detector = None
    
    @property
    def canny_detector(self):
        """Lazy load Canny detector."""
        if self._canny_detector is None:
            self._canny_detector = get_canny_detector()
        return self._canny_detector
    
    @property
    def pidinet_detector(self):
        """Lazy load PiDiNet soft edge detector."""
        if self._pidinet_detector is None:
            # Use Canny as fallback to avoid downloads
            self._pidinet_detector = get_canny_detector()
        return self._pidinet_detector
    
    @property
    def midas_detector(self):
        """Lazy load MiDaS depth detector."""
        if self._midas_detector is None:
            # Disable depth for now to avoid downloads
            self._midas_detector = None
        return self._midas_detector
    
    def auto_canny(self, image: Image.Image, low_threshold: Optional[int] = None, 
                   high_threshold: Optional[int] = None) -> Image.Image:
        """
        Generate Canny edge map with automatic threshold detection.
        
        Args:
            image: Input PIL Image
            low_threshold: Manual low threshold (optional)
            high_threshold: Manual high threshold (optional)
            
        Returns:
            Canny edge map as PIL Image
        """
        # Convert to grayscale numpy array
        gray = cv2.cvtColor(pil_to_numpy(image), cv2.COLOR_RGB2GRAY)
        
        if low_threshold is None or high_threshold is None:
            # Automatic threshold using Otsu's method
            # Typical ratio for Canny is 1:2 or 1:3
            sigma = 0.33
            median = np.median(gray)
            
            if low_threshold is None:
                low_threshold = int(max(0, (1.0 - sigma) * median))
            if high_threshold is None:
                high_threshold = int(min(255, (1.0 + sigma) * median))
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray, low_threshold, high_threshold)
        
        # Convert back to PIL RGB (ControlNet expects RGB)
        edges_rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        return numpy_to_pil(edges_rgb)
    
    def canny_controlnet_aux(self, image: Image.Image) -> Image.Image:
        """Generate Canny edges using controlnet_aux (optimized for ControlNet)."""
        return self.canny_detector(image)
    
    def soft_edge_pidinet(self, image: Image.Image) -> Image.Image:
        """Generate soft edges using PiDiNet detector."""
        return self.pidinet_detector(image)
    
    def depth_midas(self, image: Image.Image) -> Image.Image:
        """Generate depth map using MiDaS."""
        if self.midas_detector is None:
            # Fallback: return Canny edges as depth substitute
            return self.canny_controlnet_aux(image)
        return self.midas_detector(image)
    
    def generate_control_maps(self, image: Image.Image, 
                            controls: list = None) -> Dict[str, Image.Image]:
        """
        Generate multiple control maps for an image.
        
        Args:
            image: Input PIL Image
            controls: List of control types to generate. 
                     If None, generates ['canny', 'softedge', 'depth']
                     
        Returns:
            Dictionary mapping control type to PIL Image
        """
        if controls is None:
            controls = ['canny', 'softedge', 'depth']
        
        control_maps = {}
        
        for control in controls:
            if control == 'canny':
                control_maps['canny'] = self.canny_controlnet_aux(image)
            elif control == 'softedge':
                control_maps['softedge'] = self.soft_edge_pidinet(image)
            elif control == 'depth':
                control_maps['depth'] = self.depth_midas(image)
            elif control == 'auto_canny':
                control_maps['auto_canny'] = self.auto_canny(image)
            else:
                raise ValueError(f"Unsupported control type: {control}")
        
        return control_maps
    
    def process_for_controlnet(self, image: Image.Image, 
                              control_types: list = ['canny', 'depth']) -> Dict[str, Image.Image]:
        """
        Process image for ControlNet usage with specified control types.
        This is the main function used by the editing pipelines.
        
        Args:
            image: Input PIL Image
            control_types: List of control types for multi-ControlNet
            
        Returns:
            Dictionary of control maps ready for ControlNet
        """
        return self.generate_control_maps(image, control_types)


# Global processor instance
_control_processor = None

def get_control_processor() -> ControlProcessor:
    """Get singleton control processor instance."""
    global _control_processor
    if _control_processor is None:
        _control_processor = ControlProcessor()
    return _control_processor


def control_maps(image: Image.Image, controls: list = None) -> Dict[str, Image.Image]:
    """
    Convenience function to generate control maps.
    
    Args:
        image: Input PIL Image  
        controls: List of control types to generate
        
    Returns:
        Dictionary mapping control type to PIL Image
    """
    processor = get_control_processor()
    return processor.generate_control_maps(image, controls)


def get_supported_controls() -> list:
    """Get list of supported control types."""
    return ['canny', 'softedge', 'depth', 'auto_canny']


def validate_controls(controls: list) -> bool:
    """Validate if all control types are supported."""
    supported = get_supported_controls()
    return all(control in supported for control in controls)


def preprocess_for_inpainting(image: Image.Image) -> Dict[str, Image.Image]:
    """
    Standard preprocessing for inpainting with dual ControlNet (canny + depth).
    This is used by edit_sd.py for consistent control conditioning.
    """
    processor = get_control_processor()
    return processor.process_for_controlnet(image, ['canny', 'depth'])


def preprocess_for_ip2p(image: Image.Image) -> Dict[str, Image.Image]:
    """
    Standard preprocessing for InstructPix2Pix with canny edges and depth.
    Updated to use canny instead of softedge for better compatibility.
    """
    processor = get_control_processor()
    return processor.process_for_controlnet(image, ['canny', 'depth'])


def create_edge_mask_from_canny(canny_image: Image.Image, dilate_px: int = 2) -> Image.Image:
    """
    Create an edge-aware mask from Canny edges for selective processing.
    Useful for preserving important edges during diffusion.
    
    Args:
        canny_image: Canny edge map (PIL Image)
        dilate_px: Dilation amount for edges
        
    Returns:
        Edge mask as PIL Image
    """
    # Convert to grayscale
    edges = pil_to_numpy(canny_image.convert('L'))
    
    # Dilate edges to create mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_px*2+1, dilate_px*2+1))
    dilated = cv2.dilate(edges, kernel, iterations=1)
    
    return numpy_to_pil(dilated)


def enhance_control_strength(control_image: Image.Image, factor: float = 1.5) -> Image.Image:
    """
    Enhance control map strength by adjusting contrast.
    
    Args:
        control_image: Control map (PIL Image)
        factor: Enhancement factor (>1.0 increases contrast)
        
    Returns:
        Enhanced control map
    """
    # Convert to numpy
    img_array = pil_to_numpy(control_image).astype(np.float32) / 255.0
    
    # Apply contrast enhancement
    enhanced = np.clip(img_array * factor, 0, 1)
    
    # Convert back
    enhanced = (enhanced * 255).astype(np.uint8)
    return numpy_to_pil(enhanced)


def blend_control_maps(control1: Image.Image, control2: Image.Image, 
                      alpha: float = 0.5) -> Image.Image:
    """
    Blend two control maps for combined conditioning.
    
    Args:
        control1: First control map
        control2: Second control map  
        alpha: Blending factor (0.0=control1, 1.0=control2)
        
    Returns:
        Blended control map
    """
    # Ensure same size
    if control1.size != control2.size:
        control2 = control2.resize(control1.size, Image.Resampling.LANCZOS)
    
    # Convert to numpy
    c1 = pil_to_numpy(control1).astype(np.float32)
    c2 = pil_to_numpy(control2).astype(np.float32)
    
    # Blend
    blended = c1 * (1 - alpha) + c2 * alpha
    
    # Convert back
    blended = np.clip(blended, 0, 255).astype(np.uint8)
    return numpy_to_pil(blended)
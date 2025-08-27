"""
Quality control and assessment for aesthetic editing results.
Implements identity preservation (ArcFace), off-target protection (SSIM), and image quality metrics.
"""

import numpy as np
import cv2
from PIL import Image
from typing import Tuple, Dict, Optional
from skimage.metrics import structural_similarity as ssim
from .utils import pil_to_numpy
from models import get_arcface_model


class QualityController:
    """Quality control and assessment for generated images."""
    
    def __init__(self):
        self._arcface_model = None
        self.id_similarity_threshold = 0.35  # Threshold for identity preservation warning
        self.ssim_threshold = 0.98  # Threshold for off-target protection
    
    @property
    def arcface_model(self):
        """Lazy load ArcFace model."""
        if self._arcface_model is None:
            try:
                self._arcface_model = get_arcface_model()
            except ImportError:
                # insightface not available, disable identity checking
                self._arcface_model = None
        return self._arcface_model
    
    def extract_face_embedding(self, image: Image.Image) -> Optional[np.ndarray]:
        """
        Extract face embedding using ArcFace for identity comparison.
        
        Args:
            image: PIL Image
            
        Returns:
            Face embedding vector or None if no face detected
        """
        if self.arcface_model is None:
            return None  # Identity checking disabled
            
        # Convert PIL to OpenCV format
        cv_image = cv2.cvtColor(pil_to_numpy(image), cv2.COLOR_RGB2BGR)
        
        # Detect faces and extract embeddings
        faces = self.arcface_model.get(cv_image)
        
        if len(faces) == 0:
            return None
        
        # Use the largest face (most confident detection)
        largest_face = max(faces, key=lambda x: x.bbox[2] * x.bbox[3])
        
        return largest_face.embedding
    
    def identity_similarity(self, original: Image.Image, edited: Image.Image) -> float:
        """
        Calculate identity similarity between original and edited images using ArcFace.
        
        Args:
            original: Original PIL Image
            edited: Edited PIL Image
            
        Returns:
            Cosine similarity score (0-1, higher is more similar)
        """
        # Extract embeddings
        orig_embedding = self.extract_face_embedding(original)
        edit_embedding = self.extract_face_embedding(edited)
        
        if orig_embedding is None or edit_embedding is None:
            # Cannot compute similarity if face not detected
            return 0.0
        
        # Calculate cosine similarity
        dot_product = np.dot(orig_embedding, edit_embedding)
        norm_orig = np.linalg.norm(orig_embedding)
        norm_edit = np.linalg.norm(edit_embedding)
        
        if norm_orig == 0 or norm_edit == 0:
            return 0.0
        
        cosine_sim = dot_product / (norm_orig * norm_edit)
        
        # Convert to 0-1 range (cosine similarity can be -1 to 1)
        return (cosine_sim + 1) / 2
    
    def ssim_off_mask(self, original: Image.Image, edited: Image.Image, 
                     mask: Image.Image) -> float:
        """
        Calculate SSIM similarity in regions outside the mask (off-target protection).
        
        Args:
            original: Original PIL Image
            edited: Edited PIL Image  
            mask: Binary mask (PIL Image)
            
        Returns:
            SSIM score for off-mask regions (0-1, higher is better)
        """
        # Convert to grayscale numpy arrays
        orig_gray = cv2.cvtColor(pil_to_numpy(original), cv2.COLOR_RGB2GRAY)
        edit_gray = cv2.cvtColor(pil_to_numpy(edited), cv2.COLOR_RGB2GRAY)
        
        # Convert mask to binary
        mask_array = pil_to_numpy(mask.convert('L'))
        if mask_array.max() > 1:
            mask_array = mask_array / 255.0
        
        # Invert mask to get off-target regions
        off_mask = 1.0 - mask_array
        
        # Apply mask to images
        orig_masked = orig_gray * off_mask
        edit_masked = edit_gray * off_mask
        
        # Calculate SSIM only in off-mask regions
        # Use a smaller window to handle edge cases
        try:
            ssim_score = ssim(
                orig_masked.astype(np.float64), 
                edit_masked.astype(np.float64),
                data_range=255,
                win_size=7  # Smaller window for local regions
            )
        except ValueError:
            # Fallback for small regions
            ssim_score = ssim(
                orig_masked.astype(np.float64), 
                edit_masked.astype(np.float64),
                data_range=255,
                win_size=3
            )
        
        return max(0, ssim_score)  # Ensure non-negative
    
    def brisque_score(self, image: Image.Image) -> float:
        """
        Calculate BRISQUE (Blind/Referenceless Image Spatial Quality Evaluator) score.
        Lower scores indicate better perceptual quality.
        
        Args:
            image: PIL Image
            
        Returns:
            BRISQUE score (lower is better, typically 0-100)
        """
        try:
            import cv2
            # Convert to grayscale
            gray = cv2.cvtColor(pil_to_numpy(image), cv2.COLOR_RGB2GRAY)
            
            # Simple quality metric based on gradient analysis
            # This is a simplified version - in production, use proper BRISQUE implementation
            
            # Calculate gradients
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            
            # Calculate gradient magnitude
            grad_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            # Calculate statistics
            mean_grad = np.mean(grad_magnitude)
            std_grad = np.std(grad_magnitude)
            
            # Simple quality score (lower is better)
            # High gradient variance often indicates noise/artifacts
            quality_score = std_grad / (mean_grad + 1e-8)
            
            return min(100, quality_score * 10)  # Scale to 0-100 range
            
        except Exception:
            # Fallback: return neutral score
            return 50.0
    
    def lpips_score(self, original: Image.Image, edited: Image.Image) -> float:
        """
        Calculate LPIPS (Learned Perceptual Image Patch Similarity) score.
        Measures perceptual difference between images.
        
        Args:
            original: Original PIL Image
            edited: Edited PIL Image
            
        Returns:
            LPIPS score (0-1, lower is more similar)
        """
        try:
            import lpips
            
            # Initialize LPIPS model (AlexNet backend)
            lpips_model = lpips.LPIPS(net='alex')
            
            # Convert images to tensors
            import torch
            import torchvision.transforms as transforms
            
            transform = transforms.Compose([
                transforms.Resize((256, 256)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
            ])
            
            orig_tensor = transform(original).unsqueeze(0)
            edit_tensor = transform(edited).unsqueeze(0)
            
            # Calculate LPIPS
            with torch.no_grad():
                lpips_score = lpips_model(orig_tensor, edit_tensor).item()
            
            return lpips_score
            
        except ImportError:
            # LPIPS not available, use simple MSE-based metric
            orig_array = pil_to_numpy(original).astype(np.float32) / 255.0
            edit_array = pil_to_numpy(edited).astype(np.float32) / 255.0
            
            mse = np.mean((orig_array - edit_array) ** 2)
            return min(1.0, mse * 10)  # Scale MSE to 0-1 range
    
    def comprehensive_qc(self, original: Image.Image, edited: Image.Image, 
                        mask: Image.Image) -> Dict[str, float]:
        """
        Perform comprehensive quality control assessment.
        
        Args:
            original: Original PIL Image
            edited: Edited PIL Image
            mask: Area mask
            
        Returns:
            Dictionary with all quality metrics
        """
        results = {}
        
        # Identity preservation
        results['id_similarity'] = self.identity_similarity(original, edited)
        results['id_warning'] = results['id_similarity'] < self.id_similarity_threshold
        
        # Off-target protection
        results['ssim_off_mask'] = self.ssim_off_mask(original, edited, mask)
        results['ssim_warning'] = results['ssim_off_mask'] < self.ssim_threshold
        
        # Image quality
        results['brisque_original'] = self.brisque_score(original)
        results['brisque_edited'] = self.brisque_score(edited)
        results['brisque_degradation'] = results['brisque_edited'] - results['brisque_original']
        
        # Perceptual similarity
        results['lpips_score'] = self.lpips_score(original, edited)
        
        # Overall quality flag
        results['quality_passed'] = (
            not results['id_warning'] and 
            not results['ssim_warning'] and
            results['brisque_degradation'] < 10  # Allow some quality variation
        )
        
        return results
    
    def should_retry(self, qc_results: Dict[str, float]) -> Tuple[bool, str]:
        """
        Determine if generation should be retried based on QC results.
        
        Args:
            qc_results: Results from comprehensive_qc
            
        Returns:
            Tuple of (should_retry, reason)
        """
        if qc_results['id_warning']:
            return True, "Identity similarity too low"
        
        if qc_results['ssim_warning']:
            return True, "Off-target changes detected"
        
        if qc_results['brisque_degradation'] > 20:
            return True, "Significant quality degradation"
        
        return False, "Quality checks passed"


# Global QC instance
_quality_controller = None

def get_quality_controller() -> QualityController:
    """Get singleton quality controller instance."""
    global _quality_controller
    if _quality_controller is None:
        _quality_controller = QualityController()
    return _quality_controller


def qc(original: Image.Image, edited: Image.Image, mask: Image.Image) -> Tuple[float, float]:
    """
    Simplified QC function for API compatibility.
    Returns identity similarity and off-mask SSIM.
    
    Args:
        original: Original PIL Image
        edited: Edited PIL Image
        mask: Area mask
        
    Returns:
        Tuple of (id_similarity, ssim_off_mask)
    """
    controller = get_quality_controller()
    id_sim = controller.identity_similarity(original, edited)
    ssim_score = controller.ssim_off_mask(original, edited, mask)
    
    return id_sim, ssim_score


def comprehensive_assessment(original: Image.Image, edited: Image.Image, 
                           mask: Image.Image) -> Dict[str, float]:
    """
    Convenience function for comprehensive quality assessment.
    
    Args:
        original: Original PIL Image
        edited: Edited PIL Image
        mask: Area mask
        
    Returns:
        Comprehensive quality metrics
    """
    controller = get_quality_controller()
    return controller.comprehensive_qc(original, edited, mask)


def set_quality_thresholds(id_threshold: float = None, ssim_threshold: float = None):
    """
    Configure quality control thresholds.
    
    Args:
        id_threshold: Identity similarity threshold (lower triggers warning)
        ssim_threshold: SSIM off-mask threshold (lower triggers warning)
    """
    controller = get_quality_controller()
    
    if id_threshold is not None:
        controller.id_similarity_threshold = id_threshold
    
    if ssim_threshold is not None:
        controller.ssim_threshold = ssim_threshold


def validate_result_quality(original: Image.Image, edited: Image.Image, 
                          mask: Image.Image, strict: bool = False) -> bool:
    """
    Validate if the edited result meets quality standards.
    
    Args:
        original: Original image
        edited: Edited image
        mask: Area mask
        strict: Use stricter thresholds
        
    Returns:
        True if quality is acceptable
    """
    controller = get_quality_controller()
    
    # Temporarily adjust thresholds if strict mode
    orig_id_threshold = controller.id_similarity_threshold
    orig_ssim_threshold = controller.ssim_threshold
    
    if strict:
        controller.id_similarity_threshold = 0.5  # Stricter identity preservation
        controller.ssim_threshold = 0.99  # Stricter off-target protection
    
    try:
        qc_results = controller.comprehensive_qc(original, edited, mask)
        return qc_results['quality_passed']
    finally:
        # Restore original thresholds
        controller.id_similarity_threshold = orig_id_threshold
        controller.ssim_threshold = orig_ssim_threshold
"""
Image Processor for Medical AI Assistant

Handles image decoding, validation, preprocessing, and normalization
for facial analysis and landmark detection.
"""

import cv2
import numpy as np
import base64
from typing import Optional, Tuple, Dict, Any
import logging
from io import BytesIO
from PIL import Image
import requests
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ImageProcessor:
    """Service for processing and validating images for facial analysis."""
    
    def __init__(self):
        """Initialize image processor with configuration."""
        self.max_image_size = (2048, 2048)  # Maximum dimensions
        self.min_image_size = (320, 320)    # Minimum dimensions
        self.target_size = (1024, 1024)     # Preferred processing size
        self.supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.webp']
        self.max_file_size_mb = 10  # Maximum file size in MB
        
        logger.info("✅ ImageProcessor initialized")
    
    def is_healthy(self) -> bool:
        """Check if image processor is healthy."""
        try:
            # Test with a small dummy image
            dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
            dummy_image.fill(128)
            
            # Test basic operations
            result = self._validate_image_array(dummy_image)
            return result is not None
        except:
            return False
    
    async def process_image(self, image_input: str) -> Optional[np.ndarray]:
        """
        Process image from various input formats.
        
        Args:
            image_input: Base64 string, data URL, or image URL
            
        Returns:
            Processed image as numpy array (RGB format) or None if failed
        """
        try:
            # Decode image based on input format
            if image_input.startswith('data:image'):
                # Data URL format
                image_array = await self._decode_data_url(image_input)
            elif image_input.startswith('http'):
                # Remote URL
                image_array = await self._download_image(image_input)
            else:
                # Plain base64
                image_array = await self._decode_base64(image_input)
            
            if image_array is None:
                return None
            
            # Validate image
            validated_image = self._validate_image_array(image_array)
            if validated_image is None:
                return None
            
            # Preprocess image
            processed_image = self._preprocess_image(validated_image)
            
            logger.debug(f"📸 Processed image: {processed_image.shape}")
            return processed_image
            
        except Exception as e:
            logger.error(f"❌ Image processing failed: {str(e)}")
            return None
    
    async def _decode_data_url(self, data_url: str) -> Optional[np.ndarray]:
        """Decode image from data URL format."""
        try:
            # Parse data URL
            header, data = data_url.split(',', 1)
            
            # Validate MIME type
            if 'image/' not in header:
                logger.error("❌ Invalid MIME type in data URL")
                return None
            
            # Decode base64
            return await self._decode_base64(data)
            
        except Exception as e:
            logger.error(f"❌ Data URL decoding failed: {str(e)}")
            return None
    
    async def _decode_base64(self, base64_string: str) -> Optional[np.ndarray]:
        """Decode image from base64 string."""
        try:
            # Remove any whitespace
            base64_string = base64_string.strip()
            
            # Decode base64
            image_bytes = base64.b64decode(base64_string)
            
            # Check file size
            if len(image_bytes) > self.max_file_size_mb * 1024 * 1024:
                logger.error(f"❌ Image too large: {len(image_bytes) / (1024*1024):.1f}MB")
                return None
            
            # Convert to PIL Image
            pil_image = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB if needed
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to numpy array
            image_array = np.array(pil_image)
            
            return image_array
            
        except Exception as e:
            logger.error(f"❌ Base64 decoding failed: {str(e)}")
            return None
    
    async def _download_image(self, url: str) -> Optional[np.ndarray]:
        """Download and decode image from URL."""
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme in ['http', 'https']:
                logger.error("❌ Invalid URL scheme")
                return None
            
            # Download image with timeout
            headers = {
                'User-Agent': 'NuvaFace Medical Assistant/1.0'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.error(f"❌ Invalid content type: {content_type}")
                return None
            
            # Check file size
            if len(response.content) > self.max_file_size_mb * 1024 * 1024:
                logger.error(f"❌ Downloaded image too large: {len(response.content) / (1024*1024):.1f}MB")
                return None
            
            # Convert to PIL Image
            pil_image = Image.open(BytesIO(response.content))
            
            # Convert to RGB if needed
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to numpy array
            image_array = np.array(pil_image)
            
            logger.debug(f"🌐 Downloaded image: {url}")
            return image_array
            
        except Exception as e:
            logger.error(f"❌ Image download failed: {str(e)}")
            return None
    
    def _validate_image_array(self, image_array: np.ndarray) -> Optional[np.ndarray]:
        """Validate image array properties."""
        try:
            # Check if it's a valid array
            if not isinstance(image_array, np.ndarray):
                logger.error("❌ Input is not a numpy array")
                return None
            
            # Check dimensions
            if len(image_array.shape) != 3:
                logger.error(f"❌ Invalid image dimensions: {image_array.shape}")
                return None
            
            height, width, channels = image_array.shape
            
            # Check channels (should be 3 for RGB)
            if channels != 3:
                logger.error(f"❌ Invalid number of channels: {channels}")
                return None
            
            # Check size limits
            if width < self.min_image_size[0] or height < self.min_image_size[1]:
                logger.error(f"❌ Image too small: {width}x{height}")
                return None
            
            if width > self.max_image_size[0] or height > self.max_image_size[1]:
                logger.warning(f"⚠️ Image very large: {width}x{height}, will be resized")
            
            # Check data type
            if image_array.dtype != np.uint8:
                # Convert to uint8 if possible
                if image_array.dtype in [np.float32, np.float64]:
                    if image_array.max() <= 1.0:
                        image_array = (image_array * 255).astype(np.uint8)
                    else:
                        image_array = image_array.astype(np.uint8)
                else:
                    image_array = image_array.astype(np.uint8)
            
            # Check for completely black or white images
            mean_intensity = np.mean(image_array)
            if mean_intensity < 10 or mean_intensity > 245:
                logger.warning(f"⚠️ Image may be too dark or bright: mean intensity {mean_intensity:.1f}")
            
            return image_array
            
        except Exception as e:
            logger.error(f"❌ Image validation failed: {str(e)}")
            return None
    
    def _preprocess_image(self, image_array: np.ndarray) -> np.ndarray:
        """Preprocess image for optimal facial analysis."""
        try:
            height, width = image_array.shape[:2]
            
            # Resize if too large
            if width > self.max_image_size[0] or height > self.max_image_size[1]:
                image_array = self._smart_resize(image_array, self.max_image_size)
                logger.debug(f"🔄 Resized image to {image_array.shape[1]}x{image_array.shape[0]}")
            
            # Enhance image quality if needed
            enhanced_image = self._enhance_image_quality(image_array)
            
            # Normalize face orientation (optional)
            # normalized_image = self._normalize_orientation(enhanced_image)
            
            return enhanced_image
            
        except Exception as e:
            logger.error(f"❌ Image preprocessing failed: {str(e)}")
            return image_array  # Return original if preprocessing fails
    
    def _smart_resize(self, image: np.ndarray, max_size: Tuple[int, int]) -> np.ndarray:
        """Intelligently resize image while maintaining aspect ratio."""
        height, width = image.shape[:2]
        max_width, max_height = max_size
        
        # Calculate scaling factor
        scale_w = max_width / width
        scale_h = max_height / height
        scale = min(scale_w, scale_h)
        
        if scale >= 1.0:
            return image  # No resizing needed
        
        # Calculate new dimensions
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Use high-quality resizing
        resized = cv2.resize(
            image, 
            (new_width, new_height), 
            interpolation=cv2.INTER_LANCZOS4
        )
        
        return resized
    
    def _enhance_image_quality(self, image: np.ndarray) -> np.ndarray:
        """Enhance image quality for better landmark detection."""
        try:
            # Convert to LAB color space for better processing
            lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) to L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_channel_enhanced = clahe.apply(l_channel)
            
            # Merge channels back
            enhanced_lab = cv2.merge([l_channel_enhanced, a_channel, b_channel])
            
            # Convert back to RGB
            enhanced_rgb = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2RGB)
            
            # Apply slight gaussian blur to reduce noise
            enhanced_rgb = cv2.GaussianBlur(enhanced_rgb, (3, 3), 0)
            
            # Subtle sharpening
            kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
            sharpened = cv2.filter2D(enhanced_rgb, -1, kernel)
            
            # Blend original and sharpened (subtle effect)
            final_image = cv2.addWeighted(enhanced_rgb, 0.8, sharpened, 0.2, 0)
            
            return final_image
            
        except Exception as e:
            logger.warning(f"⚠️ Image enhancement failed: {str(e)}")
            return image  # Return original if enhancement fails
    
    def _normalize_orientation(self, image: np.ndarray) -> np.ndarray:
        """Normalize image orientation based on face detection."""
        # This is a placeholder for more advanced orientation correction
        # Could be implemented using face detection to rotate images to standard orientation
        return image
    
    def analyze_image_quality(self, image: np.ndarray) -> Dict[str, Any]:
        """Analyze image quality metrics for feedback."""
        try:
            height, width = image.shape[:2]
            
            # Calculate basic metrics
            mean_brightness = np.mean(image)
            std_contrast = np.std(image)
            
            # Calculate sharpness (Laplacian variance)
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Color distribution
            color_channels = cv2.split(image)
            color_balance = {
                'red_mean': float(np.mean(color_channels[0])),
                'green_mean': float(np.mean(color_channels[1])),
                'blue_mean': float(np.mean(color_channels[2]))
            }
            
            # Quality assessment
            quality_score = self._calculate_quality_score(
                mean_brightness, std_contrast, sharpness, width, height
            )
            
            # Generate recommendations
            recommendations = self._generate_quality_recommendations(
                mean_brightness, std_contrast, sharpness, width, height
            )
            
            return {
                'dimensions': {'width': width, 'height': height},
                'brightness': float(mean_brightness),
                'contrast': float(std_contrast),
                'sharpness': float(sharpness),
                'color_balance': color_balance,
                'quality_score': quality_score,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"❌ Image quality analysis failed: {str(e)}")
            return {}
    
    def _calculate_quality_score(
        self, 
        brightness: float, 
        contrast: float, 
        sharpness: float,
        width: int, 
        height: int
    ) -> float:
        """Calculate overall image quality score (0-1)."""
        score = 1.0
        
        # Resolution score
        total_pixels = width * height
        if total_pixels < 500000:  # Less than 0.5MP
            score *= 0.7
        elif total_pixels < 1000000:  # Less than 1MP
            score *= 0.85
        
        # Brightness score
        if brightness < 50 or brightness > 200:
            score *= 0.8
        elif brightness < 80 or brightness > 180:
            score *= 0.9
        
        # Contrast score
        if contrast < 20:
            score *= 0.7  # Too low contrast
        elif contrast > 80:
            score *= 0.9  # Very high contrast
        
        # Sharpness score
        if sharpness < 100:
            score *= 0.8  # Blurry
        elif sharpness < 300:
            score *= 0.9  # Acceptable
        
        return max(0.0, min(1.0, score))
    
    def _generate_quality_recommendations(
        self,
        brightness: float,
        contrast: float, 
        sharpness: float,
        width: int,
        height: int
    ) -> List[str]:
        """Generate recommendations for image quality improvement."""
        recommendations = []
        
        # Resolution recommendations
        if width * height < 500000:
            recommendations.append("Use higher resolution image (at least 800x600)")
        
        # Brightness recommendations
        if brightness < 60:
            recommendations.append("Image is too dark - use better lighting")
        elif brightness > 200:
            recommendations.append("Image is overexposed - reduce lighting")
        
        # Contrast recommendations
        if contrast < 25:
            recommendations.append("Low contrast - ensure good lighting difference")
        
        # Sharpness recommendations
        if sharpness < 150:
            recommendations.append("Image appears blurry - ensure camera is in focus")
        
        # General recommendations
        if len(recommendations) == 0:
            recommendations.append("Image quality is good for analysis")
        
        return recommendations
    
    def get_image_info(self, image: np.ndarray) -> Dict[str, Any]:
        """Get detailed information about the image."""
        try:
            height, width, channels = image.shape
            
            return {
                'width': width,
                'height': height,
                'channels': channels,
                'dtype': str(image.dtype),
                'size_bytes': image.nbytes,
                'aspect_ratio': width / height,
                'megapixels': (width * height) / 1000000,
                'color_space': 'RGB',
                'min_value': int(image.min()),
                'max_value': int(image.max()),
                'mean_value': float(image.mean())
            }
        except Exception as e:
            logger.error(f"❌ Failed to get image info: {str(e)}")
            return {}
    
    async def cleanup(self):
        """Cleanup any resources."""
        # No specific cleanup needed for image processor
        logger.info("✅ ImageProcessor cleanup completed")
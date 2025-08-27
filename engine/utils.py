"""
Utility functions for image processing, I/O, and preprocessing.
Handles base64 encoding/decoding, face alignment, resizing, and EXIF handling.
"""

import base64
import io
import random
import numpy as np
import cv2
import torch
from PIL import Image, ExifTags
from typing import Union, Tuple, Optional
import mediapipe as mp


def set_seed(seed: int) -> None:
    """Set random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)


def fix_exif_orientation(image: Image.Image) -> Image.Image:
    """Fix image orientation based on EXIF data."""
    try:
        if hasattr(image, '_getexif'):
            exif = image._getexif()
            if exif is not None:
                for tag, value in exif.items():
                    if ExifTags.TAGS.get(tag) == 'Orientation':
                        if value == 3:
                            image = image.rotate(180, expand=True)
                        elif value == 6:
                            image = image.rotate(270, expand=True)
                        elif value == 8:
                            image = image.rotate(90, expand=True)
                        break
    except:
        pass  # If EXIF processing fails, continue with original image
    
    return image


def base64_to_image(base64_str: str) -> Image.Image:
    """Convert base64 string to PIL Image."""
    # Remove data URL prefix if present
    if base64_str.startswith('data:image'):
        base64_str = base64_str.split(',')[1]
    
    image_bytes = base64.b64decode(base64_str)
    image = Image.open(io.BytesIO(image_bytes))
    
    # Fix orientation and convert to RGB
    image = fix_exif_orientation(image)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    return image


def image_to_base64(image: Image.Image, format: str = 'PNG') -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    image_bytes = buffer.getvalue()
    return base64.b64encode(image_bytes).decode('utf-8')


def url_to_image(url: str) -> Image.Image:
    """Download image from URL and convert to PIL Image."""
    import requests
    response = requests.get(url)
    response.raise_for_status()
    
    image = Image.open(io.BytesIO(response.content))
    image = fix_exif_orientation(image)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    return image


def load_image(image_input: Union[str, Image.Image]) -> Image.Image:
    """Load image from various input formats (base64, URL, or PIL Image)."""
    if isinstance(image_input, Image.Image):
        return image_input
    elif isinstance(image_input, str):
        if image_input.startswith('http'):
            return url_to_image(image_input)
        else:
            return base64_to_image(image_input)
    else:
        raise ValueError(f"Unsupported image input type: {type(image_input)}")


def resize_to_target(image: Image.Image, target_size: int = 768) -> Image.Image:
    """Resize image so that the longer side equals target_size, maintaining aspect ratio."""
    w, h = image.size
    
    if max(w, h) == target_size:
        return image
    
    if w > h:
        new_w = target_size
        new_h = int(h * target_size / w)
    else:
        new_h = target_size
        new_w = int(w * target_size / h)
    
    return image.resize((new_w, new_h), Image.Resampling.LANCZOS)


def align_face_horizontal(image: Image.Image) -> Tuple[Image.Image, Optional[dict]]:
    """
    Align face so that eyes are horizontal using MediaPipe Face Detection.
    Returns aligned image and alignment info.
    """
    mp_face_detection = mp.solutions.face_detection
    mp_drawing = mp.solutions.drawing_utils
    
    # Convert PIL to OpenCV format
    cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    
    with mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5) as face_detection:
        results = face_detection.process(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        
        if not results.detections:
            # No face detected, return original image
            return image, None
        
        # Use the first (most confident) detection
        detection = results.detections[0]
        
        # Get keypoints (eyes, nose, mouth, ears)
        keypoints = detection.location_data.relative_keypoints
        
        # MediaPipe face detection keypoints:
        # 0: right_eye, 1: left_eye, 2: nose_tip, 3: mouth_center, 4: right_ear_tragion, 5: left_ear_tragion
        if len(keypoints) >= 2:
            h, w = cv_image.shape[:2]
            
            right_eye = (int(keypoints[0].x * w), int(keypoints[0].y * h))
            left_eye = (int(keypoints[1].x * w), int(keypoints[1].y * h))
            
            # Calculate rotation angle to make eyes horizontal
            dx = left_eye[0] - right_eye[0]
            dy = left_eye[1] - right_eye[1]
            angle = np.degrees(np.arctan2(dy, dx))
            
            # Only rotate if angle is significant (> 2 degrees)
            if abs(angle) > 2:
                # Calculate rotation center (midpoint between eyes)
                center_x = (right_eye[0] + left_eye[0]) // 2
                center_y = (right_eye[1] + left_eye[1]) // 2
                
                # Create rotation matrix
                rotation_matrix = cv2.getRotationMatrix2D((center_x, center_y), angle, 1.0)
                
                # Apply rotation
                rotated = cv2.warpAffine(cv_image, rotation_matrix, (w, h), flags=cv2.INTER_LANCZOS4)
                
                # Convert back to PIL
                aligned_image = Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))
                
                alignment_info = {
                    'rotation_angle': angle,
                    'rotation_center': (center_x, center_y),
                    'right_eye': right_eye,
                    'left_eye': left_eye
                }
                
                return aligned_image, alignment_info
    
    # No significant rotation needed
    return image, {'rotation_angle': 0}


def preprocess_image(image: Union[str, Image.Image], target_size: int = 768, align_face: bool = True) -> Tuple[Image.Image, dict]:
    """
    Complete preprocessing pipeline: load, fix orientation, optionally align face, resize.
    Returns processed image and metadata.
    """
    # Load image
    image = load_image(image)
    original_size = image.size
    
    metadata = {
        'original_size': original_size,
        'target_size': target_size,
        'alignment_applied': False,
        'alignment_info': None
    }
    
    # Face alignment (optional)
    if align_face:
        image, alignment_info = align_face_horizontal(image)
        if alignment_info and alignment_info.get('rotation_angle', 0) != 0:
            metadata['alignment_applied'] = True
            metadata['alignment_info'] = alignment_info
    
    # Resize to target size
    image = resize_to_target(image, target_size)
    metadata['final_size'] = image.size
    
    return image, metadata


def numpy_to_pil(array: np.ndarray) -> Image.Image:
    """Convert numpy array to PIL Image."""
    if array.dtype != np.uint8:
        array = (array * 255).astype(np.uint8)
    
    if len(array.shape) == 3 and array.shape[2] == 3:
        return Image.fromarray(array, 'RGB')
    elif len(array.shape) == 2:
        return Image.fromarray(array, 'L')
    else:
        raise ValueError(f"Unsupported array shape: {array.shape}")


def pil_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array."""
    return np.array(image)


def create_circular_mask(size: Tuple[int, int], center: Tuple[int, int], radius: int) -> np.ndarray:
    """Create a circular mask."""
    h, w = size
    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)
    mask = dist_from_center <= radius
    return mask.astype(np.uint8) * 255


def feather_mask(mask: np.ndarray, feather_px: int) -> np.ndarray:
    """Apply feathering (Gaussian blur) to mask edges."""
    if feather_px <= 0:
        return mask
    
    # Apply Gaussian blur for soft edges
    kernel_size = feather_px * 2 + 1
    blurred = cv2.GaussianBlur(mask, (kernel_size, kernel_size), feather_px / 3)
    
    return blurred


def morphological_cleanup(mask: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """Clean up mask using morphological operations (opening + closing)."""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    
    # Opening: remove small noise
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Closing: fill small holes
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    
    return closed


def refine_mask(mask: np.ndarray, feather_px: int = 3, morph_kernel: int = 3) -> np.ndarray:
    """Complete mask refinement pipeline: morphological cleanup + feathering."""
    # Morphological cleanup
    if morph_kernel > 0:
        mask = morphological_cleanup(mask, morph_kernel)
    
    # Feathering
    if feather_px > 0:
        mask = feather_mask(mask, feather_px)
    
    return mask


def blend_images_with_mask(background: Image.Image, foreground: Image.Image, mask: Image.Image) -> Image.Image:
    """Blend two images using a mask (Poisson-like blending)."""
    # Convert to numpy arrays
    bg = np.array(background).astype(np.float32) / 255.0
    fg = np.array(foreground).astype(np.float32) / 255.0
    
    # Handle mask
    if mask.mode != 'L':
        mask = mask.convert('L')
    mask_array = np.array(mask).astype(np.float32) / 255.0
    
    # Expand mask to 3 channels
    if len(mask_array.shape) == 2:
        mask_array = np.stack([mask_array] * 3, axis=-1)
    
    # Blend
    blended = bg * (1 - mask_array) + fg * mask_array
    
    # Convert back to PIL
    blended = (blended * 255).astype(np.uint8)
    return Image.fromarray(blended)


def get_bbox_from_mask(mask: np.ndarray) -> Tuple[int, int, int, int]:
    """Get bounding box coordinates (x, y, w, h) from binary mask."""
    coords = cv2.findNonZero(mask)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        return x, y, w, h
    else:
        return 0, 0, 0, 0


def crop_to_bbox(image: Image.Image, bbox: Tuple[int, int, int, int], padding: int = 0) -> Image.Image:
    """Crop image to bounding box with optional padding."""
    x, y, w, h = bbox
    x1 = max(0, x - padding)
    y1 = max(0, y - padding)
    x2 = min(image.width, x + w + padding)
    y2 = min(image.height, y + h + padding)
    
    return image.crop((x1, y1, x2, y2))
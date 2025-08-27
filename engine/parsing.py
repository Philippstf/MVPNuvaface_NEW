"""
Face parsing using MediaPipe FaceMesh to generate area-specific masks.
Supports lips, chin, cheeks, and forehead regions for aesthetic treatments.
"""

import numpy as np
import cv2
from PIL import Image
from typing import Tuple, Optional, Dict, List
import mediapipe as mp
from .utils import pil_to_numpy, numpy_to_pil, refine_mask

# MediaPipe FaceMesh landmark indices for different facial regions
# Based on the 468 landmark model from MediaPipe

# Lips landmarks (outer contour) - Correct MediaPipe FaceMesh indices
LIPS_OUTER = [
    61, 146, 91, 181, 84, 17, 314, 405, 320, 307, 375, 321, 308, 324, 318,
    402, 317, 14, 87, 178, 88, 95, 78, 191, 80, 81, 82, 13, 312, 311, 310, 415
]

# CORRECTED MediaPipe FaceMesh landmarks - based on official documentation
# These are the OFFICIAL MediaPipe indices for lip segmentation

# Upper lip landmarks (official MediaPipe indices)
LIPS_UPPER_CORRECT = [0, 267, 269, 270, 409, 291, 375, 321, 405, 314, 17, 84, 181, 91, 146, 61, 185, 40, 39, 37]

# Lower lip landmarks (official MediaPipe indices)  
LIPS_LOWER_CORRECT = [13, 312, 311, 310, 415, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78, 191, 80, 81, 82]

# Complete lips boundary combining both upper and lower
LIPS_COMPLETE_CORRECT = LIPS_UPPER_CORRECT + LIPS_LOWER_CORRECT

# Inner lip contour for more precise definition
LIPS_INNER_COMPLETE = [
    # Inner upper lip
    78, 191, 80, 81, 82, 13, 312, 311, 310, 415,
    # Inner lower lip
    308, 324, 318, 402, 317, 14, 87, 178, 88, 95
]

# Forehead region (derived from eyebrow landmarks + extrapolation)
EYEBROW_LEFT = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
EYEBROW_RIGHT = [296, 334, 293, 300, 276, 283, 282, 295, 285, 336]

# CORRECTED Chin region - using official MediaPipe FACEMESH_FACE_OVAL landmarks
# Based on official MediaPipe documentation and research findings

# Complete face oval landmarks (for reference)
FACE_OVAL_ALL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]

# Chin-specific landmarks - Based on aesthetic medicine research 2024
# Anatomical landmarks: Pogonion (152), Menton, Paragonion areas
# Research shows chin filler targets: pogonion, menton, paragonion landmarks

# Primary chin landmarks for aesthetic treatment (pogonion region)
CHIN_POGONION_CENTER = [152]  # Central most projecting point

# Extended chin region for filler treatment (rhombic area per research)
CHIN_AESTHETIC_LANDMARKS = [
    # Central pogonion
    152,
    # Menton area (inferior border) 
    175, 199, 200, 3, 51, 48, 115, 131, 134, 102, 49, 220, 305, 272, 407, 424, 436, 416, 365, 397, 288, 361, 323,
    # Paragonion lateral areas (both sides)
    172, 136, 150, 149, 176, 148, 377, 400, 378, 379, 365, 397, 288, 361, 323
]

# Conservative jawline landmarks (lower face contour)
CHIN_JAWLINE_LOWER = [
    # Lower jawline only (not including upper jaw/cheek areas)
    172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397, 288, 361, 323
]

# Cheeks region - anatomically correct for aesthetic treatments
# Focus on zygomatic bone and mid-face volume enhancement areas
CHEEK_LEFT_ENHANCED = [
    # Zygomatic region (upper cheek)
    116, 117, 118, 119, 120, 121, 126, 142,
    # Mid-face volume area (medical aesthetic target zone)
    36, 205, 206, 207, 213, 192, 147, 187, 234, 127, 162
]

CHEEK_RIGHT_ENHANCED = [
    # Zygomatic region (upper cheek) - mirrored
    345, 346, 347, 348, 349, 350, 355, 371,
    # Mid-face volume area (medical aesthetic target zone) - mirrored  
    266, 425, 426, 427, 436, 416, 376, 411, 454, 356, 389
]


class FaceParser:
    """Face parsing using MediaPipe FaceMesh."""
    
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    
    def extract_landmarks(self, image: Image.Image) -> Optional[np.ndarray]:
        """Extract 468 facial landmarks from image."""
        # Convert PIL to OpenCV format
        cv_image = cv2.cvtColor(pil_to_numpy(image), cv2.COLOR_RGB2BGR)
        
        # Process with MediaPipe
        results = self.face_mesh.process(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        
        if not results.multi_face_landmarks:
            return None
        
        # Get first face landmarks
        face_landmarks = results.multi_face_landmarks[0]
        h, w = image.height, image.width
        
        # Convert normalized coordinates to pixel coordinates
        landmarks = []
        for landmark in face_landmarks.landmark:
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            landmarks.append([x, y])
        
        return np.array(landmarks)
    
    def create_polygon_mask(self, image_size: Tuple[int, int], landmarks: np.ndarray, 
                          indices: List[int]) -> np.ndarray:
        """Create a polygon mask from landmark indices."""
        h, w = image_size
        
        # Get polygon points
        points = landmarks[indices]
        
        # Create mask
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [points], 255)
        
        return mask
    
    def create_lips_mask(self, image: Image.Image, landmarks: np.ndarray) -> np.ndarray:
        """Create expanded lips mask for volumetric enhancement with surrounding tissue."""
        mask = np.zeros((image.height, image.width), dtype=np.uint8)
        
        # Core lip regions using corrected MediaPipe landmarks
        upper_lips = landmarks[LIPS_UPPER_CORRECT]
        lower_lips = landmarks[LIPS_LOWER_CORRECT]
        complete_lips = landmarks[LIPS_COMPLETE_CORRECT]
        
        # Fill core lip regions
        cv2.fillPoly(mask, [upper_lips], 255)
        cv2.fillPoly(mask, [lower_lips], 255)
        cv2.fillPoly(mask, [complete_lips], 255)
        
        # Enhanced mask: Add surrounding tissue for natural volume enhancement
        # Calculate lip center and dimensions
        lip_points = landmarks[LIPS_COMPLETE_CORRECT]
        center_x = int(np.mean(lip_points[:, 0]))
        center_y = int(np.mean(lip_points[:, 1]))
        
        # Calculate lip width and height for proportional expansion
        lip_width = np.max(lip_points[:, 0]) - np.min(lip_points[:, 0])
        lip_height = np.max(lip_points[:, 1]) - np.min(lip_points[:, 1])
        
        # Create expanded elliptical region for natural enhancement
        expansion_factor = 0.3  # 30% larger for surrounding tissue
        expanded_width = int(lip_width * (1 + expansion_factor))
        expanded_height = int(lip_height * (1 + expansion_factor))
        
        # Draw expanded ellipse
        cv2.ellipse(mask, (center_x, center_y), 
                   (expanded_width // 2, expanded_height // 2), 
                   0, 0, 360, 128, -1)  # 128 = 50% opacity for blending
        
        # Ensure core lips remain at full intensity
        cv2.fillPoly(mask, [complete_lips], 255)
        
        return mask
    
    def create_forehead_mask(self, image: Image.Image, landmarks: np.ndarray) -> np.ndarray:
        """Create clean forehead mask for Botox treatment - avoiding eyebrows and hairline."""
        h, w = image.height, image.width
        
        # Get eyebrow landmarks
        left_brow = landmarks[EYEBROW_LEFT]
        right_brow = landmarks[EYEBROW_RIGHT]
        
        # Find eyebrow boundaries - but stay ABOVE them
        leftmost_brow = left_brow[np.argmin(left_brow[:, 0])]
        rightmost_brow = right_brow[np.argmax(right_brow[:, 0])]
        
        # Get highest eyebrow points to stay above them
        highest_left_brow = left_brow[np.argmin(left_brow[:, 1])]
        highest_right_brow = right_brow[np.argmin(right_brow[:, 1])]
        
        # Create forehead area ABOVE eyebrows only
        forehead_offset = 15  # Stay 15px above eyebrows
        forehead_height = int(0.10 * h)  # Smaller height to avoid hairline
        
        # Conservative forehead area - only smooth skin above eyebrows
        forehead_points = np.array([
            # Start above left eyebrow
            [leftmost_brow[0] + 10, highest_left_brow[1] - forehead_offset],
            # Top of forehead (conservative)
            [leftmost_brow[0] + 40, highest_left_brow[1] - forehead_height],
            [rightmost_brow[0] - 40, highest_right_brow[1] - forehead_height],
            # End above right eyebrow
            [rightmost_brow[0] - 10, highest_right_brow[1] - forehead_offset],
            # Back to start, staying above eyebrows
            [rightmost_brow[0] - 10, highest_right_brow[1] - forehead_offset],
            [leftmost_brow[0] + 10, highest_left_brow[1] - forehead_offset]
        ])
        
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [forehead_points], 255)
        
        return mask
    
    def create_chin_mask(self, image: Image.Image, landmarks: np.ndarray) -> np.ndarray:
        """Create anatomically correct chin mask based on aesthetic medicine research 2024.
        
        Uses pogonion, menton, and paragonion landmarks for rhombic chin treatment area.
        Based on: 'Chin Augmentation With Hyaluronic Acid: An Injection Technique Based on Anatomical Morphology'
        """
        mask = np.zeros((image.height, image.width), dtype=np.uint8)
        
        try:
            # STEP 1: Use research-based anatomical landmarks
            # Get pogonion (central projection point)
            pogonion = landmarks[152]
            
            # Get jawline landmarks for proper chin contour
            jawline_points = landmarks[CHIN_JAWLINE_LOWER]
            
            # STEP 2: Create rhombic chin area (pogonion, menton, paragonion regions)
            # Based on 2024 research showing rhombic area formation
            
            # Find menton (lowest point of chin)
            menton_candidates = landmarks[[175, 199, 200, 3, 51, 48]]
            menton = menton_candidates[np.argmax(menton_candidates[:, 1])]  # Lowest Y value
            
            # Find paragonion points (lateral chin projections)
            left_paragonion = landmarks[172]   # Left side chin contour
            right_paragonion = landmarks[397]  # Right side chin contour
            
            # Create rhombic polygon based on aesthetic treatment area
            rhombic_points = np.array([
                pogonion,                    # Top center (most projecting)
                left_paragonion,             # Left lateral
                menton,                      # Bottom center (lowest)
                right_paragonion             # Right lateral
            ])
            
            # Create convex hull for smooth boundaries
            hull = cv2.convexHull(rhombic_points)
            cv2.fillPoly(mask, [hull], 255)
            
            # STEP 3: Extend mask using jawline for natural chin boundaries
            # Connect to lower jawline for anatomically correct coverage
            try:
                # Create extended polygon including lower jawline
                extended_points = np.vstack([
                    rhombic_points,
                    landmarks[[136, 150, 149, 176, 148]],  # Lower left jaw
                    landmarks[[377, 400, 378, 379, 365]]   # Lower right jaw
                ])
                
                # Create hull for extended area
                extended_hull = cv2.convexHull(extended_points)
                extended_mask = np.zeros_like(mask)
                cv2.fillPoly(extended_mask, [extended_hull], 255)
                
                # Combine with original rhombic mask
                mask = cv2.bitwise_or(mask, extended_mask)
                
            except (IndexError, ValueError):
                # If extended points fail, use rhombic area only
                pass
            
            # STEP 4: Morphological refinement for smooth boundaries
            # Research shows importance of smooth injection area boundaries
            kernel_size = max(5, int(0.008 * min(image.width, image.height)))
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            
            # Apply closing to fill gaps and create smooth contour
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # STEP 5: Safety boundaries to avoid mouth area
            # Ensure mask doesn't extend above mouth level
            mouth_landmarks = landmarks[[61, 291, 13, 14, 17, 18]]  # Mouth corners and center
            mouth_top_y = np.min(mouth_landmarks[:, 1]) - int(0.005 * image.height)  # Safety margin
            
            # Clip mask above mouth area
            mask[:mouth_top_y, :] = 0
            
            # STEP 6: Final smoothing for natural boundaries
            mask = cv2.GaussianBlur(mask, (5, 5), 1.0)
            _, mask = cv2.threshold(mask, 127, 255, cv2.THRESH_BINARY)
            
            return mask
            
        except (IndexError, ValueError):
            # Enhanced fallback using pogonion-centered approach
            pogonion = landmarks[152]
            
            # Create proportional chin area based on face geometry
            face_width = np.max(landmarks[:, 0]) - np.min(landmarks[:, 0])
            chin_width = int(0.15 * face_width)    # 15% of face width
            chin_height = int(0.08 * image.height) # 8% of image height
            
            # Create elliptical chin area centered on pogonion
            cv2.ellipse(mask, tuple(pogonion), (chin_width, chin_height), 0, 0, 360, 255, -1)
            
            # Apply morphological closing for smooth boundaries
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            return mask
    
    def create_cheeks_mask(self, image: Image.Image, landmarks: np.ndarray) -> np.ndarray:
        """Create anatomically correct cheeks mask for mid-face volume enhancement."""
        try:
            # Create left and right cheek masks using enhanced landmarks
            left_mask = self.create_polygon_mask((image.height, image.width), landmarks, CHEEK_LEFT_ENHANCED)
            right_mask = self.create_polygon_mask((image.height, image.width), landmarks, CHEEK_RIGHT_ENHANCED)
            
            # Combine both cheeks
            combined_mask = cv2.bitwise_or(left_mask, right_mask)
            
            return combined_mask
            
        except (IndexError, ValueError):
            # Improved cheek areas - focus on actual zygomatic bone region
            mask = np.zeros((image.height, image.width), dtype=np.uint8)
            
            # Left cheek - anatomically correct positioning
            left_eye_outer = landmarks[33]    # Left eye outer corner
            left_mouth_corner = landmarks[61] # Left mouth corner
            # Position cheek higher - closer to cheekbone
            left_cheek_x = left_eye_outer[0] - 20  # Slightly outward from eye
            left_cheek_y = left_eye_outer[1] + int(0.4 * (left_mouth_corner[1] - left_eye_outer[1]))
            
            # Right cheek - anatomically correct positioning  
            right_eye_outer = landmarks[362]   # Right eye outer corner
            right_mouth_corner = landmarks[291] # Right mouth corner
            # Position cheek higher - closer to cheekbone
            right_cheek_x = right_eye_outer[0] + 20  # Slightly outward from eye
            right_cheek_y = right_eye_outer[1] + int(0.4 * (right_mouth_corner[1] - right_eye_outer[1]))
            
            # Smaller, more focused cheek areas
            cheek_radius_x = int(0.04 * image.width)   # 4% of image width (smaller)
            cheek_radius_y = int(0.06 * image.height)  # 6% of image height (smaller)
            
            # Draw left cheek (higher on cheekbone)
            cv2.ellipse(mask, (left_cheek_x, left_cheek_y), (cheek_radius_x, cheek_radius_y), 0, 0, 360, 255, -1)
            
            # Draw right cheek (higher on cheekbone)
            cv2.ellipse(mask, (right_cheek_x, right_cheek_y), (cheek_radius_x, cheek_radius_y), 0, 0, 360, 255, -1)
            
            return mask
    
    def segment_area(self, image: Image.Image, area: str, feather_px: int = 3) -> Tuple[np.ndarray, Optional[Dict]]:
        """
        Segment specified facial area and return mask with metadata.
        
        Args:
            image: Input PIL Image
            area: One of 'lips', 'chin', 'cheeks', 'forehead'
            feather_px: Feathering amount for mask edges
            
        Returns:
            Tuple of (mask_array, metadata_dict)
        """
        # Extract landmarks
        landmarks = self.extract_landmarks(image)
        
        if landmarks is None:
            # No face detected
            empty_mask = np.zeros((image.height, image.width), dtype=np.uint8)
            return empty_mask, {'error': 'No face detected', 'confidence': 0.0}
        
        # Create area-specific mask
        if area == 'lips':
            mask = self.create_lips_mask(image, landmarks)
        elif area == 'forehead':
            mask = self.create_forehead_mask(image, landmarks)
        elif area == 'chin':
            mask = self.create_chin_mask(image, landmarks)
        elif area == 'cheeks':
            mask = self.create_cheeks_mask(image, landmarks)
        else:
            raise ValueError(f"Unsupported area: {area}")
        
        # Refine mask (morphological operations + feathering)
        mask = refine_mask(mask, feather_px=feather_px, morph_kernel=3)
        
        # Calculate metadata
        mask_area = np.sum(mask > 0)
        total_area = mask.shape[0] * mask.shape[1]
        coverage = mask_area / total_area
        
        # Get bounding box
        coords = cv2.findNonZero(mask)
        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            bbox = {'x': int(x), 'y': int(y), 'width': int(w), 'height': int(h)}
        else:
            bbox = {'x': 0, 'y': 0, 'width': 0, 'height': 0}
        
        metadata = {
            'area': area,
            'landmarks_count': len(landmarks),
            'mask_coverage': float(coverage),
            'bbox': bbox,
            'feather_px': feather_px,
            'confidence': 1.0  # Assume good detection if landmarks found
        }
        
        return mask, metadata


# Global parser instance for efficiency
_face_parser = None

def get_face_parser() -> FaceParser:
    """Get singleton face parser instance."""
    global _face_parser
    if _face_parser is None:
        _face_parser = FaceParser()
    return _face_parser


def segment_area(image: Image.Image, area: str, feather_px: int = 3) -> Tuple[Image.Image, Dict]:
    """
    Convenience function to segment facial area and return PIL mask + metadata.
    
    Args:
        image: Input PIL Image
        area: One of 'lips', 'chin', 'cheeks', 'forehead'  
        feather_px: Feathering amount for mask edges
        
    Returns:
        Tuple of (mask_PIL_Image, metadata_dict)
    """
    parser = get_face_parser()
    mask_array, metadata = parser.segment_area(image, area, feather_px)
    mask_image = numpy_to_pil(mask_array)
    
    return mask_image, metadata


def get_supported_areas() -> List[str]:
    """Get list of supported facial areas."""
    return ['lips', 'chin', 'cheeks', 'forehead']


def validate_area(area: str) -> bool:
    """Validate if area is supported."""
    return area in get_supported_areas()
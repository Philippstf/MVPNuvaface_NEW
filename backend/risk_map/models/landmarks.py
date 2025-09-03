"""
Facial Landmark Detection using MediaPipe

Robust face landmark detection with 468-point face mesh for precise
anatomical point identification and coordinate mapping.
"""

import cv2
import numpy as np
import mediapipe as mp
from typing import List, Optional, Tuple, Dict
import logging
from dataclasses import dataclass

from models.schemas import Point, LandmarkResult, NormalizedFace

logger = logging.getLogger(__name__)

@dataclass
class MediaPipeLandmarks:
    """MediaPipe landmark indices for key facial features."""
    
    # Eye landmarks
    LEFT_EYE_INNER = 133
    LEFT_EYE_OUTER = 33
    RIGHT_EYE_INNER = 362
    RIGHT_EYE_OUTER = 263
    LEFT_EYE_CENTER = 468  # Calculated
    RIGHT_EYE_CENTER = 469  # Calculated
    
    # Nose landmarks
    NOSE_TIP = 1
    NOSE_BRIDGE_HIGH = 6
    LEFT_ALAE = 31
    RIGHT_ALAE = 261
    
    # Mouth landmarks
    UPPER_LIP_CENTER = 13
    LOWER_LIP_CENTER = 14
    LEFT_MOUTH_CORNER = 61
    RIGHT_MOUTH_CORNER = 291
    
    # Lip detail points
    UPPER_LIP_PEAKS = [185, 40]  # Cupid's bow peaks
    LOWER_LIP_BOTTOM = 17
    
    # Eyebrow landmarks
    LEFT_EYEBROW_INNER = 70
    LEFT_EYEBROW_CENTER = 107
    LEFT_EYEBROW_PEAK = 105
    RIGHT_EYEBROW_INNER = 300
    RIGHT_EYEBROW_CENTER = 336
    RIGHT_EYEBROW_PEAK = 334
    
    # Chin landmarks
    CHIN_TIP = 175
    LEFT_JAW = 172
    RIGHT_JAW = 397
    
    # Forehead area (calculated from eyebrow points)
    FOREHEAD_CENTER = 9
    LEFT_TEMPLE = 162
    RIGHT_TEMPLE = 389

class FaceLandmarkDetector:
    """Advanced facial landmark detection with MediaPipe Face Mesh."""
    
    def __init__(self):
        """Initialize MediaPipe Face Mesh model."""
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Initialize face mesh with optimized settings
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,  # Better accuracy around eyes and lips
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5
        )
        
        self.landmark_map = MediaPipeLandmarks()
        self._is_initialized = True
        
        logger.info("✅ FaceLandmarkDetector initialized with MediaPipe Face Mesh")
    
    def is_healthy(self) -> bool:
        """Check if the landmark detector is healthy."""
        return self._is_initialized and self.face_mesh is not None
    
    async def detect_landmarks(self, image_data: np.ndarray) -> LandmarkResult:
        """
        Detect facial landmarks from image data.
        
        Args:
            image_data: RGB image array
            
        Returns:
            LandmarkResult with detected landmarks and confidence
        """
        try:
            # Convert to RGB if needed (MediaPipe expects RGB)
            if len(image_data.shape) == 3 and image_data.shape[2] == 3:
                # Assume BGR from OpenCV, convert to RGB
                rgb_image = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = image_data
            
            # Process the image
            results = self.face_mesh.process(rgb_image)
            
            if not results.multi_face_landmarks:
                logger.warning("⚠️ No face landmarks detected")
                return LandmarkResult(
                    success=False,
                    landmarks=[],
                    confidence=0.0,
                    error_message="No face detected in image"
                )
            
            # Extract landmarks from first detected face
            face_landmarks = results.multi_face_landmarks[0]
            
            # Convert normalized coordinates to pixel coordinates
            h, w = rgb_image.shape[:2]
            landmark_points = []
            
            for landmark in face_landmarks.landmark:
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                landmark_points.append(Point(x=float(x), y=float(y)))
            
            # Calculate confidence based on landmark quality
            confidence = self._calculate_landmark_confidence(
                landmark_points, 
                (w, h)
            )
            
            logger.debug(f"🎯 Detected {len(landmark_points)} landmarks with confidence {confidence:.2f}")
            
            return LandmarkResult(
                success=True,
                landmarks=landmark_points,
                confidence=confidence,
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"❌ Landmark detection failed: {str(e)}")
            return LandmarkResult(
                success=False,
                landmarks=[],
                confidence=0.0,
                error_message=str(e)
            )
    
    def get_key_landmarks(self, landmarks: List[Point]) -> Dict[str, Point]:
        """Extract key anatomical landmarks from the full set."""
        if len(landmarks) < 468:
            raise ValueError("Insufficient landmarks for key point extraction")
        
        key_points = {}
        
        # Eye points
        key_points["left_eye_inner"] = landmarks[self.landmark_map.LEFT_EYE_INNER]
        key_points["left_eye_outer"] = landmarks[self.landmark_map.LEFT_EYE_OUTER]
        key_points["right_eye_inner"] = landmarks[self.landmark_map.RIGHT_EYE_INNER]
        key_points["right_eye_outer"] = landmarks[self.landmark_map.RIGHT_EYE_OUTER]
        
        # Calculate eye centers
        left_eye_center = Point(
            x=(key_points["left_eye_inner"].x + key_points["left_eye_outer"].x) / 2,
            y=(key_points["left_eye_inner"].y + key_points["left_eye_outer"].y) / 2
        )
        right_eye_center = Point(
            x=(key_points["right_eye_inner"].x + key_points["right_eye_outer"].x) / 2,
            y=(key_points["right_eye_inner"].y + key_points["right_eye_outer"].y) / 2
        )
        key_points["left_eye_center"] = left_eye_center
        key_points["right_eye_center"] = right_eye_center
        
        # Nose points
        key_points["nose_tip"] = landmarks[self.landmark_map.NOSE_TIP]
        key_points["nose_bridge_high"] = landmarks[self.landmark_map.NOSE_BRIDGE_HIGH]
        key_points["left_alae"] = landmarks[self.landmark_map.LEFT_ALAE]
        key_points["right_alae"] = landmarks[self.landmark_map.RIGHT_ALAE]
        
        # Mouth points
        key_points["upper_lip_center"] = landmarks[self.landmark_map.UPPER_LIP_CENTER]
        key_points["lower_lip_center"] = landmarks[self.landmark_map.LOWER_LIP_CENTER]
        key_points["left_mouth_corner"] = landmarks[self.landmark_map.LEFT_MOUTH_CORNER]
        key_points["right_mouth_corner"] = landmarks[self.landmark_map.RIGHT_MOUTH_CORNER]
        
        # Cupid's bow peaks
        key_points["left_cupids_bow"] = landmarks[self.landmark_map.UPPER_LIP_PEAKS[0]]
        key_points["right_cupids_bow"] = landmarks[self.landmark_map.UPPER_LIP_PEAKS[1]]
        
        # Eyebrow points
        key_points["left_eyebrow_inner"] = landmarks[self.landmark_map.LEFT_EYEBROW_INNER]
        key_points["left_eyebrow_center"] = landmarks[self.landmark_map.LEFT_EYEBROW_CENTER]
        key_points["left_eyebrow_peak"] = landmarks[self.landmark_map.LEFT_EYEBROW_PEAK]
        key_points["right_eyebrow_inner"] = landmarks[self.landmark_map.RIGHT_EYEBROW_INNER]
        key_points["right_eyebrow_center"] = landmarks[self.landmark_map.RIGHT_EYEBROW_CENTER]
        key_points["right_eyebrow_peak"] = landmarks[self.landmark_map.RIGHT_EYEBROW_PEAK]
        
        # Calculate eyebrow midpoint for forehead reference
        eyebrow_midpoint = Point(
            x=(key_points["left_eyebrow_center"].x + key_points["right_eyebrow_center"].x) / 2,
            y=(key_points["left_eyebrow_center"].y + key_points["right_eyebrow_center"].y) / 2
        )
        key_points["eyebrow_center_midpoint"] = eyebrow_midpoint
        
        # Chin points
        key_points["chin_tip"] = landmarks[self.landmark_map.CHIN_TIP]
        key_points["left_jaw"] = landmarks[self.landmark_map.LEFT_JAW]
        key_points["right_jaw"] = landmarks[self.landmark_map.RIGHT_JAW]
        
        # Forehead calculated points
        key_points["forehead_center"] = landmarks[self.landmark_map.FOREHEAD_CENTER]
        key_points["left_temple"] = landmarks[self.landmark_map.LEFT_TEMPLE]
        key_points["right_temple"] = landmarks[self.landmark_map.RIGHT_TEMPLE]
        
        return key_points
    
    def _calculate_landmark_confidence(self, landmarks: List[Point], image_shape: Tuple[int, int]) -> float:
        """Calculate confidence score based on landmark quality."""
        if len(landmarks) < 100:
            return 0.1
        
        w, h = image_shape
        confidence_factors = []
        
        # Check if face is well-centered
        face_center_x = np.mean([lm.x for lm in landmarks])
        face_center_y = np.mean([lm.y for lm in landmarks])
        center_score = 1.0 - min(1.0, abs(face_center_x - w/2) / (w/4))
        center_score *= 1.0 - min(1.0, abs(face_center_y - h/2) / (h/4))
        confidence_factors.append(center_score)
        
        # Check landmark spread (face not too small/large)
        landmark_spread = np.std([lm.x for lm in landmarks]) + np.std([lm.y for lm in landmarks])
        spread_score = min(1.0, landmark_spread / (w * 0.1))
        confidence_factors.append(spread_score)
        
        # Check for reasonable face proportions
        if len(landmarks) >= 468:
            try:
                # Eye-to-mouth ratio check
                eye_y = (landmarks[133].y + landmarks[362].y) / 2  # Eye level
                mouth_y = landmarks[13].y  # Upper lip
                eye_mouth_distance = abs(mouth_y - eye_y)
                
                # Reasonable proportion check
                if eye_mouth_distance > h * 0.05:  # At least 5% of image height
                    proportion_score = min(1.0, eye_mouth_distance / (h * 0.15))
                    confidence_factors.append(proportion_score)
                else:
                    confidence_factors.append(0.3)  # Face too small
            except:
                confidence_factors.append(0.5)  # Default if calculation fails
        
        # Check completeness (all landmarks detected)
        completeness_score = len(landmarks) / 468.0
        confidence_factors.append(completeness_score)
        
        # Combined confidence score
        overall_confidence = np.mean(confidence_factors)
        return max(0.1, min(1.0, overall_confidence))
    
    async def warm_up(self):
        """Warm up the model with a dummy image."""
        try:
            # Create a dummy image for warm-up
            dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
            dummy_image.fill(128)  # Gray image
            
            # Add a simple face-like pattern
            cv2.circle(dummy_image, (320, 200), 80, (200, 180, 160), -1)  # Face
            cv2.circle(dummy_image, (300, 180), 10, (50, 50, 50), -1)    # Left eye
            cv2.circle(dummy_image, (340, 180), 10, (50, 50, 50), -1)    # Right eye
            cv2.ellipse(dummy_image, (320, 220), (20, 10), 0, 0, 180, (100, 50, 50), -1)  # Mouth
            
            # Process dummy image
            await self.detect_landmarks(dummy_image)
            logger.info("🔥 Landmark detector warmed up successfully")
            
        except Exception as e:
            logger.warning(f"⚠️ Warm-up failed: {str(e)}")
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.face_mesh:
                self.face_mesh.close()
            logger.info("✅ Landmark detector cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {str(e)}")
    
    def visualize_landmarks(self, image: np.ndarray, landmarks: List[Point], key_points_only: bool = False) -> np.ndarray:
        """
        Visualize landmarks on image for debugging.
        
        Args:
            image: Input image
            landmarks: Detected landmarks
            key_points_only: If True, only show key anatomical points
            
        Returns:
            Image with landmarks drawn
        """
        result_image = image.copy()
        
        if key_points_only and len(landmarks) >= 468:
            # Draw only key points
            key_landmarks = self.get_key_landmarks(landmarks)
            
            colors = {
                'eye': (0, 255, 0),      # Green
                'nose': (255, 0, 0),     # Red  
                'mouth': (0, 0, 255),    # Blue
                'eyebrow': (255, 255, 0), # Yellow
                'chin': (255, 0, 255),   # Magenta
                'forehead': (0, 255, 255) # Cyan
            }
            
            # Draw key points with labels
            for name, point in key_landmarks.items():
                color = colors.get(name.split('_')[0], (255, 255, 255))
                cv2.circle(result_image, (int(point.x), int(point.y)), 3, color, -1)
                cv2.putText(result_image, name[:8], 
                           (int(point.x) + 5, int(point.y) - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1)
        else:
            # Draw all landmarks
            for i, landmark in enumerate(landmarks):
                cv2.circle(result_image, (int(landmark.x), int(landmark.y)), 1, (0, 255, 0), -1)
        
        return result_image
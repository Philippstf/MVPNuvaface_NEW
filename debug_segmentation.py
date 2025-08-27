#!/usr/bin/env python3
"""
Debug-Script für die Gesichtssegmentierung
"""

import sys
import os
import base64
import io
from PIL import Image
import cv2
import numpy as np

# Add project path
sys.path.append('.')

def test_image_processing(image_path):
    """Test der Bildverarbeitung Schritt für Schritt."""
    
    print(f"[DEBUG] Teste Bild: {image_path}")
    
    # 1. Bild laden
    try:
        img = Image.open(image_path)
        print(f"[OK] Bild geladen: {img.size}, Mode: {img.mode}")
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
            print(f"[OK] Zu RGB konvertiert")
            
    except Exception as e:
        print(f"[ERROR] Fehler beim Laden: {e}")
        return False
    
    # 2. MediaPipe Test
    try:
        import mediapipe as mp
        
        face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        print("[OK] MediaPipe FaceMesh initialisiert")
        
        # Convert PIL to OpenCV
        cv_image = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        print(f"[OK] OpenCV Bild: {cv_image.shape}")
        
        # Process with MediaPipe
        results = face_mesh.process(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
        
        if results.multi_face_landmarks:
            face_landmarks = results.multi_face_landmarks[0]
            landmark_count = len(face_landmarks.landmark)
            print(f"[OK] Gesicht erkannt! {landmark_count} Landmarks gefunden")
            
            # Test landmark extraction
            h, w = img.height, img.width
            landmarks = []
            for landmark in face_landmarks.landmark:
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                landmarks.append([x, y])
            
            landmarks_array = np.array(landmarks)
            print(f"[OK] Landmarks konvertiert: {landmarks_array.shape}")
            
            # Test specific area (lips)
            from engine.parsing import LIPS_OUTER
            if len(LIPS_OUTER) > 0:
                lips_points = landmarks_array[LIPS_OUTER]
                print(f"[OK] Lippen-Landmarks: {lips_points.shape}")
                
                # Create simple mask
                mask = np.zeros((h, w), dtype=np.uint8)
                cv2.fillPoly(mask, [lips_points], 255)
                mask_area = np.sum(mask > 0)
                print(f"[OK] Lippen-Maske erstellt: {mask_area} Pixel")
                
                return True
            else:
                print("[ERROR] Keine Lippen-Landmarks definiert")
                return False
                
        else:
            print("[ERROR] Kein Gesicht erkannt!")
            print("Mögliche Ursachen:")
            print("- Gesicht zu klein/groß")
            print("- Schlechte Bildqualität") 
            print("- Gesicht nicht frontal")
            print("- Zu wenig Kontrast")
            return False
            
    except ImportError as e:
        print(f"[ERROR] MediaPipe Import-Fehler: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] MediaPipe Verarbeitungsfehler: {e}")
        return False

def test_api_segment(image_path):
    """Test der API-Segmentierung."""
    
    print(f"\n[DEBUG] Teste API-Segmentierung...")
    
    try:
        # Convert image to base64
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
            base64_str = base64.b64encode(image_bytes).decode('utf-8')
        
        print(f"[OK] Base64 konvertiert: {len(base64_str)} Zeichen")
        
        # Test with engine directly
        from engine.parsing import segment_area
        from engine.utils import load_image
        
        # Load image
        img = load_image(base64_str)
        print(f"[OK] Bild mit engine.utils geladen: {img.size}")
        
        # Test segmentation
        mask_img, metadata = segment_area(img, "lips", feather_px=3)
        print(f"[OK] Segmentierung erfolgreich!")
        print(f"Metadata: {metadata}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] API-Segmentierung Fehler: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Test mit einem Beispielbild
    test_image = "test_face.jpg"  # Pfad zu Ihrem Testbild
    
    print("=" * 60)
    print("NUVAFACE SEGMENTIERUNG DEBUG")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        test_image = sys.argv[1]
    
    if os.path.exists(test_image):
        success1 = test_image_processing(test_image)
        success2 = test_api_segment(test_image)
        
        if success1 and success2:
            print("\n[SUCCESS] Alle Tests erfolgreich!")
        else:
            print(f"\n[WARNING] Tests fehlgeschlagen")
    else:
        print(f"[ERROR] Testbild nicht gefunden: {test_image}")
        print("Verwendung: python debug_segmentation.py <pfad_zum_bild>")
#!/usr/bin/env python3
"""
NuvaFace Core Functionality Demo
Demonstrates the core components without requiring heavy ML dependencies.
"""

import sys
import os
import base64
import io
from PIL import Image
import numpy as np

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_sample_image():
    """Create a simple test image."""
    # Create a 256x256 RGB image
    img = Image.new('RGB', (256, 256), color='lightblue')
    
    # Add a simple face-like circle
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    
    # Face outline
    draw.ellipse([50, 50, 200, 200], fill='peachpuff', outline='black', width=2)
    
    # Eyes
    draw.ellipse([80, 100, 100, 120], fill='black')
    draw.ellipse([150, 100, 170, 120], fill='black')
    
    # Nose
    draw.ellipse([120, 130, 130, 150], fill='pink')
    
    # Mouth
    draw.ellipse([100, 160, 150, 175], fill='red')
    
    return img

def test_utils():
    """Test utility functions."""
    print("Testing engine.utils...")
    
    try:
        from engine.utils import (
            pil_to_numpy, numpy_to_pil, 
            create_circular_mask, feather_mask,
            image_to_base64, set_seed
        )
        
        # Create test image
        img = create_sample_image()
        print(f"✓ Created test image: {img.size}")
        
        # Test PIL <-> numpy conversion
        img_array = pil_to_numpy(img)
        img_restored = numpy_to_pil(img_array)
        print(f"✓ PIL <-> numpy conversion: {img_array.shape}")
        
        # Test base64 conversion
        base64_str = image_to_base64(img)
        print(f"✓ Base64 conversion: {len(base64_str)} chars")
        
        # Test mask creation
        mask = create_circular_mask((256, 256), (128, 128), 50)
        print(f"✓ Circular mask created: {mask.shape}")
        
        # Test mask feathering
        feathered = feather_mask(mask, 5)
        print(f"✓ Mask feathering: {feathered.shape}")
        
        # Test seed setting
        set_seed(42)
        print("✓ Seed setting")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error in utils: {e}")
        return False
    except Exception as e:
        print(f"✗ Error in utils: {e}")
        return False

def test_schemas():
    """Test API schemas."""
    print("\nTesting api.schemas...")
    
    try:
        from api.schemas import (
            AreaType, PipelineType, SegmentRequest, 
            HealthResponse, get_prompt_for_area
        )
        
        # Test enums
        print(f"✓ Areas: {[area.value for area in AreaType]}")
        print(f"✓ Pipelines: {[pipe.value for pipe in PipelineType]}")
        
        # Test prompt generation
        prompt = get_prompt_for_area(AreaType.LIPS, "en")
        print(f"✓ Prompt for lips: '{prompt[:50]}...'")
        
        # Test request model
        request_data = {
            "image": "dummy_base64",
            "area": "lips",
            "feather_px": 3
        }
        
        seg_request = SegmentRequest(**request_data)
        print(f"✓ Segment request: {seg_request.area}")
        
        # Test health response
        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            models_loaded={},
            gpu_available=False
        )
        print(f"✓ Health response: {health.status}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error in schemas: {e}")
        return False
    except Exception as e:
        print(f"✗ Error in schemas: {e}")
        return False

def test_parsing_basic():
    """Test basic parsing functionality (without MediaPipe)."""
    print("\nTesting engine.parsing (basic)...")
    
    try:
        from engine.parsing import (
            get_supported_areas, validate_area,
            LIPS_OUTER, EYEBROW_LEFT
        )
        
        # Test area validation
        areas = get_supported_areas()
        print(f"✓ Supported areas: {areas}")
        
        # Test validation
        valid = validate_area("lips")
        invalid = validate_area("nose")
        print(f"✓ Area validation: lips={valid}, nose={invalid}")
        
        # Test landmark constants
        print(f"✓ Lips landmarks count: {len(LIPS_OUTER)}")
        print(f"✓ Eyebrow landmarks count: {len(EYEBROW_LEFT)}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error in parsing: {e}")
        return False
    except Exception as e:
        print(f"✗ Error in parsing: {e}")
        return False

def test_quality_control_basic():
    """Test basic QC functionality (without heavy models)."""
    print("\nTesting engine.qc (basic)...")
    
    try:
        from engine.qc import QualityController, set_quality_thresholds
        
        # Create QC instance
        qc_controller = QualityController()
        print("✓ QualityController created")
        
        # Test threshold setting
        set_quality_thresholds(id_threshold=0.5, ssim_threshold=0.99)
        print(f"✓ Thresholds set: ID={qc_controller.id_similarity_threshold}, SSIM={qc_controller.ssim_threshold}")
        
        # Test BRISQUE on sample image
        img = create_sample_image()
        brisque_score = qc_controller.brisque_score(img)
        print(f"✓ BRISQUE score: {brisque_score:.2f}")
        
        # Test should_retry logic
        good_qc = {
            'id_warning': False,
            'ssim_warning': False,
            'brisque_degradation': 5.0
        }
        should_retry, reason = qc_controller.should_retry(good_qc)
        print(f"✓ Retry logic: {should_retry} - {reason}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error in qc: {e}")
        return False
    except Exception as e:
        print(f"✗ Error in qc: {e}")
        return False

def test_project_structure():
    """Test project structure and file organization."""
    print("\nTesting project structure...")
    
    required_files = [
        'install.sh',
        'api/main.py',
        'api/schemas.py',
        'engine/utils.py',
        'engine/parsing.py',
        'engine/controls.py',
        'engine/edit_sd.py',
        'engine/edit_ip2p.py',
        'engine/qc.py',
        'models/__init__.py',
        'ui/index.html',
        'ui/app.js',
        'ui/styles.css',
        'docs/README.md',
        'docs/PROMPTS.md',
        'docs/ASSUMPTIONS.md',
        'tests/test_qc.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"✗ Missing files: {missing_files}")
        return False
    else:
        print(f"✓ All {len(required_files)} required files present")
        return True

def demo_full_workflow():
    """Demonstrate a complete workflow simulation."""
    print("\n" + "="*60)
    print("NUVAFACE CORE FUNCTIONALITY DEMO")
    print("="*60)
    
    # Test each component
    tests = [
        ("Project Structure", test_project_structure),
        ("Utility Functions", test_utils),
        ("API Schemas", test_schemas),
        ("Parsing Module", test_parsing_basic),
        ("Quality Control", test_quality_control_basic),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*40}")
        print(f"Testing: {test_name}")
        print('='*40)
        
        success = test_func()
        results.append((test_name, success))
        
        if success:
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    # Summary
    print(f"\n{'='*60}")
    print("DEMO SUMMARY")
    print('='*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All core components are working correctly!")
        print("\nNext steps:")
        print("1. Run './install.sh' to install ML dependencies")
        print("2. Start the server: 'uvicorn api.main:app --reload'")
        print("3. Open ui/index.html in your browser")
        print("4. Test with a real face image")
    else:
        print(f"\n⚠️  {total - passed} components need attention before proceeding.")
    
    return passed == total

if __name__ == "__main__":
    demo_full_workflow()
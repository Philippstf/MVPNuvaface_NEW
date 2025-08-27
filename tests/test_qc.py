"""
Test suite for quality control functionality.
Tests identity preservation, off-mask protection, and overall quality assessment.
"""

import pytest
import numpy as np
from PIL import Image
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.qc import (
    QualityController, 
    qc, 
    comprehensive_assessment,
    validate_result_quality,
    set_quality_thresholds
)
from engine.utils import create_circular_mask


class TestQualityController:
    """Test suite for QualityController class."""
    
    @pytest.fixture
    def sample_images(self):
        """Create sample test images."""
        # Create a simple test image (RGB)
        original = Image.new('RGB', (256, 256), color='white')
        
        # Create a slightly modified version
        edited = Image.new('RGB', (256, 256), color='lightgray')
        
        # Create a mask
        mask_array = create_circular_mask((256, 256), (128, 128), 50)
        mask = Image.fromarray(mask_array, 'L')
        
        return original, edited, mask
    
    @pytest.fixture
    def qc_controller(self):
        """Create QualityController instance."""
        return QualityController()
    
    def test_identity_similarity_identical_images(self, qc_controller, sample_images):
        """Test identity similarity with identical images."""
        original, _, _ = sample_images
        
        # Test with identical images (should be perfect similarity)
        similarity = qc_controller.identity_similarity(original, original)
        
        # Note: Without faces in the image, ArcFace will return 0.0
        # This is expected behavior for test images
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0
    
    def test_ssim_off_mask_identical_images(self, qc_controller, sample_images):
        """Test SSIM off-mask with identical images."""
        original, _, mask = sample_images
        
        # Test with identical images (should be perfect SSIM)
        ssim_score = qc_controller.ssim_off_mask(original, original, mask)
        
        assert isinstance(ssim_score, float)
        assert ssim_score >= 0.9  # Should be very high for identical images
    
    def test_ssim_off_mask_different_images(self, qc_controller, sample_images):
        """Test SSIM off-mask with different images."""
        original, edited, mask = sample_images
        
        ssim_score = qc_controller.ssim_off_mask(original, edited, mask)
        
        assert isinstance(ssim_score, float)
        assert 0.0 <= ssim_score <= 1.0
        # Should be lower than identical images but still reasonable
        assert ssim_score >= 0.5
    
    def test_brisque_score(self, qc_controller, sample_images):
        """Test BRISQUE quality score calculation."""
        original, _, _ = sample_images
        
        score = qc_controller.brisque_score(original)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 100.0
    
    def test_comprehensive_qc(self, qc_controller, sample_images):
        """Test comprehensive quality control assessment."""
        original, edited, mask = sample_images
        
        qc_results = qc_controller.comprehensive_qc(original, edited, mask)
        
        # Check that all expected keys are present
        expected_keys = [
            'id_similarity', 'id_warning',
            'ssim_off_mask', 'ssim_warning',
            'brisque_original', 'brisque_edited', 'brisque_degradation',
            'lpips_score', 'quality_passed'
        ]
        
        for key in expected_keys:
            assert key in qc_results
        
        # Check data types
        assert isinstance(qc_results['id_similarity'], float)
        assert isinstance(qc_results['id_warning'], bool)
        assert isinstance(qc_results['ssim_off_mask'], float)
        assert isinstance(qc_results['ssim_warning'], bool)
        assert isinstance(qc_results['quality_passed'], bool)
    
    def test_should_retry_logic(self, qc_controller):
        """Test retry logic based on quality results."""
        # Test case: Good quality (no retry needed)
        good_qc = {
            'id_warning': False,
            'ssim_warning': False,
            'brisque_degradation': 5.0
        }
        
        should_retry, reason = qc_controller.should_retry(good_qc)
        assert should_retry == False
        assert reason == "Quality checks passed"
        
        # Test case: ID warning (should retry)
        id_warning_qc = {
            'id_warning': True,
            'ssim_warning': False,
            'brisque_degradation': 5.0
        }
        
        should_retry, reason = qc_controller.should_retry(id_warning_qc)
        assert should_retry == True
        assert "Identity" in reason
        
        # Test case: SSIM warning (should retry)
        ssim_warning_qc = {
            'id_warning': False,
            'ssim_warning': True,
            'brisque_degradation': 5.0
        }
        
        should_retry, reason = qc_controller.should_retry(ssim_warning_qc)
        assert should_retry == True
        assert "Off-target" in reason


class TestQualityUtilityFunctions:
    """Test utility functions for quality control."""
    
    @pytest.fixture
    def sample_images(self):
        """Create sample test images."""
        original = Image.new('RGB', (256, 256), color='white')
        edited = Image.new('RGB', (256, 256), color='lightgray')
        mask_array = create_circular_mask((256, 256), (128, 128), 50)
        mask = Image.fromarray(mask_array, 'L')
        return original, edited, mask
    
    def test_qc_function(self, sample_images):
        """Test the simplified qc() function."""
        original, edited, mask = sample_images
        
        id_sim, ssim_score = qc(original, edited, mask)
        
        assert isinstance(id_sim, float)
        assert isinstance(ssim_score, float)
        assert 0.0 <= id_sim <= 1.0
        assert 0.0 <= ssim_score <= 1.0
    
    def test_comprehensive_assessment_function(self, sample_images):
        """Test the comprehensive_assessment() function."""
        original, edited, mask = sample_images
        
        results = comprehensive_assessment(original, edited, mask)
        
        assert isinstance(results, dict)
        assert 'id_similarity' in results
        assert 'ssim_off_mask' in results
        assert 'quality_passed' in results
    
    def test_validate_result_quality(self, sample_images):
        """Test result quality validation."""
        original, _, mask = sample_images
        
        # Test with identical images (should pass)
        is_valid = validate_result_quality(original, original, mask, strict=False)
        # Note: May fail due to no faces in test images, but should not crash
        assert isinstance(is_valid, bool)
        
        # Test with strict mode
        is_valid_strict = validate_result_quality(original, original, mask, strict=True)
        assert isinstance(is_valid_strict, bool)
    
    def test_set_quality_thresholds(self):
        """Test quality threshold configuration."""
        # Test setting new thresholds
        set_quality_thresholds(id_threshold=0.5, ssim_threshold=0.99)
        
        # Verify thresholds were set
        from engine.qc import get_quality_controller
        controller = get_quality_controller()
        
        assert controller.id_similarity_threshold == 0.5
        assert controller.ssim_threshold == 0.99
        
        # Reset to defaults
        set_quality_thresholds(id_threshold=0.35, ssim_threshold=0.98)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_images(self):
        """Test with empty/invalid images."""
        # Create minimal images
        tiny_img = Image.new('RGB', (1, 1), color='white')
        tiny_mask = Image.new('L', (1, 1), color='white')
        
        # Should not crash, but may return low scores
        id_sim, ssim_score = qc(tiny_img, tiny_img, tiny_mask)
        assert isinstance(id_sim, float)
        assert isinstance(ssim_score, float)
    
    def test_size_mismatch_handling(self):
        """Test handling of mismatched image sizes."""
        img1 = Image.new('RGB', (100, 100), color='white')
        img2 = Image.new('RGB', (200, 200), color='white')
        mask = Image.new('L', (100, 100), color='white')
        
        # Should handle size mismatch gracefully
        try:
            id_sim, ssim_score = qc(img1, img2, mask)
            # If it doesn't crash, check that values are reasonable
            assert isinstance(id_sim, float)
            assert isinstance(ssim_score, float)
        except Exception as e:
            # Size mismatch should be handled, but if it raises an exception,
            # it should be a clear error message
            assert "size" in str(e).lower() or "shape" in str(e).lower()
    
    def test_grayscale_image_handling(self):
        """Test handling of grayscale images."""
        # Create grayscale image
        gray_img = Image.new('L', (256, 256), color='white')
        rgb_img = gray_img.convert('RGB')
        mask = Image.new('L', (256, 256), color='white')
        
        # Should handle gracefully by converting to RGB
        id_sim, ssim_score = qc(rgb_img, rgb_img, mask)
        assert isinstance(id_sim, float)
        assert isinstance(ssim_score, float)


class TestPerformance:
    """Test performance characteristics."""
    
    def test_processing_speed(self):
        """Test that quality control runs in reasonable time."""
        import time
        
        # Create reasonably sized test images
        original = Image.new('RGB', (512, 512), color='white')
        edited = Image.new('RGB', (512, 512), color='lightgray')
        mask_array = create_circular_mask((512, 512), (256, 256), 100)
        mask = Image.fromarray(mask_array, 'L')
        
        start_time = time.time()
        id_sim, ssim_score = qc(original, edited, mask)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (less than 10 seconds)
        assert processing_time < 10.0
        print(f"QC processing time: {processing_time:.2f} seconds")
    
    def test_memory_usage(self):
        """Test that quality control doesn't consume excessive memory."""
        # Create large images to test memory handling
        large_img = Image.new('RGB', (1024, 1024), color='white')
        mask_array = create_circular_mask((1024, 1024), (512, 512), 200)
        large_mask = Image.fromarray(mask_array, 'L')
        
        # Should not crash or use excessive memory
        try:
            id_sim, ssim_score = qc(large_img, large_img, large_mask)
            assert isinstance(id_sim, float)
            assert isinstance(ssim_score, float)
        except MemoryError:
            pytest.skip("Insufficient memory for large image test")


def create_test_data():
    """Create simple test data for development."""
    # Create a basic test image
    test_img = Image.new('RGB', (256, 256), color='lightblue')
    
    # Add some simple patterns
    from PIL import ImageDraw
    draw = ImageDraw.Draw(test_img)
    draw.ellipse([50, 50, 200, 200], fill='white', outline='black')
    
    # Save test image
    os.makedirs('tests/data', exist_ok=True)
    test_img.save('tests/data/test_face.png')
    
    print("Created test data in tests/data/")


if __name__ == "__main__":
    # Create test data if running directly
    create_test_data()
    
    # Run tests
    pytest.main([__file__, "-v"])
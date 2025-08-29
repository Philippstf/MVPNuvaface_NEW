"""
Test script for Gemini worker fixes
"""
import subprocess
import sys
import os
from pathlib import Path

def test_gemini_worker():
    """Test the fixed gemini_worker.py"""
    
    # Paths
    worker_script = Path("gemini_worker.py")
    test_image = Path("testbild.png")
    output_path = Path("test_output.png")
    
    # Check if test image exists
    if not test_image.exists():
        print(f"ERROR: Test image {test_image} not found!")
        return False
    
    # Prepare command
    command = [
        sys.executable,  # Use current Python
        str(worker_script),
        "--input", str(test_image),
        "--output", str(output_path),
        "--volume", "2.0",
        "--area", "lips"
    ]
    
    print("Testing Gemini worker with fixed configuration...")
    print(f"Command: {' '.join(command)}")
    print("-" * 60)
    
    try:
        # Run the worker
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print("STDOUT:")
        print(process.stdout)
        print("\nSTDERR:")
        print(process.stderr)
        
        # Check if output was created
        if output_path.exists():
            print(f"\n✅ SUCCESS: Output image created at {output_path}")
            print(f"File size: {output_path.stat().st_size} bytes")
            return True
        else:
            print(f"\n❌ FAILED: No output image created")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n❌ FAILED: Process timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False

if __name__ == "__main__":
    # Set environment variable if not set
    if not os.getenv('GOOGLE_API_KEY'):
        print("WARNING: GOOGLE_API_KEY not set in environment")
        print("Please set it or the test will fail")
    
    success = test_gemini_worker()
    sys.exit(0 if success else 1)
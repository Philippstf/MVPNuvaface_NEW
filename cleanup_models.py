#!/usr/bin/env python3
"""
Clean up downloaded model weights to free disk space.
"""

import os
import shutil
import sys

def cleanup_huggingface_models():
    """Remove downloaded HuggingFace models to save disk space."""
    
    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    
    if not os.path.exists(cache_dir):
        print("No HuggingFace cache directory found.")
        return
    
    models_to_remove = [
        "models--runwayml--stable-diffusion-inpainting",
        "models--lllyasviel--sd-controlnet-canny", 
        "models--lllyasviel--sd-controlnet-depth",
        "models--lllyasviel--Annotators"
    ]
    
    total_freed = 0
    
    for model in models_to_remove:
        model_path = os.path.join(cache_dir, model)
        
        if os.path.exists(model_path):
            # Calculate size before deletion
            size = 0
            for dirpath, dirnames, filenames in os.walk(model_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        size += os.path.getsize(filepath)
                    except OSError:
                        pass
            
            size_mb = size / (1024 * 1024)
            print(f"Removing {model}: {size_mb:.1f} MB")
            
            try:
                shutil.rmtree(model_path)
                total_freed += size_mb
                print(f"[OK] Removed {model}")
            except Exception as e:
                print(f"[ERROR] Failed to remove {model}: {e}")
        else:
            print(f"• {model} not found")
    
    print(f"\nTotal disk space freed: {total_freed:.1f} MB")

if __name__ == "__main__":
    print("=" * 50)
    print("CLEANUP NUVAFACE MODEL WEIGHTS")
    print("=" * 50)
    
    cleanup_huggingface_models()
    
    print("\nCleanup complete!")
    print("Note: Models will be re-downloaded on next use.")
# engine/edit_gemini.py
"""
This module orchestrates the call to the isolated Gemini worker script.
"""
import os
import subprocess
import uuid
from PIL import Image
import logging
import sys
import io
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# --- Configuration ---
# Define paths for temporary files and the worker environment
ROOT_DIR = Path(__file__).parent.parent
TEMP_INPUT_DIR = ROOT_DIR / 'temp_inputs'
TEMP_OUTPUT_DIR = ROOT_DIR / 'temp_outputs'

# Try to find the Python executable - check multiple possible locations
possible_pythons = [
    ROOT_DIR / 'nuvaface_env' / 'Scripts' / 'python.exe',  # Your current env
    ROOT_DIR / 'gemini_env' / 'Scripts' / 'python.exe',     # Alternative env
    sys.executable  # Fallback to current Python
]

GEMINI_ENV_PYTHON = None
for python_path in possible_pythons:
    if Path(python_path).exists():
        GEMINI_ENV_PYTHON = python_path
        break

if not GEMINI_ENV_PYTHON:
    GEMINI_ENV_PYTHON = sys.executable  # Use current Python as last resort

WORKER_SCRIPT = ROOT_DIR / 'gemini_worker.py'

os.makedirs(TEMP_INPUT_DIR, exist_ok=True)
os.makedirs(TEMP_OUTPUT_DIR, exist_ok=True)

async def generate_gemini_simulation(
    original_image: Image.Image, 
    volume_ml: float,
    area: str = "lips",
    mask_image: Image.Image = None
) -> Image.Image:
    """
    Generates an aesthetic simulation by calling the gemini_worker.py script
    in its own dedicated virtual environment.
    """
    if not Path(GEMINI_ENV_PYTHON).exists():
        raise FileNotFoundError(f"Python executable not found at {GEMINI_ENV_PYTHON}")
    if not WORKER_SCRIPT.exists():
        raise FileNotFoundError(f"Gemini worker script not found at {WORKER_SCRIPT}")

    session_id = str(uuid.uuid4())
    input_path = TEMP_INPUT_DIR / f"{session_id}_input.png"
    mask_path = TEMP_INPUT_DIR / f"{session_id}_mask.png"
    output_path = TEMP_OUTPUT_DIR / f"{session_id}_output.png"
    
    logger.info(f"🔍 DEBUG: Session ID: {session_id}")
    logger.info(f"🔍 DEBUG: Area parameter: '{area}'")
    logger.info(f"🔍 DEBUG: Volume: {volume_ml}ml")
    
    # Save original image
    original_image.save(input_path, "PNG")
    logger.info(f"🔍 DEBUG: Saved input image to: {input_path}")
    
    # Save mask if provided
    mask_arg = ""
    if mask_image is not None:
        mask_image.save(mask_path, "PNG")
        mask_arg = f"--mask {mask_path}"
        logger.info(f"🔍 DEBUG: Saved mask image to: {mask_path}")
        logger.info(f"🔍 DEBUG: Mask image mode: {mask_image.mode}, size: {mask_image.size}")
    else:
        logger.info(f"🔍 DEBUG: No mask image provided!")

    try:
        command = [
            str(GEMINI_ENV_PYTHON),
            str(WORKER_SCRIPT),
            "--input", str(input_path),
            "--output", str(output_path),
            "--volume", str(volume_ml),
            "--area", str(area),
        ]
        
        # Add mask if provided
        if mask_image is not None:
            command.extend(["--mask", str(mask_path)])
            logger.info(f"🔍 DEBUG: Added mask argument to command")
        
        logger.info(f"🔍 DEBUG: Executing Gemini worker command: {' '.join(command)}")
        
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True, # This will raise a CalledProcessError if the script fails
            encoding='utf-8'
        )
        
        logger.info(f"Gemini worker stdout: {process.stdout}")
        
        # Extract image data from stdout instead of file
        stdout = process.stdout
        if "IMAGE_DATA_START:" in stdout and ":IMAGE_DATA_END" in stdout:
            # Extract base64 image data from stdout
            start_marker = "IMAGE_DATA_START:"
            end_marker = ":IMAGE_DATA_END"
            start_idx = stdout.find(start_marker) + len(start_marker)
            end_idx = stdout.find(end_marker)
            
            if start_idx > len(start_marker) and end_idx > start_idx:
                base64_data = stdout[start_idx:end_idx].strip()
                
                # Decode base64 to image
                import base64
                image_bytes = base64.b64decode(base64_data)
                result_image = Image.open(io.BytesIO(image_bytes))
                
                # Convert to RGB if needed
                if result_image.mode != 'RGB':
                    result_image = result_image.convert('RGB')
                
                logger.info("Successfully extracted image from stdout")
                return result_image
            else:
                raise RuntimeError("Could not extract image data from stdout")
        else:
            raise RuntimeError(f"Worker script did not return image data. Stdout: {stdout[:500]}")

    except subprocess.CalledProcessError as e:
        logger.error(f"Gemini worker script failed with code {e.returncode}:\n{e.stderr}")
        raise RuntimeError(f"Gemini Worker Error: {e.stderr}")
    except Exception as e:
        logger.error(f"Error in generate_gemini_simulation: {e}")
        raise
"""
Firebase Functions wrapper for NuvaFace API
"""
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path to import our modules
sys.path.append(str(Path(__file__).parent.parent))

from firebase_functions import https_fn, options
from flask import Flask, request, jsonify
import logging

# Import our existing API
try:
    from api.main import app as fastapi_app
    from api.main import segment_face, simulate_filler, health_check
except ImportError as e:
    logging.error(f"Could not import API modules: {e}")
    raise

# Create Flask app for Firebase Functions
app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Import and call the health check from FastAPI
        import asyncio
        from api.schemas import HealthResponse
        
        # Create a simple health response
        return jsonify({
            "status": "healthy",
            "version": "2.0.0-firebase",
            "models_loaded": {"segmentation": True, "generation": True},
            "gpu_available": False  # Firebase functions don't have GPU
        })
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/segment', methods=['POST'])
def segment():
    """Face segmentation endpoint"""
    try:
        import asyncio
        from api.schemas import SegmentRequest
        
        data = request.get_json()
        segment_request = SegmentRequest(**data)
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(segment_face(segment_request))
        
        return jsonify(result.dict())
    except Exception as e:
        logger.error(f"Segmentation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/simulate/filler', methods=['POST'])
def simulate_filler_endpoint():
    """Filler simulation endpoint"""
    try:
        import asyncio
        from api.schemas import SimulationRequest
        
        data = request.get_json()
        simulation_request = SimulationRequest(**data)
        
        # Note: This will need to be adapted for Firebase environment
        # as the Gemini worker subprocess approach won't work in serverless
        logger.warning("Gemini simulation not fully supported in Firebase Functions yet")
        return jsonify({"error": "Simulation not available in Firebase environment"}), 501
        
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        return jsonify({"error": str(e)}), 500

# Firebase Function entry point
@https_fn.on_request(
    cors=options.CorsOptions(
        cors_origins=["*"],
        cors_methods=["GET", "POST", "OPTIONS"]
    ),
    memory=options.MemoryOption.MB_1024,
    timeout_sec=300
)
def api(req: https_fn.Request) -> https_fn.Response:
    """Main API function for Firebase"""
    with app.test_request_context(req.path, method=req.method, 
                                  data=req.data, headers=req.headers):
        try:
            response = app.dispatch_request()
            return https_fn.Response(
                response.data,
                status=response.status_code,
                headers=dict(response.headers)
            )
        except Exception as e:
            logger.error(f"API error: {e}")
            return https_fn.Response(
                f"Internal server error: {str(e)}",
                status=500
            )
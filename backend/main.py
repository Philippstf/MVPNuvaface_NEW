"""
Medical AI Assistant Backend Entry Point

This is the main entry point for the Medical AI Assistant backend.
It imports and runs the FastAPI app from the risk_map module.
"""

from risk_map.app import app
import os

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
"""
Medical AI Assistant Backend Entry Point

This is the main entry point for the Medical AI Assistant backend.
It imports and runs the FastAPI app from the risk_map module.
"""

from risk_map.app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
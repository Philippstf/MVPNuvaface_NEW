"""
SUPER SIMPLE Medical AI Assistant API 
Just to get it working first!
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI(title="Medical AI Assistant - Simple")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Medical AI Assistant Simple API", "status": "working"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "medical-ai-assistant-simple"}

@app.get("/api/info")
def api_info():
    return {
        "name": "Medical AI Assistant",
        "version": "1.0.0",
        "status": "working",
        "endpoints": ["/health", "/api/info", "/api/risk-map/analyze"]
    }

@app.post("/api/risk-map/analyze")
def analyze_risk_map(request: dict):
    # Simple mock response for now
    return {
        "analysis_id": "test-123",
        "image_size": {"width": 512, "height": 512},
        "risk_zones": [
            {
                "name": "Test Risk Zone",
                "severity": "low",
                "polygon": [{"x": 100, "y": 100}, {"x": 200, "y": 100}, {"x": 200, "y": 200}, {"x": 100, "y": 200}],
                "safety_recommendations": ["This is a test"],
                "consequences": ["Test consequence"]
            }
        ],
        "injection_points": [
            {
                "label": "Test Point",
                "position": {"x": 150, "y": 150},
                "code": "TP1",
                "technique": "test",
                "depth": "dermal",
                "volume": "0.1 ml",
                "confidence": 0.9,
                "warnings": ["Test warning"]
            }
        ],
        "confidence_score": 0.85,
        "processing_time_ms": 100,
        "medical_disclaimer": "For testing purposes only."
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
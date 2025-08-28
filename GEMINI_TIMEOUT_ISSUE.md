# NuvaFace Gemini API Timeout Issue

## Problem Description

Our NuvaFace aesthetic simulation application is experiencing systematic timeouts when calling Google Gemini 2.5 Flash Image API from Google Cloud Run in us-central1 region. The Gemini worker process starts but never returns a response, causing Cloud Run to timeout after ~30 seconds.

## Tech Stack

### Frontend
- **Framework**: Vanilla JavaScript
- **Deployment**: Firebase Hosting
- **Image Processing**: HTML5 Canvas API for square cropping
- **API Calls**: Fetch API with base64 encoded images

### Backend API
- **Framework**: FastAPI (Python 3.10)
- **Deployment**: Google Cloud Run (us-central1 region)
- **Container**: Docker with Python 3.10
- **Timeout Settings**: 300 seconds (configured)
- **Memory**: 2Gi, CPU: 2 cores

### Image Processing Pipeline
1. **Face Segmentation**: MediaPipe + BiSeNet (CelebAMask-HQ)
2. **Image Generation**: Google Gemini 2.5 Flash Image via new `google-genai` SDK
3. **Subprocess Architecture**: Main API spawns isolated `gemini_worker.py` process

### Gemini Integration
- **SDK**: `google-genai` (latest, replaces deprecated `google-generativeai`)
- **Models Attempted**: 
  - `gemini-2.5-flash-image-preview`
  - `gemini-2.0-flash-exp`
  - `gemini-1.5-pro-latest`
  - `gemini-1.5-flash-latest`
- **Input Format**: `types.Part.from_bytes()` with PNG images
- **Configuration**: 
  ```python
  config={
      "temperature": 0.1,
      "top_p": 0.8,
      "max_output_tokens": 8192,
      "response_modalities": ["TEXT", "IMAGE"]
  }
  ```

## Detailed Issue Analysis

### What Works ✅
- **Frontend**: Image upload, cropping to square format, API communication
- **Backend**: FastAPI health check, face segmentation, mask generation
- **Cloud Run**: Service deployment in us-central1, environment variables set
- **API Key**: GOOGLE_API_KEY properly configured and accessible

### What Fails ❌
- **Gemini API Calls**: All models timeout without returning any response
- **Worker Process**: `gemini_worker.py` starts but produces no stdout/stderr output
- **No Error Messages**: Process hangs silently, no Gemini-specific error logs

### Logs Analysis

**Successful Steps:**
```
INFO:api.main:DEBUG: Received simulation request for lips with 4.0ml
INFO:api.main:DEBUG: Loaded original image: (2062, 2062)
INFO:api.main:DEBUG: Processed image size: (768, 768)
INFO:api.main:DEBUG: Generated mask for area 'lips', mask size: (768, 768)
INFO:engine.edit_gemini:DEBUG: Executing Gemini worker command: 
/usr/local/bin/python3.10 /app/gemini_worker.py --input /app/temp_inputs/[uuid]_input.png --output /app/temp_outputs/[uuid]_output.png --volume 4.0 --area lips --mask /app/temp_inputs/[uuid]_mask.png
```

**Failure Point:**
- Worker process starts at `16:54:26.727 MESZ`
- No output for 30+ seconds
- Cloud Run returns 500 Internal Server Error
- Final error: `SERVER_OVERLOAD: Entschuldigung! :( Die Server sind aktuell überlastet`

### Code Structure

**Main API Flow:**
```python
# api/main.py
@app.post("/simulate/filler")
async def simulate_filler(request: SimulationRequest):
    # 1. Load and process image ✅
    # 2. Generate face mask ✅  
    # 3. Call Gemini engine ❌
    result = await generate_gemini_simulation(image, volume_ml, area, mask)
```

**Gemini Worker Process:**
```python
# gemini_worker.py
def main():
    # Load images and prepare data ✅
    # Create Gemini client ✅
    # Call generate_with_fallback() ❌ (hangs here)
    
def generate_with_fallback(client, prompt, image_data, mask_data):
    for model_name in GEMINI_MODELS:
        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, image_data, mask_data],
            config=config
        ) # ❌ This call never returns
```

### Environment Details

- **Region**: us-central1 (specifically chosen for Gemini Image Generation support)
- **Image Size**: 768x768 PNG (after preprocessing)
- **Prompt**: Volume-based aesthetic enhancement prompts (~500-1000 chars)
- **Input Data**: ~850KB total (image + mask + prompt)

### Attempted Solutions

1. ✅ **Fixed SDK Format**: Switched from dict format to `types.Part.from_bytes()`
2. ✅ **Added response_modalities**: Explicitly request `["TEXT", "IMAGE"]`
3. ✅ **Regional Migration**: Moved from europe-west1 to us-central1
4. ✅ **API Key Validation**: Confirmed GOOGLE_API_KEY is set and accessible
5. ✅ **Timeout Increase**: Set Cloud Run timeout to 300 seconds
6. ⚠️ **Model Fallback**: Tries 4 different models, all fail silently

## Questions for Analysis

1. **Is this a known issue** with the new `google-genai` SDK in Cloud Run environments?
2. **Are there regional connectivity issues** from us-central1 to Gemini services?
3. **Should we implement async patterns** instead of synchronous API calls?
4. **Are there request size limitations** we're hitting (~850KB input)?
5. **Is the subprocess architecture** causing issues with Gemini SDK initialization?

## Minimal Reproduction

```bash
# Test with minimal image
curl -X POST "https://rmgpgab-nuvaface-api-europe-west1-philippstf-mvpn-hapllrcw7a-uc.a.run.app/simulate/filler" \
  -H "Content-Type: application/json" \
  -d '{"area":"lips","strength":0.5,"image":"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}'
```

**Expected**: Image generation response within 10-30 seconds
**Actual**: Timeout after 17+ seconds, no Gemini API response

## Dependencies

```txt
google-genai==0.6.0
fastapi==0.104.1
uvicorn==0.24.0
pillow==10.0.1
mediapipe==0.10.7
```

---

*Generated: 2025-08-28*
*Cloud Run Service*: `https://rmgpgab-nuvaface-api-europe-west1-philippstf-mvpn-hapllrcw7a-uc.a.run.app`
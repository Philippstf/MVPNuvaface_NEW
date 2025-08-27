# NuvaFace - AI-Powered Aesthetic Simulation

NuvaFace is a proof-of-concept system for simulating aesthetic procedures using advanced AI diffusion models. It provides realistic previews of filler and Botox treatments through state-of-the-art image generation techniques.

## ⚠️ Important Disclaimer

**This is a visualization tool for educational purposes only.** Results are AI-generated simulations and do not guarantee actual treatment outcomes. Always consult with qualified medical professionals for real aesthetic procedures.

## 🎯 Features

### Supported Procedures
- **Filler Simulation**: Lips, Chin, Cheeks
- **Botox Simulation**: Forehead wrinkles

### Technical Capabilities
- MediaPipe-based facial landmark detection
- Stable Diffusion inpainting with ControlNet guidance
- InstructPix2Pix alternative pipeline
- Real-time mask editing
- Quality control with identity preservation metrics
- Responsive web interface

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web UI        │    │   FastAPI       │    │   ML Engine     │
│                 │◄──►│                 │◄──►│                 │
│ • Upload        │    │ • /segment      │    │ • Face parsing  │
│ • Area select   │    │ • /simulate/*   │    │ • ControlNet    │
│ • Mask editor   │    │ • Quality check │    │ • SD Inpainting │
│ • Results view  │    │                 │    │ • Quality ctrl  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Pipeline Overview (Weg A)

1. **Upload** → Face alignment & preprocessing (768px)
2. **Segmentation** → MediaPipe FaceMesh → Area masks
3. **Control Maps** → Canny + Depth (SD) / SoftEdge + Depth (IP2P)
4. **Diffusion** → SD-Inpainting + dual ControlNet
5. **Quality Control** → ArcFace ID + SSIM off-mask
6. **Results** → Blended output with metrics

## 🚀 Quick Start

### Installation

1. **Prerequisites**
   ```bash
   # Ensure you have conda/miniconda installed
   conda --version
   ```

2. **Run Installation Script**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Activate Environment**
   ```bash
   conda activate nuvaface
   ```

### Starting the Server

```bash
# Development server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Using the Web Interface

1. Open `http://localhost:8000/docs` for API documentation
2. Open `ui/index.html` in your browser for the web interface
3. Upload a frontal face photo
4. Select treatment area (lips, chin, cheeks, forehead)
5. Adjust effect strength (0-100%)
6. Generate simulation

## 📋 API Reference

### Health Check
```bash
GET /health
```

### Face Segmentation
```bash
POST /segment
{
  "image": "base64_string",
  "area": "lips|chin|cheeks|forehead",
  "feather_px": 3
}
```

### Filler Simulation
```bash
POST /simulate/filler
{
  "image": "base64_string",
  "area": "lips|chin|cheeks",
  "strength": 50,
  "pipeline": "sd_inpaint|ip2p",
  "seed": 12345
}
```

### Botox Simulation
```bash
POST /simulate/botox
{
  "image": "base64_string", 
  "area": "forehead",
  "strength": 50,
  "pipeline": "sd_inpaint",
  "seed": 12345
}
```

### Example Usage
```bash
curl -X POST http://localhost:8000/simulate/filler \
  -H "Content-Type: application/json" \
  -d '{
    "image": "iVBORw0KGgoAAAANSUhEUgAA...",
    "area": "lips",
    "strength": 60,
    "pipeline": "sd_inpaint",
    "seed": 123
  }'
```

## ⚙️ Configuration

### Model Settings
The system uses these pre-trained models:
- **SD Inpainting**: `runwayml/stable-diffusion-inpainting`
- **InstructPix2Pix**: `timbrooks/instruct-pix2pix`
- **ControlNet**: `lllyasviel/sd-controlnet-*`
- **Face Analysis**: MediaPipe FaceMesh + InsightFace ArcFace

### Performance Tuning
```python
# Recommended settings for RTX 3090
steps = 30
resolution = 768
fp16 = True
xformers = True
```

### Quality Thresholds
```python
id_similarity_threshold = 0.35  # ArcFace warning
ssim_threshold = 0.98          # Off-target protection
```

## 🧪 Testing

### Run Quality Control Tests
```bash
python -m pytest tests/test_qc.py -v
```

### Manual Testing Workflow
1. Upload test images from `tests/data/`
2. Test each area type
3. Verify quality metrics
4. Check edge cases (no face, multiple faces)

## 📊 Quality Metrics

### Identity Preservation
- **Method**: ArcFace cosine similarity
- **Threshold**: > 0.65 (good), < 0.35 (warning)
- **Purpose**: Ensure person remains recognizable

### Off-Target Protection  
- **Method**: SSIM in non-masked regions
- **Threshold**: > 0.98
- **Purpose**: Prevent unwanted changes outside treatment area

### Image Quality
- **Method**: BRISQUE score comparison
- **Threshold**: < 10 point increase
- **Purpose**: Maintain perceptual quality

## 🔬 Scientific Background

### Botox Pipeline Research
The forehead treatment implements a two-stage pipeline based on ACCV 2022 research:

1. **Segmentation Stage**: Precise wrinkle area identification
2. **Inpainting Stage**: Texture-aware filling with global context

This approach achieves state-of-the-art results for photorealistic wrinkle removal while preserving natural skin texture.

**Future Enhancement**: Integration of Unet++ segmentation and LaMa/FFC inpainting models for improved clinical accuracy.

## 📁 Project Structure

```
NuvaFace_MVPneu/
├── api/                    # FastAPI application
│   ├── main.py            # API routes and handlers
│   └── schemas.py         # Pydantic models
├── engine/                # ML processing pipeline
│   ├── utils.py           # I/O, preprocessing
│   ├── parsing.py         # Face segmentation
│   ├── controls.py        # ControlNet preprocessing  
│   ├── edit_sd.py         # SD inpainting pipeline
│   ├── edit_ip2p.py       # InstructPix2Pix pipeline
│   └── qc.py              # Quality control
├── models/                # Model loading and caching
├── ui/                    # Web interface
│   ├── index.html         # Main UI
│   ├── app.js             # JavaScript logic
│   └── styles.css         # Styling
├── docs/                  # Documentation
│   ├── PROMPTS.md         # Prompt templates
│   └── ASSUMPTIONS.md     # Technical assumptions
├── tests/                 # Test suite
└── install.sh             # Installation script
```

## 🛣️ Roadmap

### Weg A (Current) - Diffusion Editing
- ✅ SD Inpainting + ControlNet
- ✅ InstructPix2Pix alternative
- ✅ Quality control system
- ✅ Web interface

### Weg B (Future) - Hybrid Approach
- 🔄 Geometric warping (TPS) for shape control
- 🔄 Combined geometry + texture editing
- 🔄 Improved form determinism for lips
- 🔄 API-compatible integration

### Clinical Enhancements
- 🔄 Unet++ segmentation model
- 🔄 LaMa/FFC inpainting integration
- 🔄 Wrinkle-specific loss functions
- 🔄 Clinical validation studies

## 🤝 Contributing

1. **Development Setup**
   ```bash
   git clone <repository>
   cd NuvaFace_MVPneu
   ./install.sh
   conda activate nuvaface
   ```

2. **Code Style**
   - Follow PEP 8 for Python
   - Use TypeScript-style JSDoc for JavaScript
   - Test changes with quality control suite

3. **Testing**
   - Add tests for new features
   - Verify quality metrics on test dataset
   - Document assumptions in `ASSUMPTIONS.md`

## 📝 License

This project is for research and educational purposes. Commercial use requires appropriate licensing of the underlying models:

- Stable Diffusion: CreativeML Open RAIL-M
- MediaPipe: Apache 2.0
- InsightFace: Academic use license

## 🆘 Troubleshooting

### Common Issues

**GPU Out of Memory**
```bash
# Reduce batch size or enable CPU offloading
export CUDA_VISIBLE_DEVICES=""  # Force CPU mode
```

**Model Download Errors**
```bash
# Clear cache and retry
rm -rf ~/.cache/huggingface/
python -c "from models import get_sd_inpaint_pipeline; get_sd_inpaint_pipeline()"
```

**API Connection Issues**
```bash
# Check server status
curl http://localhost:8000/health

# Verify CORS settings in production
```

### Performance Optimization

**Faster Inference**
- Use fp16 precision
- Enable xformers attention
- Reduce inference steps (20-25)
- Cache models in memory

**Memory Management**
- Enable model CPU offloading
- Use gradient checkpointing
- Reduce image resolution

## 📞 Support

- **Documentation**: See `docs/` directory
- **API Reference**: `http://localhost:8000/docs`
- **Issues**: Check troubleshooting section
- **Research**: See scientific references in documentation

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Status**: Proof of Concept (Weg A Complete)  

*This README provides a comprehensive overview of the NuvaFace system. For detailed technical information, refer to the documentation in the `docs/` directory.*
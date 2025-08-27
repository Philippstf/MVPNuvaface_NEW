# NuvaFace Technical Assumptions and Design Decisions

This document outlines the key assumptions, design decisions, and technical choices made in the NuvaFace implementation.

## Face Processing Assumptions

### MediaPipe FaceMesh Landmark Mapping

The system uses MediaPipe's 468-point face mesh. Key landmark groups and assumptions:

#### Lips Region
- **Outer Contour**: Landmarks [61, 84, 17, 314, 405, 320, 307, 375, 321, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78, 191, 80, 81, 82, 13, 312, 311, 310, 415]
- **Inner Contour**: Landmarks [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]
- **Assumption**: Inner and outer lip contours provide sufficient coverage for filler simulation
- **Fallback**: If landmarks fail, use basic face detection bounding box

#### Forehead Region
- **Eyebrow References**: 
  - Left: [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
  - Right: [296, 334, 293, 300, 276, 283, 282, 295, 285, 336]
- **Forehead Extrapolation**: Extend 15% of face height above eyebrow landmarks
- **Assumption**: Forehead region can be approximated by extending upward from eyebrow line
- **Rationale**: MediaPipe doesn't provide direct forehead landmarks

#### Chin Region
- **Jawline Base**: Lower portion of jawline landmarks
- **Vertical Threshold**: Lower 8% of detected face height
- **Assumption**: Chin area is the lowest 8% of the face region
- **Refinement**: Use convex hull for smoother mask boundaries

#### Cheeks Region
- **Left Cheek**: Landmarks [116, 117, 118, 119, 120, 121, 126, 142, 36, 205, 206, 207, 213, 192, 147, 187]
- **Right Cheek**: Landmarks [345, 346, 347, 348, 349, 350, 451, 452, 453, 464, 435, 410, 454, 356]
- **Assumption**: Mid-face lateral regions approximate cheek filler areas
- **Note**: Most heuristic of all regions - may need refinement based on user feedback

### Face Alignment

#### Eye-Based Rotation
- **Method**: Calculate angle between left and right eye centers
- **Threshold**: Only rotate if angle > 2 degrees
- **Assumption**: Most portrait photos have reasonable face alignment
- **Center**: Rotation center is midpoint between eyes

#### Size Normalization
- **Target Size**: 768px on the longer side
- **Assumption**: 768px provides good balance between quality and processing speed
- **Aspect Ratio**: Always preserved during resizing

## Model and Pipeline Assumptions

### Stable Diffusion Inpainting
- **Model**: "runwayml/stable-diffusion-inpainting"
- **Assumption**: This model provides best balance of quality and availability
- **ControlNet**: Dual control with Canny + Depth
- **Rationale**: Canny preserves edges, Depth maintains 3D structure

### InstructPix2Pix
- **Model**: "timbrooks/instruct-pix2pix"
- **Control**: SoftEdge + Depth (different from SD inpainting)
- **Assumption**: IP2P works better with softer edge guidance
- **Use Case**: Alternative pipeline when inpainting fails

### Parameter Mapping (Slider 0-100)

```python
# Core assumption: Linear parameter mapping provides intuitive control
denoising_strength = 0.15 + 0.005 * slider  # 0.15 → 0.65
guidance_scale = 3.5 + 0.04 * slider         # 3.5 → 7.5  
controlnet_scale = 0.60 + 0.006 * slider    # 0.60 → 1.20
mask_feather = round(3 + slider/40)         # 3 → 5 px
```

**Assumptions:**
- Linear mapping provides predictable user experience
- Range limits prevent over-enhancement and artifacts
- Conservative starting values (low end) ensure subtle effects

### Quality Control Thresholds

#### Identity Preservation (ArcFace)
- **Warning Threshold**: Cosine similarity < 0.35
- **Assumption**: 0.35 represents noticeable identity change
- **Based on**: Empirical testing with face recognition systems

#### Off-Target Protection (SSIM)
- **Warning Threshold**: SSIM < 0.98 in non-masked regions
- **Assumption**: 0.98 represents acceptable background preservation
- **Rationale**: Higher threshold ensures surgical precision

#### Image Quality (BRISQUE)
- **Degradation Limit**: +10 points from original
- **Assumption**: 10-point increase represents acceptable quality loss
- **Note**: Uses simplified BRISQUE implementation

## Processing Assumptions

### Hardware Requirements
- **GPU**: CUDA-capable recommended, fallback to CPU
- **VRAM**: 8GB+ for optimal performance
- **Assumption**: Most users have mid-range modern hardware

### Performance Targets
- **Inference Time**: 2-6 seconds @ 768px on RTX 3090
- **Assumption**: Sub-10-second response acceptable for web UI
- **Optimization**: fp16, xformers, model caching

### Memory Management
- **Pipeline Caching**: Keep loaded models in memory
- **Assumption**: Memory usage is acceptable trade-off for speed
- **Fallback**: CPU offloading if GPU memory insufficient

## UI/UX Assumptions

### User Workflow
1. **Single Image**: One photo per session
2. **Area Selection**: User picks one area at a time  
3. **Mask Refinement**: Optional manual editing
4. **Strength Control**: Single slider for effect intensity

**Assumptions:**
- Users prefer simple, guided workflow
- Most users will use auto-generated masks
- Single-area editing is primary use case

### Image Requirements
- **Format**: JPEG, PNG
- **Size**: Max 2048x2048 pixels
- **Quality**: Good lighting, frontal face view
- **Assumption**: Users will provide appropriate photos

### Browser Compatibility
- **Target**: Modern browsers with Canvas support
- **Assumption**: Users have recent browser versions
- **Fallback**: Graceful degradation for older browsers

## Medical and Aesthetic Assumptions

### Procedure Simulation Scope
- **Filler**: Volume enhancement simulation only
- **Botox**: Wrinkle reduction simulation only
- **Assumption**: Visual simulation sufficient for educational/preview purposes

### Clinical Accuracy
- **Disclaimer**: Results are visualizations, not medical predictions
- **Assumption**: Users understand limitations of AI simulation
- **Legal**: Educational/entertainment use only

### Anatomical Constraints
- **Natural Limits**: Parameter ranges prevent extreme modifications
- **Assumption**: Conservative limits maintain realistic results
- **Override**: Advanced users can modify via API parameters

## Data and Privacy Assumptions

### Image Processing
- **Temporary Storage**: Images processed in memory only
- **Assumption**: No persistent storage needed for MVP
- **Privacy**: No image data retained after session

### Model Data
- **Pre-trained Models**: Use publicly available models only
- **Assumption**: No custom training data required for MVP
- **Compliance**: Standard model licensing terms apply

## Future Architecture Assumptions

### Weg B (Geometry Warping)
- **TPS Warping**: Thin-plate spline for geometric transformation
- **Assumption**: Landmark-based warping provides better shape control
- **Integration**: Maintains API compatibility with Weg A

### Scalability
- **Horizontal Scaling**: Stateless API design allows load balancing
- **Assumption**: Database not needed for core functionality
- **Monitoring**: Standard observability patterns apply

## Edge Cases and Limitations

### Face Detection Failures
- **No Face Detected**: Return empty mask with error message
- **Multiple Faces**: Use largest detected face
- **Poor Quality**: Graceful degradation with warnings

### Model Limitations
- **Bias**: Models trained primarily on Western faces
- **Assumption**: Results may vary across ethnicities
- **Mitigation**: Quality control catches major failures

### Network and Performance
- **Slow Connections**: Show progress indicators
- **GPU Failures**: Fallback to CPU processing
- **Assumption**: Graceful degradation maintains usability

## Configuration and Extensibility

### Environment Variables
```bash
CUDA_VISIBLE_DEVICES=0  # GPU selection
MODEL_CACHE_DIR=/models # Model storage location
API_BASE_URL=localhost  # API endpoint
```

### Model Configuration
- **Swappable Models**: Architecture supports model replacement
- **Assumption**: Future model improvements can be integrated
- **Versioning**: API versioning for backward compatibility

## Validation and Testing

### Quality Metrics
- **Identity**: ArcFace cosine similarity
- **Structure**: SSIM off-mask
- **Perceptual**: LPIPS (optional)
- **Assumption**: Combination provides comprehensive quality assessment

### Test Data
- **Golden Set**: 20-50 diverse test images
- **Assumption**: Representative sample for validation
- **Metrics**: Automated quality scoring for regression testing

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Initial | Complete assumption documentation |

## References

1. MediaPipe Face Mesh: [Google AI Documentation](https://google.github.io/mediapipe/)
2. Stable Diffusion: [Stability AI Research](https://stability.ai/)
3. ControlNet: [Zhang et al., ICCV 2023](https://arxiv.org/abs/2302.05543)
4. InstructPix2Pix: [Brooks et al., CVPR 2023](https://arxiv.org/abs/2211.09800)

---

*This document should be updated as assumptions are validated or changed during development and testing.*
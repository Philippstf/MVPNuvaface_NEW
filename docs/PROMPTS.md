# NuvaFace Prompt Templates

This document contains the prompt templates used for different facial areas and procedures in the NuvaFace aesthetic simulation system.

## Overview

The prompt system uses carefully crafted text prompts to guide the diffusion models in generating realistic aesthetic enhancements. Each area has specific prompts designed to:

- Maintain natural appearance
- Preserve skin texture and lighting
- Avoid over-enhancement or artificial looks
- Provide consistent results across different face types

## Filler Prompts

### Lips (Lippen)

**English:**
```
slightly fuller, smoother, hydrated lips, natural shape, no makeup, keep lighting
```

**German:**
```
Lippen leicht voller und glatter, natürlich, kein Make-up, Licht unverändert
```

**Key Elements:**
- `fuller, smoother` - Primary enhancement goal
- `hydrated` - Natural appearance
- `natural shape` - Preserve individual lip characteristics
- `no makeup` - Avoid cosmetic appearance
- `keep lighting` - Preserve original photo lighting

### Chin (Kinn)

**English:**
```
subtle chin projection and rounding, natural, preserve skin texture
```

**German:**
```
dezente Projektion und Abrundung des Kinns, natürlich, Hauttextur erhalten
```

**Key Elements:**
- `subtle projection` - Gentle enhancement
- `rounding` - Softening of sharp angles
- `preserve skin texture` - Maintain natural skin appearance

### Cheeks (Wangen)

**English:**
```
slight cheek contour and volume, natural, avoid over-smoothing
```

**German:**
```
leichte Kontur und Volumen im Wangenbereich, natürlich, keine Überglättung
```

**Key Elements:**
- `slight contour and volume` - Gentle enhancement
- `avoid over-smoothing` - Prevent plastic appearance
- Focus on mid-face enhancement

## Botox Prompts

### Forehead (Stirn)

**English:**
```
reduce horizontal forehead wrinkles, keep pores and natural skin, keep original lighting
```

**German:**
```
reduziere horizontale Stirnfalten, Poren erhalten, natürliche Haut, Licht unverändert
```

**Key Elements:**
- `reduce horizontal forehead wrinkles` - Specific to target area
- `keep pores` - Maintain skin texture realism
- `natural skin` - Avoid porcelain effect
- `keep original lighting` - Preserve photo authenticity

## Prompt Engineering Guidelines

### Core Principles

1. **Natural Enhancement**: All prompts emphasize natural-looking results
2. **Texture Preservation**: Maintain skin pores and natural texture
3. **Lighting Consistency**: Keep original photo lighting
4. **Area Specificity**: Targeted descriptions for each facial region
5. **Avoid Over-Enhancement**: Prevent unrealistic or artificial results

### Negative Prompts

For all procedures, the following negative prompts are automatically applied:

```
blurry, distorted, unrealistic, artificial, plastic, fake, oversaturated, cartoon, anime, low quality, bad anatomy
```

### InstructPix2Pix Formatting

When using InstructPix2Pix pipeline, prompts are automatically converted to instruction format:

- **Lips**: `Make the lips {base_prompt}`
- **Chin**: `Enhance the chin to be {base_prompt}`
- **Cheeks**: `Adjust the cheeks to have {base_prompt}`
- **Forehead**: `Smooth the forehead by {base_prompt}`

## Prompt Customization

### API Usage

Prompts can be retrieved via the API:

```bash
GET /prompts/{area}?language={en|de}
```

Example:
```bash
curl "http://localhost:8000/prompts/lips?language=en"
```

### Custom Prompts

For advanced users, custom prompts can be provided in simulation requests. However, using the default prompts is recommended for consistent results.

## Medical Context and Botox Pipeline

### Scientific Background

The Botox (forehead) pipeline is based on research showing that a two-stage approach (segmentation → inpainting) achieves state-of-the-art results for wrinkle reduction:

1. **Segmentation Stage**: Precise identification of wrinkle areas
2. **Inpainting Stage**: Smooth texture filling with global context awareness

This approach, documented in ACCV 2022 papers, uses models like LaMa/FFC for superior texture synthesis in repetitive patterns (skin pores, texture).

### Future Enhancements

The current implementation uses SD-Inpainting + ControlNet. Future versions will integrate:

- **Unet++** for improved segmentation
- **LaMa/FFC** models for superior texture inpainting
- **Focal Frequency Loss** for better texture preservation
- **Wrinkle-specific loss functions** for clinical accuracy

## Slider-to-Prompt Mapping

The effect strength (0-100) influences not just model parameters but also prompt emphasis:

- **Low Strength (0-30)**: More conservative language ("subtle", "slight")
- **Medium Strength (31-70)**: Standard prompts as listed above
- **High Strength (71-100)**: Enhanced but still natural ("fuller", "smoother")

## Quality Validation

### Prompt Effectiveness Metrics

1. **Identity Preservation**: ArcFace similarity > 0.65
2. **Natural Appearance**: Avoid "plastic" or "artificial" keywords in descriptions
3. **Texture Quality**: BRISQUE score changes < 10 points
4. **Area Specificity**: SSIM off-mask > 0.98

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Over-smoothing | Generic "smooth" prompts | Use "preserve texture", "keep pores" |
| Artificial look | High guidance scale | Add "natural", "realistic" emphasis |
| Color shifts | Lighting changes | Include "keep lighting", "preserve colors" |
| Identity changes | Strong modifications | Emphasize "subtle", "slight" enhancement |

## Language Support

Currently supported languages:
- **English (en)**: Primary language for model training
- **German (de)**: Localized for German-speaking markets

Additional languages can be added by:
1. Translating prompt templates
2. Testing with multilingual diffusion models
3. Validating quality metrics across languages

## Research References

- **Facial Wrinkle Removal**: ACCV 2022 - "Photorealistic Facial Wrinkles Removal"
- **LaMa Inpainting**: WACV 2022 - "Resolution-robust Large Mask Inpainting"
- **ControlNet**: ICCV 2023 - "Adding Conditional Control to Text-to-Image"
- **InstructPix2Pix**: CVPR 2023 - "Learning to Follow Image Editing Instructions"

---

*Last updated: Version 1.0.0*
*For technical questions, refer to the main documentation or API reference.*
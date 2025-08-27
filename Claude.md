NuvaFace – PoC-Bauplan (Weg A → Abschluss → Weiterführung Weg B)

Ziel: schnell einsetzbarer Upload→Segmentierung→(InstructPix2Pix / SD-Inpainting) + ControlNet-Prototyp mit Slider-Steuerung. Danach sauberer Abschluss von Weg A und Erweiterung zu Weg B (Geometrie-Warping + Inpainting).

Scope des PoC (Areal-Auswahl)

Für einen verlässlichen, schnellen Start wählen wir die technisch leichtesten Areale:

Filler (3 Areale): Lippen, Kinn, Wangen
(Nase lassen wir im PoC aus – stärker 3D-/Schatten-sensitiv).

Botox (1 Areal): Horizontale Stirnfalten
(glatte, breite Region; robust segmentierbar; Paper-gestützte Pipeline Segmentierung→Inpainting).
Referenz: Zweistufige Pipeline „Falten-Segmentierung (Unet++ o. ä.) → Inpainting (LaMa/FFC)“ für fotorealistische Glättung und natürliche Hauttextur.

Teil I – Weg A (Diffusion-Editing pur)
A1. Architektur (high-level)
[Web-UI]
├─ Upload (JPG/PNG) + Consent
├─ Areal-Auswahl (Lippen/Kinn/Wangen/Stirn)
├─ Slider (0–100%) → maps to (denoising/guidance/control strength)
└─ Vorher/Nachher Viewer (A/B blend)

[API (FastAPI)]
├─ POST /segment → Face parsing (BiSeNet) + optional User-Refine
├─ POST /simulate/filler → SD-Inpainting | InstructPix2Pix + ControlNet
├─ POST /simulate/botox → SD-Inpainting (Stirn) + ControlNet
└─ GET /healthz

[Inference-Engine (GPU)]
├─ Preprocessing: Align/Crop/Normalize (768px long side)
├─ Parsing: BiSeNet (CelebAMask-HQ) → Masken (Lippen/Kinn/Wangen/Stirn)
├─ Control-Maps: Canny / SoftEdge / MiDaS-Depth
├─ Edit:
│ • InstructPix2Pix ODER SD-Inpainting (masked) + ControlNet
│ • Slider→(denoising strength, guidance scale, control weight)
├─ Postprocessing: Poisson/Color match, Feather, Sharpen (sanft)
└─ Qualitäts-Gates: ArcFace-ID Δ, SSIM off-mask, IQA

[Storage]
├─ Originale, Masken, Seeds, Parameter (S3/Blob)
└─ Logs (Audit, Prompt/Params, Inferenzzeiten)

[Security]
├─ HTTPS/TLS, JWT (Praxis), PII-Minimierung
└─ Export/Deletion (DSGVO)

Botox-Anker (Stirn): Das Paper empfiehlt explizit die Zweistufen-Logik (Falten-Maske → Inpainting), wobei LaMa/FFC die Hauttextur global konsistent inpaintet (stark bei repetitiven Mustern wie Poren). Wir übernehmen die Struktur (Segmentierung → gezieltes Inpainting) im PoC mit SD-Inpainting/ControlNet; später lässt sich das Training mit Unet++ & LaMa/FFC ergänzen.

A2. Tech-Stack & Requirements

Runtime

Python 3.10

PyTorch (CUDA 12.x Build)

FastAPI + Uvicorn

diffusers, transformers, accelerate

controlnet_aux (Canny/SoftEdge/Depth, FaceParsing helper)

opencv-python, mediapipe (optional für Landmark-Checks)

insightface + onnxruntime-gpu (ID-Check)

xformers (optional, Speed)

Modelle (keine eigenen Trainings nötig)

Stable Diffusion Inpainting Pipeline

InstructPix2Pix (Bild-Edit per Textinstruktion)

ControlNet: canny, softedge, depth

Face Parsing: BiSeNet (CelebAMask-HQ) → Areal-Masken

MiDaS Depth (controlnet_aux) für Depth-Map

ArcFace für Identity-Ähnlichkeit (Qualitäts-Gate)

Setup (CLI)

conda create -n nuvaface python=3.10 -y && conda activate nuvaface
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install diffusers transformers accelerate xformers
pip install controlnet-aux opencv-python mediapipe
pip install insightface onnxruntime-gpu
pip install fastapi uvicorn[standard] pillow einops

A3. Slider-Mapping (einheitlich)

Slider s ∈ [0..100]

denoising_strength d = 0.15 + 0.005·s → 0.15–0.65

guidance_scale g = 3.5 + 0.04·s → 3.5–7.5

controlnet_scale c = 0.60 + 0.006·s → 0.60–1.20

mask_feather px = round(3 + s/40) → 3–5 px

Interpretation: kleine s → dezente, texturschonende Edits; große s → stärkere Modulation (mehr Volumen/Glättung).

A4. Prompt-Presets (DE/EN)

Filler – Lippen (maskiert: Lippen)

DE: „Lippen leicht voller und glatter, natürlich, kein Make-up, Licht unverändert“

EN: “slightly fuller, smoother, hydrated lips, natural shape, no makeup, keep lighting”

Filler – Kinn (maskiert: Kinnregion)

DE: „dezente Projektion und Abrundung des Kinns, natürlich, Hauttextur erhalten“

EN: “subtle chin projection and rounding, natural, preserve skin texture”

Filler – Wangen (maskiert: Jochbogen/Wangenkörper)

DE: „leichte Kontur und Volumen im Wangenbereich, natürlich, keine Hautglättung“

EN: “slight cheek contour and volume, natural, avoid over-smoothing”

Botox – Stirn (maskiert: Stirnfläche)

DE: „reduziere horizontale Stirnfalten, Poren erhalten, natürliche Haut, Licht unverändert“

EN: “reduce horizontal forehead wrinkles, keep pores and natural skin, keep original lighting”
(Konzept: Segmentierung→Inpainting strukturgleich zum Paper; LaMa/FFC wird als späteres Feintuning angestrebt.)

A5. API-Design (Minimal)

POST /segment
Request: { image: <base64|url>, area: "lips|chin|cheeks|forehead" }
Response: { mask_png, mask_bbox, face_landmarks? }

POST /simulate/filler
Body:

{
"image": "<base64|url>",
"area": "lips|chin|cheeks",
"strength": 0-100,
"pipeline": "sd_inpaint|ip2p",
"seed": 12345
}

Response: { result_png, seed, params: {d,g,c}, qc: {id_cos, ssim_offmask, time_ms} }

POST /simulate/botox
Analog zu /simulate/filler, area:"forehead".

A6. Implementations-Skeleton (Claude Code-freundlich)

Projektstruktur

/api
main.py # FastAPI + routes
/engine
parsing.py # BiSeNet/FaceParsing + masks
controls.py # canny/softedge/depth maps
edit_sd.py # SD-inpainting + ControlNet
edit_ip2p.py # InstructPix2Pix pipeline
qc.py # ArcFace-ID, SSIM off-mask, BRISQUE optional
/models

# local cache for pipelines / onnx / arcface

/ui

# (optional) simple web front-end

Parsing (Pseudo-Code)

# engine/parsing.py

def segment_area(image_rgb, area:str) -> np.ndarray:
parsing = run_faceparsing(image_rgb) # logits→labels
mask = labels_to_mask(parsing, area) # lips/cheeks/chin/forehead
mask = refine_mask(mask, feather_px) # open/close + feather
return mask

Control-Maps

# engine/controls.py

def control_maps(image_rgb):
canny = auto_canny(image_rgb)
depth = midas_depth(image_rgb)
soft = softedge_pidinet(image_rgb)
return {"canny":canny, "depth":depth, "soft":soft}

SD-Inpainting + ControlNet

# engine/edit_sd.py

def simulate_sd_inpaint(image_rgb, mask, maps, s, seed, prompt):
d = 0.15 + 0.005*s; g = 3.5 + 0.04*s; c = 0.60 + 0.006\*s
pipe = get_inpaint_pipeline(control="canny+depth") # cached
set_seed(seed)
res = pipe(image=image_rgb, mask_image=mask, prompt=prompt,
controlnet_scales=[c,c], guidance_scale=g,
strength=d, num_inference_steps=30)
out = postprocess(res.image[0], image_rgb, mask)
return out, {"d":d,"g":g,"c":c}

InstructPix2Pix (Alternative)

# engine/edit_ip2p.py

def simulate_ip2p(image_rgb, mask, maps, s, seed, prompt):
d = 0.15 + 0.005*s; g = 3.5 + 0.04*s; c = 0.60 + 0.006\*s
pipe = get_ip2p_pipeline(control="softedge+depth")
set_seed(seed) # ip2p: condition via image+prompt; mask via inpaint variant or alpha blend
edited = pipe(image=image_rgb, prompt=prompt,
guidance_scale=g, strength=d, num_inference_steps=28)
out = masked_blend(image_rgb, edited.image[0], mask) # keep off-mask intact
return out, {"d":d,"g":g,"c":c}

Qualitäts-Gates

# engine/qc.py

def qc(original, edited, mask):
id_cos = arcface_cosine(original, edited) # ID preservation
ssim = ssim_offmask(original, edited, mask) # protect off-target
return id_cos, ssim

FastAPI-Routes (Kurz)

# api/main.py

@app.post("/simulate/filler")
def simulate_filler(req: SimReq):
img = load_image(req.image); area = req.area; s = req.strength
mask = segment_area(img, area)
maps = control_maps(img)
if req.pipeline == "ip2p":
out, params = simulate_ip2p(img, mask, maps, s, req.seed, prompt_for(area))
else:
out, params = simulate_sd_inpaint(img, mask, maps, s, req.seed, prompt_for(area))
id_cos, ssim = qc(img, out, mask)
return respond(out, seed=req.seed, params=params,
qc={"id_cos":float(id_cos), "ssim_offmask":float(ssim)})

A7. UX-Flow (User Story)

Upload Frontalbild → automatische Parsing-Maske (Areal).

Nutzer korrigiert Maske (Pinsel/Eraser), bestätigt.

Slider bewegen (z. B. 0 → 100).

Backend generiert Kontroll-Maps + führt Inpainting (oder i2p) mit den Slider-Parametern aus.

Ergebnis erscheint (typ. 2–6 s @ 512–768 px). A/B-Blend, Seed fixierbar.

Download/Share + Hinweis: „Visualisierung – kein Heilerfolg“.

A8. Qualitäts-/Sicherheits-Leitplanken

ID-Erhalt: ArcFace-Kosinus Δ-Schwelle (z. B. ≥ 0.35 auffällig → Warnhinweis).

Off-Target-Schutz: SSIM off-mask ≥ 0.98; sonst Retry (Seed+1) oder Control-Stärke ↓.

Artefakt-Score: no-ref IQA (BRISQUE/NIQE) in Masken-Region; Threshold-Fail → softere Parameter.

Botox-Spezifik: Strukturgleiche Pipeline Segmentierung→Inpainting wie im Paper; später Unet++-Maskierer + LaMa/FFC feintunen (State-of-the-Art-Ergebnisse für Faltenglättung & natürliche Textur).

A9. Performance-Tipps

Batch=1, steps=28–32, fp16, xformers → 2–4 s @ 768 px (A10/3090).

Cache Pipelines & ControlNet-Backbones.

Seeds deterministisch, Guidance moderat (g≈5–6) für natürliches Licht.

Maske feathern (3–5 px), Poisson-Blend off-edges.

Teil II – Abschluss von Weg A (PoC-“Definition of Done”)

Abnahmekriterien

Lippen/Kinn/Wangen: stufenloser Volumen-Eindruck (0→100), ohne Identitätsverlust; off-mask SSIM ≥ 0.98 in ≥ 95 % der Fälle; Artefakte < 5 % (manuell).

Stirn (Botox): deutliche Reduktion horizontaler Falten, Poren sichtbar, natürliche Haut.
Begründung/Paper-Bezug: Segmentierung→Inpainting liefert fotorealistische Glättung mit global konsistenter Hauttextur (LaMa/FFC).

Testing

Golden-Set (20–50 Bilder, diverse Hauttöne/Belichtung).

Snapshots (Seed, s=25/50/75), visuelle Diffs, ID/SSIM-Metriken in CI.

Kontraindikationen: „Unrealistic Shine“, Zahn-/Lippenrand-Bleeding → Parameter-Clamp (d,max; c,max) + Mask-Tuning.

Compliance/Log

Patienten-Consent (Aufklärungs-Hinweis), Seed/Prompt/Params persistieren (Audit).

DSGVO: Delete-API, Datenminimierung.

Teil III – Weiterführung zu Weg B (Hybrid: Geometrie-Warp + Inpainting)
B1. Motivation

Formtreue/Slider-Linearität (insb. Lippen) verbessert sich, weil Geometrie die Volumen-Änderung deterministisch vorgibt; Diffusion kümmert sich „nur“ um Textur & Glanz.

B2. Zusatz-Bausteine

Mediapipe FaceMesh (468 Landmark-Punkte).

Thin-Plate-Spline (TPS) / baryzentrisches Mesh-Warping für Zielareal.

Warp-Amplitude α = s/100 (s=Slider).

SD-Inpainting wie in Weg A zur Artefakt-Glättung.

B3. Pipeline (Lippen; analog Kinn/Wangen)
Image → FaceMesh → Lippenkontur(innen/außen)
→ Generiere Kontrollpunkte (Cupid’s bow, Commissures)
→ Definiere Normalen-Offsets ∝ α → TPS-Warp (nur in Areal)
→ SD-Inpainting (maskiert) mit neutralem Prompt
→ Postprocess + QC (ID, SSIM off-mask)

Botox (Stirn) bleibt identisch zu Weg A (Segmentierung→Inpainting). Das Paper zeigt, dass die Qualität stark von Maskenqualität + Inpainting abhängt; die LaMa/FFC-Inpainting-Eigenschaften (globaler Kontext, Haut-Repetitionen) sind hier besonders wertvoll.

B4. Zusatz-Requirements
pip install shapely scikit-image scipy

TPS-Implementierung (scipy RBF o. Custom TPS), opencv.remap fürs Warping.

Geometrie-Guards: Max-Verschiebung je Randpunkt; Kanten-Drift-Check (Edge-Map Δ).

B5. API-Kompatibilität

gleiche Endpunkte wie Weg A; Query-Param pipeline=B aktiviert Warping-Vorstufe.

Fallback: Landmark-Confidence < τ → automatisch auf Weg A.

B6. Kalibrierung & Roadmap

PoC: Einheit „Stärke“ statt „ml“.

Später: klinische Kalibrierung (Pilotdaten) → Mapping Stärke↔ml.

Für Botox: mittelfristig Unet++-Segmentierer + LaMa/FFC-Finetuning gemäß Paper-Training (Dice-Loss für Seg., Inpainting-Loss mit Focal Frequency Loss + Wrinkle-Loss, s. Paper-Figuren & Tabellen).

Anhang – Quickstart (Befehle)

# Start Dev-Server

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Beispiel-Call (curl)

curl -X POST http://localhost:8000/simulate/filler \
 -H "Content-Type: application/json" \
 -d '{"image":"<base64>","area":"lips","strength":60,"pipeline":"sd_inpaint","seed":123}'

Warum dieser Plan funktioniert

Weg A liefert schnell fotorealistische Ergebnisse mit kontrollierter Lokalität (Masken + ControlNet).

Botox profitiert direkt von der Segmentierung→Inpainting-Struktur, die in der Literatur State-of-the-Art ist (LaMa/FFC, Unet++-Maskierer, „Wrinkle-Loss“).

Weg B erhöht die Form-Deterministik (insb. Lippen) und bleibt API-kompatibel – nur ein modularer Schritt vor dem bekannten Inpainting.

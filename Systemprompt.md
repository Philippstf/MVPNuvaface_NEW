SYSTEM / ROLE
Du bist ein Senior Full-Stack + ML Engineer. Du setzt den folgenden PoC für „NuvaFace“ um – präzise, robust, mit sauberen Modulen, Tests und guter Developer-Ergonomie. Du arbeitest iterativ: schreibe Code-Dateien vollständig, erkläre kurz Entscheidungen, führe dann die nächsten Schritte aus. Keine Rückfragen – wenn etwas unklar ist, triff eine pragmatische, dokumentierte Annahme. Halte dich strikt an die Struktur und Akzeptanzkriterien. Ziel: in wenigen Iterationen ein benutzbares MVP (Weg A), dann Erweiterung (Weg B).

ZIEL / SCOPE DES POC

- „Bild-Upload → Segmentierung (Areal) → InstructPix2Pix/Stable Diffusion Inpainting + ControlNet → Ergebnis“, gesteuert über einen Slider (0–100).
- Unterstützte Areale im PoC (technisch leichteste):
  - FILLER: **Lippen**, **Kinn**, **Wangen**
  - BOTOX: **horizontale Stirnfalten (Stirn)**
- Weg A (Diffusion pur) zuerst produktionsnah umsetzen. Danach „Definition of Done“ prüfen. Anschließend Weg B (Hybrid: Geometrie-Warp + Inpainting) integrieren – API kompatibel, via Pipeline-Schalter.

ARCHITEKTUR (HIGH-LEVEL)

- ui/ : Minimal-Frontend (Upload, Arealwahl, Masken-Editor (Pinsel/Eraser), Slider 0–100, Vorher/Nachher-Blender).
- api/ : FastAPI mit Endpunkten:
  - POST /segment → erzeugt Arealmaske (lips|chin|cheeks|forehead) + optionale Landmark-Infos.
  - POST /simulate/filler → Diffusion-Editing (Weg A) auf Maskenregion.
  - POST /simulate/botox → Diffusion-Editing (Stirn) mit Falten-Reduktion.
  - POST /simulate/filler?pipeline=B → Hybrid (Weg B, nach Ausbau).
- engine/ : ML-/CV-Bausteine
  - parsing.py → Mediapipe FaceMesh + helper zur Maskengenerierung (Lippen/Stirn exakt; Kinn/Wangen pragmatisch).
  - controls.py → ControlNet-Karten (Canny, SoftEdge/Edge, Depth (MiDaS)).
  - edit_sd.py → Stable Diffusion Inpainting + ControlNet (Hauptweg).
  - edit_ip2p.py → InstructPix2Pix (Alternative), anschl. masked blend.
  - qc.py → ArcFace-ID-Ähnlichkeit, SSIM off-mask, optional BRISQUE/NIQE.
  - warping.py → (Weg B) Thin-Plate-Spline / Mesh-Warp + Remap.
- models/ : Pipelines/Weights-Cache (diffusers, onnx/arcface).
- docs/ : kurze README, Prompt-Presets, Annahmen, Changelog.

RUNTIME / REQUIREMENTS

- Python 3.10
- PyTorch (CUDA 12.x build), diffusers, transformers, accelerate, xformers
- controlnet-aux (Canny/PiDiNet/Depth), opencv-python, mediapipe
- insightface + onnxruntime-gpu (ArcFace)
- fastapi, uvicorn[standard], pillow, einops, scikit-image, scipy, shapely (für B)
- Stable Diffusion Inpainting pipeline
- InstructPix2Pix pipeline
- ControlNet: canny, softedge(pidinet), depth(midas)
- Mediapipe FaceMesh (468 Landmark-Punkte)

INSTALLATION (ALS SHELL-BLOCK AUSGEBEN + ERKLÄREN)

1. conda env anlegen + Pakete installieren
2. Model-Repos/Pipelines lazy-laden (diffusers) und lokal cachen
3. .env mit Model-Namen und Performance-Parametern anlegen

PROJEKTSTRUKTUR (ANLEGEN + DATEIEN MIT CODE FÜLLEN)
/
api/
main.py # FastAPI App + Routen
schemas.py # Pydantic-Modelle Requests/Responses
engine/
utils.py # I/O, base64, seed, resize/align
parsing.py # Mediapipe FaceMesh → Masken (lips/chin/cheeks/forehead)
controls.py # Canny, SoftEdge, Depth (controlnet_aux)
edit_sd.py # SD-Inpainting + ControlNet (canny+depth)
edit_ip2p.py # InstructPix2Pix + masked blend (Alternative)
qc.py # ArcFace, SSIM(off-mask), IQA stubs
warping.py # (Weg B) TPS/Mesh-Warp + Remap
models/
**init**.py # Lazy Loader für Pipelines/Detektoren
ui/
index.html # Minimal UI (Dropzone, Masken-Canvas, Slider, Buttons)
app.js # REST-Calls, Canvas Editing, A/B Blend
styles.css
docs/
README.md
PROMPTS.md # Prompt-Templates je Areal (DE/EN)
ASSUMPTIONS.md # getroffene Annahmen (Indices, Heuristiken)
tests/
test_qc.py # ID/SSIM checks für Golden-Images
data/ # wenige Beispielbilder (Platzhalter)

WEG A – FUNKTIONSWEISE

1. Preprocessing:
   - Face-Align (Augen horizontal), Long-Side 768 px, EXIF fix.
2. Maskierung:
   - Mediapipe FaceMesh:
     • Lippen: benutze etablierte Lippen-Landmark-Indizes (äußere/innere Kontur).
     • Stirn: Region oberhalb der Brauen – aus Brauen-Landmarks polygonal ableiten, nach oben um ~12–18% der Gesichtshöhe erweitern (Clamping an Image-Bounds).
     • Kinn: unterer Gesichtsbereich – jawline-Landmarks + schmaler vertikaler Offset (konservativ).
     • Wangen: Jochbogen-Region – Landmark-Cluster seitlich, heuristisch define (Konfiguration in ASSUMPTIONS.md).
   - Mask-Refine: morph. open/close, Feather 3–5 px (slider-abhängig).
   - UI: Masken-Pinsel/Eraser zum manuellen Feinzeichnen; Maske zurück an API.
3. Control-Maps:
   - Canny (auto thresholds), SoftEdge (PiDiNet), Depth (MiDaS small).
4. Edit-Kernel:
   - Standard: Stable Diffusion Inpainting + 2×ControlNet (canny, depth).
   - Alternative: InstructPix2Pix → anschließend Masked-Blend (falls Inpainting-Pfad mal ausfällt).
5. Slider-Mapping (global):
   - s ∈ [0..100]
     • denoising_strength d = 0.15 + 0.005*s → 0.15..0.65
     • guidance_scale g = 3.5 + 0.04*s → 3.5..7.5
     • controlnet_scale c = 0.60 + 0.006\*s → 0.60..1.20
     • mask_feather = round(3 + s/40) → 3..5 px
6. Prompt-Presets (in docs/PROMPTS.md ablegen, im Code verlinken):
   - Filler – Lippen (Mask: lips)
     DE: „Lippen leicht voller und glatter, natürlich, kein Make-up, Licht unverändert“
     EN: “slightly fuller, smoother, hydrated lips, natural shape, no makeup, keep lighting”
   - Filler – Kinn (Mask: chin)
     DE: „dezente Projektion und Abrundung des Kinns, natürlich, Hauttextur erhalten“
     EN: “subtle chin projection and rounding, natural, preserve skin texture”
   - Filler – Wangen (Mask: cheeks)
     DE: „leichte Kontur und Volumen im Wangenbereich, natürlich, keine Überglättung“
     EN: “slight cheek contour and volume, natural, avoid over-smoothing”
   - Botox – Stirn (Mask: forehead)
     DE: „reduziere horizontale Stirnfalten, Poren erhalten, natürliche Haut, Licht unverändert“
     EN: “reduce horizontal forehead wrinkles, keep pores and natural skin, keep original lighting”
7. Postprocessing:
   - Farb-/Belichtungs-Match minimal, Poisson/Alpha-Blend am Maskenrand, leichtes Sharpen ≤0.3.
8. Qualitäts-Gates:
   - ArcFace-ID-Cos ≤ Δ-Schwelle (z.B. Δ > 0.35 → Warnung/Retry (Seed+1)).
   - SSIM off-mask ≥ 0.98 (sonst Guidance/Control runter oder Seed wechseln).
   - Optional: BRISQUE/NIQE in Maskenregion (Artefakt-Score).

API-SIGNATUREN (MIT Pydantic SCHEMAS UND VOLLEM CODE ERSTELLEN)

- POST /segment
  Req: { image(base64|url), area: "lips|chin|cheeks|forehead" }
  Res: { mask_png(base64), bbox, landmarks? }
- POST /simulate/filler
  Req: { image, area: "lips|chin|cheeks", strength:0..100, pipeline:"sd_inpaint|ip2p", seed:int? }
  Res: { result_png(base64), seed, params:{d,g,c}, qc:{id_cos, ssim_offmask}, time_ms }
- POST /simulate/botox
  Gleiche Struktur, area:"forehead"

UI (EINFACHES STATIC FRONTEND ERSTELLEN)

- index.html + app.js: Upload, Arealselect, Mask-Canvas (zeichnen/ausradieren), Slider, „Simulate“ Button, A/B-Slider.
- REST-Calls zu /segment, /simulate/\*; Ergebnis anzeigen + Download.

TESTS & GOLDEN-SET

- tests/test_qc.py: Lade 3–5 Beispielbilder (Dummy), prüfe, dass API antwortet, und dass qc-Felder vorhanden sind.
- (Optional) Mock-Pipelines für CI.

PERFORMANCE-TUNING

- steps=28–32, fp16, xformers, 768px lange Kante, Pipeline-Objekte cachen.
- Ziel: 2–6 s Inferenz @ 512–768 px (A10/3090-Niveau).

DEFINITION OF DONE (Weg A)

- FILLER: Lippen/Kinn/Wangen zeigen stufenlos realistisch mehr Volumen (0→100), ohne Off-Target (SSIM off-mask ≥ 0.98 in ≥95% der Fälle), ID stabil (ArcFace-Δ ok).
- BOTOX: Stirn-Falten deutlich reduziert, Poren & Hautkorn erkennbar, kein „Porzellan-Look“.
- Seeds/Params/PROMPT werden geloggt (Audit Trail); UI mit Hinweis: „Visualisierung, keine Ergebnisgarantie“.

> > > SETZE JETZT UM:

1. Lege das Repo-Skelett an.
2. Erstelle install.sh (Paket-Installation/Umgebung).
3. Implementiere engine/utils.py (I/O, base64, seed, resize/align).
4. Implementiere engine/parsing.py:
   - Mediapipe FaceMesh laden.
   - Funktion mask_for_area(image, area, feather_px):
     • lips: Standard Lippen-Landmark-Polygone nutzen (äußere/innere Kontur).
     • forehead: aus Augenbrauen-Landmarks ein oberes Polygon extrapolieren (12–18% Bildhöhe).
     • chin: jawline-Landmarks + kleiner Offset (konservativ).
     • cheeks: laterale Polygone in Höhe Jochbogen (heuristisch; in ASSUMPTIONS.md dokumentieren).
5. Implementiere engine/controls.py (Canny, SoftEdge, Depth) via controlnet_aux.
6. Implementiere engine/edit_sd.py:
   - Stable Diffusion Inpainting Pipeline + zwei ControlNets (canny, depth).
   - Slider-Mapping (d,g,c).
   - Inferenz mit mask_image, prompt (aus PROMPTS.md), Seed, Steps.
7. Implementiere engine/edit_ip2p.py:
   - InstructPix2Pix Pipeline; Ergebnis via masked_blend mit Original (außerhalb Maske unverändert).
8. Implementiere engine/qc.py (ArcFace-Cos, SSIM off-mask) + Schwellen.
9. Implementiere api/schemas.py (Pydantic) + api/main.py (Routen).
10. Implementiere ui/ (index.html, app.js, styles.css) inkl. Masken-Editor (Canvas).
11. Starte Uvicorn und zeige ein kompletter Durchlauf im Log (Upload→Segment→Simulate).
12. Lege docs/PROMPTS.md, docs/ASSUMPTIONS.md mit allen Annahmen (Landmark-Indizes, Heuristiken) an.
13. Lege tests/test_qc.py an und führe Tests aus.

KURZE MEDIZINISCHE VERANKERUNG (BOTox)

- Wir nutzen konzeptuell eine Zweistufen-Pipeline „Falten-Maske → Inpainting“, wie in einer ACCV-Arbeit („Photorealistic Facial Wrinkles Removal“) mit LaMa/FFC aufgezeigt (globale Kontext-Textur). Im PoC nutzen wir SD-Inpainting + ControlNet, die Struktur ist identisch. Dokumentiere das im README und verweise in docs/ auf das Paper (978-3-031-27066-6.pdf).

NACH DEM DO-DONE VON WEG A: WEITERFÜHRUNG WEG B (HYBRID)

- Ziel: deterministische Formkontrolle (Slider linear), besonders für Lippen; Diffusion übernimmt nur Textur/Glanz.
- Änderungen:
  1. engine/warping.py implementieren:
     - Hole Lippen-Konturpunkte (FaceMesh).
     - Erzeuge Zielkontur durch Verschiebung entlang Normalen (Amplitude α = s/100).
     - Thin-Plate-Spline/Mesh-Warp nur innerhalb der Lippen-Maske (opencv.remap).
  2. In api/main.py Pipeline-Schalter `pipeline=B`:
     - Warpe Eingabebild + Maske.
     - Danach **denselben** SD-Inpainting-Call mit neutralem Prompt (Textur glätten, Dehnungsartefakte füllen).
  3. Geometrie-Guards/QA:
     - Max-Verschiebung je Landmark begrenzen.
     - Kanten-Drift prüfen (Edge-Map-Δ).
     - Fallback: Wenn Landmark-Confidence < τ → automatisch auf Weg A.
- UI: Toggle „Form-präzise (Beta)“ aktiviert Pipeline B; Slider unverändert.
- Kalibrierung: Einheit zunächst „Stärke“ anstatt „ml“. Mapping „Stärke↔ml“ erst nach Pilotdaten.

AKZEPTANZKRITERIEN (WEG B)

- Gleiche Qualitäts-Gates wie Weg A.
- Zusätzliche Form-Treue: Lippenkontur bleibt stabil; Off-Target-Edges minimal; deterministische Reproduzierbarkeit bei gleichen Seeds.

DOCUMENTATION & HANDBUCH

- docs/README.md mit:
  - Architekturdiagramm (ASCII/mermaid)
  - Install/Run-Anleitung
  - API-Beispiele (curl)
  - Prompt-Preset-Liste (DE/EN)
  - Qualitätsmetriken & Schwellwerte
  - Bekannte Edge Cases & Fallbacks
- Changelog in docs/; commit messages prägnant.

JETZT STARTEN:

- Lege umgehend alle Dateien an und fülle sie mit funktionsfähigem Code.
- Gib nach jedem großen Schritt: Datei-Diff + kurzer Test-Output.
- Schließe Weg A vollständig ab (inkl. Minimal-UI).
- Danach implementiere Weg B (Warping) und demonstriere eine komplette Lippen-Simulation mit Pipeline=B.

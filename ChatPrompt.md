# NuvaFace — Claude Code Arbeitsauftrag (MVP „Medical AI Assistant“)

**Bitte lies ALLES gründlich. Erstelle zuerst eine eigene Umsetzungs- und Arbeitsplanung als `docs/medicalassistant.md` auf Basis dieser Spezifikation und arbeite dann die Umsetzung entlang deiner Planung ab.**  
Ziel: In der NuvaFace Web-App sollen Investor:innen live sehen, wie wir auf einem **2D-User-Upload-Foto** medizinisch fundierte **Risikozonen** und **ideale Injektionspunkte** (inkl. Tiefe/Dosierung/Technik) für **Lippen (Filler), Kinn (Filler), Wangen (Filler), Stirn (Botox)** ein- und ausblenden.  
Wichtig: **Kein 3D hier.** Das 3D-Head auf der Landing ist nur die Vorauswahl-UX. Die Overlays erscheinen **im Simulationsergebnis auf dem 2D-Vorherbild**.

---

## 0) Kontext & Zielbild

- **Story für Investoren:**
  1. Bereichs-Preselection (3D-Landing) → 2) Foto-Upload → 3) Simulation → 4) Toggle: _„Risikozonen“_ und _„Ideale Injektionspunkte“_ (Medical AI Assistant).
  2. Beim Hover/Klick auf Punkte/Polygone erscheinen **medizinische Erklärungen** (MD Codes, Technik, Tiefe, Volumen) – **reproduzierbar** und **nicht willkürlich**.
- **Leitmotiv:** _AI Simulation Suite & AI Safety_. Wir markieren keine „irgendwo“-Flächen, sondern **regel- und guideline-basiert** (z. B. MD Codes, anatomische Danger Zones).
- **Determinismus/Reproduzierbarkeit:** Ergebnisse sollen gleiches Gesicht → gleiche Punkte liefern. Zufall vermeiden (keine stochastische Platzierung).

---

## 1) Wissensaufbau (MD Codes, Danger Zones, Techniken)

**Aufgabe:** Baue dir **lokalen Kontext** (kein Internetzugriff erforderlich) aus bereitgestellten/noch zu ergänzenden Dokumenten.  
Im Projekt sind Verzeichnisse vorgesehen, in die du Dateien kopieren kannst:

/assets/knowledge
common/ # generelle Anatomie- und Safety-Dokumente
lips/ # MD Codes & Papers zu Lippen-Filler
chin/ # Kinn-Filler
cheeks/ # Wangen-Filler
forehead/ # Stirn-Botox (Frontalis/Glabella)

**Was du tun sollst:**

- Extrahiere aus den Dokumenten **regelbare, implementierbare Strukturen**:
  - **Injektionspunkte**: label, MD-Code (falls vorhanden), **Tiefe** (z. B. „dermal“, „subkutan“, „supraperiostal“), **Technik** (z. B. „linear threading“, „Bolus“, „Fächer“, „Kanüle vs. Nadel“), **volumetrische Empfehlung** (Startwerte in ml oder Units), **Warnhinweise**.
  - **Risikozonen** („Danger Zones“): polygonale Bereiche (z. B. Glabella-Gefahr, A. angularis/Nasenflügel, infraorbital/temporal), **Warntexte**, **Rationale** (welches Gefäß/Nerv, welches Risiko).
- Forme daraus **konfigurierbare YAML/JSON-Definitionen**, die wir **regelbasiert** an **Face-Landmarks** binden (siehe Abschnitt 3/4).

➡️ **Ergebnis**: Lege im Repo Dateien an wie:

/assets/knowledge/lips/injection_points.yaml
/assets/knowledge/lips/risk_zones.yaml
... (chin, cheeks, forehead analog)

**Vorschlag YAML-Schema (Injektionspunkte):**

```yaml
area: lips
points:
  - id: Lp2
    label: "Oberlippe – Vermillion"
    md_code: "LP2"        # falls verfügbar/übernommen
    technique: "linear threading"
    depth: "dermal"
    volume_recommendation: "0.05–0.1 ml"
    tool: "needle"        # oder "cannula"
    notes: "Konturierung, Philtrum-schonend"
    # Regeldefinition: wie aus Gesichtslandmarken berechnen (siehe unten)
    rule:
      type: "landmark_vector_offset"
      anchors: ["UPPER_LIP_CENTER", "LEFT_LIP_CORNER", "RIGHT_LIP_CORNER"]
      offset_percent: { x: 0.0, y: -0.02 }   # in Bildbezug auf Gesichtsbox
      clamp_to_mask: "lips"                  # optional: auf Segment clippen

Vorschlag YAML-Schema (Risikozonen):

area: cheeks
zones:
  - name: "Facial artery course (approx.)"
    severity: "high"
    color: "#FF4D4D"
    opacity: 0.25
    rationale: "A. facialis – Risiko Embolie/Nekrose"
    rule:
      type: "polyline_buffer_from_landmarks"
      anchors: ["ALAE_BASE", "ORAL_COMMISSURE", "MALAR_APEX"]
      buffer_px: 12
      style: "hatched"
      tooltip: "Vermeide Bolus; Kanüle subkutan in Distanz"

Wichtig: Nutze verständliche Labels, konservative Volumina, deutliche Warnhinweise. Ziel ist Sicherheit + Erklärbarkeit.



2) Architektur Gesamtbild (MVP)

Frontend (Web, vorhandene App):

Fotoanzeige (Vorherbild) + Overlay-Layer (Canvas oder SVG) in exakt gleicher Größe.

Medical AI Assistant: schwebender Button unten rechts → Menü mit Toggles:

„Risikozonen einblenden“

„Ideale Injektionspunkte einblenden“

Tooltip/Popover bei Hover/Klick auf Marker/Polygone mit medizinischem Inhalt (aus Knowledgebase).

Backend-Service („risk-map“):

Input: Bild (Base64/URL/Upload) + area (lips/chin/cheeks/forehead).

Schritte:

Gesichtslandmarks ermitteln (MediaPipe/dlib/OpenCV).

Normierung (Face-Align, Bounding Box, Maßfaktoren).

Regelbasierte Projektion der YAML-Definitionen → konkrete Pixel-Koordinaten (Polygone/Punkte).

Output (JSON): Koordinaten + Metadaten (code, depth, volume, technique, warnings).

Endpunkt-Entwurf:
POST /api/risk-map/analyze
{
  "image": "<base64 or url>",
  "area": "lips" | "chin" | "cheeks" | "forehead",
  "modes": { "risk_zones": true, "injection_points": true }
}

→ 200 OK
{
  "imageSize": { "w": 1024, "h": 1024 },
  "landmarks": { ... (optional für Debug) ... },
  "risk_zones": [
    { "name":"...", "polygon":[[x,y],...], "severity":"high", "tooltip":"...", "style":{...} }
  ],
  "injection_points": [
    { "label":"...", "code":"LP2", "x":512, "y":620,
      "depth":"dermal", "technique":"linear threading", "volume":"0.05–0.1 ml",
      "tool":"needle", "confidence":0.85, "notes":"..." }
  ]
}

3) Landmarking & Normalisierung (Determinismus)

Ziel: Gleiche Gesichter → gleiche, reproduzierbare Punkte.
Vorgehen:

Nutze FaceMesh/468 Punkte oder vergleichbar.

Bestimme Schlüssel-Anker:

Augen: inner/outer corners, Pupillenmitte

Nase: Nasenspitze, Alae-Basis links/rechts

Mund: Lippenmittelpunkte, Mundwinkel

Stirn: abgeleitet oberhalb Brauenlinie (aus Augenbrauenpunkten)

Kinn: Pogonion (Kinnspitze), Menton (tiefster Kinnpunkt)

Wangen: Malar Apex/Jochbogen → aus Landmark-Triplets genähert

Face-Align: Optionale Rotation auf „Augenlinie horizontal“, damit Regeln als Prozentwerte vom Face-Bounding-Box robust funktionieren.

Koordinaten-Raum: Arbeite intern in [0..1] relativ zur Face-Box (x_rel,y_rel). Wandle am Ende in Bildpixel um (Multiplikation mit Boxbreite/-höhe + Offset).

Clamping/Snapping:

Punkte ggf. auf Segmentmasken (z. B. Lippenkontur) clampen.

Für visuelle Ruhe Snap auf 2–4 px Raster.

4) Regel-Engine (Mapping YAML → Pixel)

Implementiere im Backend eine kleine Rule-Engine, die YAML-„rule“-Blöcke interpretiert:

Unterstützte Rule-Typen (Startumfang):

landmark_vector_offset

Nimmt 1–3 Anker-Landmarks, berechnet Basisvektoren (Mitte, Richtung) → addiert relative Offsets (in Prozent der Face-Box oder lokaler Distanz) → liefert Punkt.

polyline_buffer_from_landmarks

Nimmt Landmark-Sequenzen (z. B. Nase→Mundwinkel→Malar Apex), erzeugt eine Polyline und erweitert sie um einen Buffer (Pixel) zu einem Polygon (für Gefäßverlauf-Approximationen).

mask_from_landmark_loop

Erzeugt aus Landmark-Indizes (z. B. Lippenkontur) ein Polygon (für semitransparente Masken).

circle_around_landmark

Einfacher kreisförmiger Marker mit Radius als Prozentwert von Face-Box oder Pupillendistanz.

bone_point

Für supraperiostale Punkte: an knochennahen Landmark-Relationen (z. B. Zygoma-peak) positionieren.

Best Practice: Hinterlege in Knowledgebase konservative Offsets und nutze bekannte Proportionsregeln (z. B. philtrale Linien, Tragus-Referenzen), um reproduzierbar zu sein.


5) Frontend-Overlay (Canvas/SVG) & Interaktionen

Layering: <div class="frame"> <img id="photo"> <canvas id="overlay"> </div>

Zeichnung:

Risikozonen: halbtransparente rote Polygone (z. B. rgba(255,77,77,0.25)), optional „hatched“ (gepunktete Kontur).

Injektionspunkte: weiße Punkte mit sanftem Glow (Schatten/blur).

GSAP für Fade-In/Out beim Toggle.

UI Toggles: „Risikozonen anzeigen“, „Ideale Injektionspunkte anzeigen“.

Tooltips: Hover → kleiner Card mit label/code/depth/technique/volume/tool/notes/warning. Klick → fixiertes Info-Paneel (rechts) für tiefergehende Erklärung inkl. Quelle/MD-Code.

Resizing: Wenn das Bild skaliert dargestellt wird, transformiere Server-Koordinaten → Viewport-Koordinaten mit Scale + Offsets (immer den gleichen Referenz-Frame beibehalten).

Zustand/Redux (optional): overlayState = { riskZonesVisible: bool, pointsVisible: bool, currentArea: 'lips'|'chin'|'cheeks'|'forehead' }.

Pseudocode Frontend:
async function renderOverlays(imageEl, area, modes) {
  const res = await fetch('/api/risk-map/analyze', { method:'POST', body: JSON.stringify({ image:getImagePayload(imageEl), area, modes })});
  const data = await res.json();
  drawRiskZones(data.risk_zones);
  drawInjectionPoints(data.injection_points);
}

function drawInjectionPoints(points){
  points.forEach(p => {
    // canvas: circle + outer glow
    // attach mouse events -> showTooltip(p)
  });
}

6) Medical AI Assistant (Widget)

Platzierung: Floating Button (unten rechts), Titel: „Medical AI Assistant“.

Interaktion: Klick öffnet ein Mini-Panel:

Checkbox „Risikozonen einblenden“

Checkbox „Ideale Injektionspunkte einblenden“

(Optional) Dropdown „Detailgrad“ (nur Punkte / + Tooltips / + Quellen).

Transparenz/Disclaimer: Unter dem Panel kurzer Hinweis:

„Hinweise basieren auf anatomischen Standarddaten und regelbasierter Gesichtsanalyse. Für medizinische Fachanwender. Keine Patientenaufklärung/Indikation.“

Fehlerfälle: Falls Landmarking fehlschlägt: zeige Fallback (statische Schablone skaliert an Augenabstand/Mundbreite) + Banner „Automatische Anpassung fehlgeschlagen – vereinfachte Darstellung“.

7) Datenmodell (Frontend/Backend)
Gemeinsames Schema: (stark vereinheitlicht für Rendering + Tooltips)
type RiskZone = {
  name: string;          // e.g. "A. angularis danger"
  polygon: [number,number][]; // in Bildpixeln
  severity: 'low'|'moderate'|'high';
  tooltip?: string;
  style?: { color?: string; opacity?: number; hatch?: boolean };
  source?: { ref?: string; md_code?: string };
}

type InjectionPoint = {
  label: string;         // "Mid-cheek structural point"
  code?: string;         // "CK3"
  x: number; y: number;  // Bildpixel
  depth?: string;        // "dermal" | "subcutaneous" | "supraperiosteal"
  technique?: string;    // "linear threading" | "bolus" | "fanning" | "cannula"
  volume?: string;       // "0.05–0.1 ml" | "2–4 U"
  tool?: string;         // "needle" | "cannula"
  notes?: string;        // zusätzlicher Kontext
  confidence?: number;   // 0..1 (optional)
  warnings?: string[];   // z. B. „Keep distance to facial artery“
  source?: { ref?: string; md_code?: string };
}

8) Akzeptanzkriterien (MVP Demo-Ready)

Laden eines User-Fotos → Anzeige des Vorherbilds in fester Stage (z. B. 1024×1024 oder adaptive Größe mit korrekter Skalierung).

Medical AI Assistant aufgeklappt → Toggles sichtbar.

Risikozonen-Overlay: Mindestens 1–2 relevante Zonen je Area (konservativ!):

Lippen: periorale Danger-Hinweise (A. labialis Umgebung vermeiden).

Kinn: Vorsicht an mental nerve exit.

Wangen: A. facialis Verlauf / infraorbital warning.

Stirn: Glabella/Frontalis (Blindheitsrisiko bei falscher Platzierung).

Injektionspunkte-Overlay: 2–4 fundierte Punkte je Area mit Tiefe/Technik/Volumen.

Tooltips: auf Marker-Klick öffnen sich medizinische Infos (aus Knowledgebase), inkl. MD-Code-Referenzen/Quelle.

Determinismus: Gleiche Eingabe → identische Ausgabe (innerhalb kleiner Pixeltoleranz).

Fallback: Bei Landmark-Fail → skalierte Schablone + Hinweisbanner.

Performance: Analyse < 1–2 s auf Standard-Hardware (Server-seitig ok), Rendering 60 FPS beim Ein-/Ausblenden.

Sicherheit/Transparenz: sichtbarer Hinweis, dass das Assistenz ist (keine Indikation), nur für geschultes Personal.

9) Datei- & Modulstruktur (Vorschlag)
/docs/
  medicalassistant.md        # <- DEINE PLANUNG (als Erstes erstellen)
/assets/knowledge/
  common/*.md|.pdf|.yaml
  lips/*.yaml
  chin/*.yaml
  cheeks/*.yaml
  forehead/*.yaml
/frontend/
  components/MedicalAssistantButton.tsx
  components/OverlayCanvas.tsx
  lib/overlayRenderer.ts
  lib/tooltip.ts
  styles/overlays.css
/backend/
  risk_map/
    app.py                   # FastAPI
    landmarks.py             # FaceMesh wrapper
    rules_engine.py          # YAML -> coords
    schemas.py               # Pydantic
    knowledge_loader.py      # YAML reader/cache
    tests/
      test_rules_engine.py
      samples/ (test images)

10) Implementierungsschritte (in dieser Reihenfolge)

Erstelle docs/medicalassistant.md

Beschreibe deinen detaillierten Arbeitsplan (Aufgaben, Meilensteine, Teststrategie, Fallbacks, Risiken).

Liste die Regeldefinitionen je Area (erste 2–4 Punkte + 1–2 Risikozonen).

Notiere welche Knowledge-Dateien du verwendest (aus /assets/knowledge/**), ggf. Zusammenfassung der MD-Code-Rationale.

Knowledgebase einrichten

Lege initiale *.yaml pro Area an (min. 2 Punkte + 1 Zone).

Schreibe konservative, klare Texte (depth/technique/volume).

Backend „risk-map“

FastAPI-Endpunkt /api/risk-map/analyze.

Pipeline: decode image → Face landmarks → normalize → apply rules → JSON out.

Logging + deterministisches Verhalten (keine RNG).

Unit-Tests für rules_engine.py (geben Landmark-Dummies rein, prüfen Koordinatenbereich).

Frontend-Overlay

Canvas/SVG Renderer: Polygone + Glow-Punkte + Tooltips.

GSAP Fade on toggle.

Scaling korrekt lösen (Bild vs. Overlay).

Event-Handling (hover/click → Info).

Assistant-Widget

Floating Button + Panel mit Toggles.

API call orchestrieren (area + modes).

Fehlermeldungen/Disclaimer.

E2E-Demo-Flow

Seed-Bilder + Screens für Live-Demo.

Show-Skript: Area wählen → Upload → Simulation anzeigen → Assistant → Risk → Points → Tooltip mit MD-Code.

QA & Feinschliff

Prüfe 3–4 unterschiedliche Gesichter (Gesichtsform, Pose leicht variabel).

Sensible Texte (keine Heilaussagen, klare Safety-Hinweise).

Kontraste/Barrierefreiheit der Overlays.

11) Fallbacks & Edge Cases

Kein Gesicht erkannt → Meldung + statische, an Augenabstand und Mundbreite skaliert platzierte Schablone; Banner „vereinfachte Darstellung“.

Teilverdeckung (Brille/Haar) → markiere Unsicherheit („gestrichelt“ + Tooltip „approx.“).

Extreme Posen → bitte Frontalsicht für MVP annehmen; bei Abweichung: Warnbanner „Bitte frontales Foto“.

12) „Investor Wow“-Details

Smooth Overlays (kurzes Glow, federnder Fade).

Mini-Legende oben rechts („rot = Risiko“, „weiß = Empfehlung“).

Klick auf Punkt → „Warum hier?“ mit 1–2 Sätzen Rationale + Quelle (MD Code/Anatomy).

Kurzer Safety-Score je Area (Balken: gering/moderat/hoch) basierend auf aktiven Zonen.

14) Was du jetzt konkret machst

Erstelle docs/medicalassistant.md (dein eigenständiger, detaillierter Umsetzungsplan – nutze dieses Dokument als Vorlage, aber formuliere deinen Plan).

Richte die Knowledgebase-Dateien in /assets/knowledge/{lips,chin,cheeks,forehead}/ ein (YAML wie oben). Nutze vorhandene Dokumente, kopiere relevante Snippets (falls erlaubt) und abstrahiere sie in Regeln.

Implementiere Backend + Frontend wie beschrieben.

Zeige eine lauffähige Demo mit 4 Bereichen, je 2–4 Punkten und 1–2 Risikozonen, inkl. Tooltips mit Tiefe/Technik/Volumen/Quelle.

Bitte verifiziere während der Arbeit laufend die medizinische Plausibilität deiner Regeln anhand der (lokalen) MD-Code-/Anatomie-Ressourcen in /assets/knowledge/**. Markiere unsichere Areale konservativ und kommuniziere Unsicherheit im Tooltip.

15) Hinweise zum bestehenden Projekt

Das 3D-Head (female_head_areas.glb) ist nur auf der Landing für die Bereichsauswahl; nicht in diesem Modul verwenden.

Bildanalyse & Overlays betreffen die 2D-Vorheraufnahme nach der Simulation.

16) Abnahme-Checkliste (kurz)

 docs/medicalassistant.md vorhanden & vollständig (Plan, Regeln je Area, Testplan).

 YAML-Definitionsdateien pro Area.

 /api/risk-map/analyze liefert konsistentes JSON.

 Frontend rendert Overlays (Risk/Points) mit Toggle + Tooltips.

 Demo-Flow funktioniert stabil in 3–4 Beispielbildern.

 Disclaimer/Transparenz-Sektion vorhanden.

 Danke! Bitte starte mit docs/medicalassistant.md und führe die Umsetzung anschließend Schritt für Schritt aus.
Ziel ist eine beeindruckende, medizinisch fundierte Live-Demo, die NuvaFace als AI Safety & Guidance-Plattform klar positioniert.
```

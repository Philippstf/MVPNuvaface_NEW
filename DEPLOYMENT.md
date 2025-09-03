# Medical AI Assistant Backend Deployment

## Cloud Build Deployment

Das Medical AI Assistant Backend ist jetzt bereit für Deployment über Cloud Build.

### 1. Deployment starten

```bash
# Im Hauptverzeichnis des Projekts
gcloud builds submit --config cloudbuild.yaml .
```

### 2. Deployment-Details

- **Service Name**: `nuvaface-medical-ai-assistant`
- **Region**: `us-central1`  
- **Source**: `./backend` (enthält das komplette Medical AI Assistant)
- **Resources**: 4Gi Memory, 2 CPUs, 10 min timeout
- **Concurrency**: 80 gleichzeitige Anfragen

### 3. Nach erfolgreichem Deployment

Die API wird verfügbar sein unter:
```
https://nuvaface-medical-ai-assistant-<hash>-uc.a.run.app
```

### 4. Hauptendpunkte

- `POST /api/risk-map/analyze` - Hauptanalyse-Endpunkt
- `GET /health` - Health Check
- `GET /api/info` - API Information

### 5. Frontend-Konfiguration aktualisieren

Nach dem Deployment muss die API-URL im Frontend aktualisiert werden:

**In `ui/medical-assistant-integration.js`:**
```javascript
apiEndpoint: 'https://nuvaface-medical-ai-assistant-<IHRE-URL>/api/risk-map/analyze'
```

### 6. Test der Deployment

```bash
# Health Check
curl https://nuvaface-medical-ai-assistant-<hash>-uc.a.run.app/health

# API Info
curl https://nuvaface-medical-ai-assistant-<hash>-uc.a.run.app/api/info
```

### 7. Erwartete Deployment-Zeit

- **Cold Start**: ~30-45 Sekunden (MediaPipe Model Loading)
- **Warmer Zustand**: ~2-5 Sekunden pro Analyse
- **Build Zeit**: ~5-8 Minuten

### 8. Monitoring

Nach dem Deployment können Sie die Logs überwachen:
```bash
gcloud logs read --service=nuvaface-medical-ai-assistant --limit=50
```

Das Medical AI Assistant Backend enthält:
- ✅ 50+ Injection Points (LP1-LP4, CK1-CK4, CH1-CH4, FH1-FH3)
- ✅ 25+ Risk Zones mit Severity-Levels
- ✅ MediaPipe 468-Punkt Landmark Detection
- ✅ Deterministische Koordinaten-Generierung
- ✅ Medizinische Safety Validierung
- ✅ Comprehensive Error Handling
- ✅ GDPR-konforme Datenverarbeitung
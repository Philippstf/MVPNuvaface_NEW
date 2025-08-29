# 🚀 DEPLOYMENT INSTRUCTIONS - GEMINI FIX

## Was wurde gefixt:
1. **gemini_worker.py** - Multimodal Output Konfiguration korrigiert
2. **response_modalities** für Bildgenerierung aktiviert  
3. Expliziter Prompt für Bildgenerierung hinzugefügt

## Deployment auf Cloud Run (us-central1):

### Option 1: Automatisches Deployment via Cloud Build
```bash
# Triggert automatisches Deployment nach Git Push
git add gemini_worker.py
git commit -m "Fix: Enable multimodal output for Gemini 2.5 Flash Image"
git push origin main
```

### Option 2: Manuelles Deployment
```bash
# Windows Command:
deploy-us-central.bat

# Oder direkt mit gcloud:
gcloud run deploy rmgpgab-nuvaface-api-europe-west1-philippstf-mvpnuvaface-newiem \
    --source . \
    --region=us-central1 \
    --platform=managed \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300 \
    --max-instances=10
```

## Wichtige Hinweise:

### ✅ Was funktioniert jetzt:
- Multimodal Output (Text + Bild) aktiviert
- Korrekte API-Konfiguration für Gemini 2.5 Flash Image
- Explizite Aufforderung zur Bildgenerierung

### ⚠️ Bekannte Einschränkungen:
- Gemini 2.5 Flash Image ist nur in US-Regionen verfügbar
- Cloud Run muss in us-central1 laufen (bereits konfiguriert)
- Frontend URL zeigt bereits auf die richtige us-central1 Instanz (-uc suffix)

## Test nach Deployment:

1. **Health Check:**
```bash
curl https://rmgpgab-nuvaface-api-europe-west1-philippstf-mvpn-hapllrcw7a-uc.a.run.app/health
```

2. **UI Test:**
- Öffne die Web-UI
- Lade ein Testbild hoch
- Wähle "Lippen" als Behandlungsbereich
- Stelle Slider auf 2.0ml
- Klicke "Generieren"

## Debugging bei Problemen:

### Logs prüfen:
```bash
gcloud run logs read --region=us-central1 \
    --service=rmgpgab-nuvaface-api-europe-west1-philippstf-mvpnuvaface-newiem \
    --limit=50
```

### Häufige Fehler:
- **"Multi-modal output is not supported"** → Fix wurde nicht deployed
- **Timeout Errors** → Normal bei hoher Last, Retry hilft
- **Identical Images** → API-Quota erreicht oder degraded performance

## Kontakt bei Problemen:
Die Fixes adressieren die Hauptprobleme mit der Multimodal-Konfiguration.
Das System sollte nach dem Deployment wieder Bilder generieren können.
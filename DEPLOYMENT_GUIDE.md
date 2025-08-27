# 🚀 NuvaFace MVP - Production Deployment Guide

## Architektur: Firebase + Google Cloud Run

**Optimale Lösung:**
- 🌐 **Frontend**: Firebase Hosting (UI)
- ⚡ **Backend**: Google Cloud Run (API mit Gemini)
- 🔗 **Integration**: CORS-konfiguriert, vollständig funktionsfähig

---

## 🎯 Deployment-Schritte

### 1. Backend auf Cloud Run deployen

```bash
# 1. Google Cloud CLI installieren (falls nicht vorhanden)
# https://cloud.google.com/sdk/docs/install

# 2. Automatisches Deployment
deploy-cloudrun.bat
```

**Was passiert:**
- Docker Image wird gebaut und zu Google Cloud Registry gepusht
- Cloud Run Service wird erstellt/aktualisiert
- Öffentliche URL wird generiert (z.B. `https://nuvaface-api-abc123-ew.a.run.app`)

### 2. Frontend-URL aktualisieren

Nach dem Cloud Run Deployment:

1. **Kopiere die Cloud Run URL** aus der Konsole
2. **Ersetze in `ui/app.js`:**
   ```javascript
   this.apiBaseUrl = 'https://nuvaface-api-[DEINE-HASH]-ew.a.run.app';
   ```

### 3. Frontend auf Firebase deployen

```bash
# Firebase Deployment
deploy-firebase.bat
```

---

## 🌍 URLs nach Deployment

- **Frontend**: `https://nuvafacemvp.web.app`
- **Backend**: `https://nuvaface-api-[hash]-ew.a.run.app`
- **API Docs**: `https://nuvaface-api-[hash]-ew.a.run.app/docs`

---

## 🔧 Konfiguration

### Environment Variables (Cloud Run)

Automatisch gesetzt via Deployment-Script:
- `GOOGLE_API_KEY`: Dein Gemini API Key
- `PORT`: Automatisch von Cloud Run gesetzt
- `PYTHONPATH`: `/app`

### Firebase Hosting

- **Public Directory**: `ui/`
- **Rewrites**: Keine (da separate Services)
- **CORS**: Automatisch konfiguriert

---

## 📊 Ressourcen & Kosten

### Cloud Run Konfiguration:
- **Memory**: 2GB (für ML-Models)
- **CPU**: 2 vCPUs
- **Timeout**: 300 Sekunden
- **Max Instances**: 10
- **Scaling**: Auf 0 bei Inaktivität

### Geschätzte Kosten:
- **Cloud Run**: ~$0.10 pro 1M Requests
- **Firebase Hosting**: Kostenlos (bis 10GB)
- **Total**: < $10/Monat bei moderater Nutzung

---

## ✅ Vorteile dieser Lösung

1. **🚄 Vollständige Funktionalität**
   - Gemini 2.5 Flash Image funktioniert perfekt
   - Subprocess-Aufrufe unterstützt
   - Lokale Dateien möglich

2. **📈 Automatisches Scaling**
   - Skaliert auf 0 bei Inaktivität
   - Skaliert hoch bei Traffic
   - Pay-per-use Modell

3. **🔒 Produktionstauglich**
   - HTTPS automatisch
   - Gesundheitschecks
   - Monitoring integriert

4. **🛠 Einfaches Management**
   - Ein-Klick Deployment
   - Automatische Builds
   - Version Control

---

## 🚨 Wichtige Hinweise

### CORS Konfiguration

Cloud Run ist automatisch für CORS konfiguriert. Falls Probleme auftreten, prüfe:

```python
# In api/main.py sollte stehen:
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nuvafacemvp.web.app", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Erste Anfrage (Cold Start)

- Erste Anfrage nach Inaktivität dauert ~10-30 Sekunden
- Nachfolgende Anfragen: < 2 Sekunden
- Für produktive Nutzung: Keep-Alive implementieren

---

## 📝 Deployment Checkliste

- [ ] Google Cloud CLI installiert
- [ ] `GOOGLE_API_KEY` Environment Variable gesetzt
- [ ] `deploy-cloudrun.bat` ausgeführt
- [ ] Cloud Run URL kopiert
- [ ] `ui/app.js` mit neuer URL aktualisiert  
- [ ] `deploy-firebase.bat` ausgeführt
- [ ] Funktionalität getestet

---

## 🔧 Troubleshooting

### Problem: "Service not found"
**Lösung**: Projekt-ID in `deploy-cloudrun.bat` prüfen

### Problem: "Permission denied"
**Lösung**: 
```bash
gcloud auth login
gcloud config set project nuvafacemvp
```

### Problem: CORS Fehler
**Lösung**: Cloud Run URL in `app.js` prüfen und CORS-Middleware verifizieren

---

## 🎉 Fertig!

Nach diesen Schritten hast du eine vollständig funktionsfähige, skalierbare Web-App mit:
- ✅ Gemini 2.5 Flash Image Integration
- ✅ Automatischem Scaling
- ✅ Produktions-ready Infrastruktur
- ✅ Kostenoptimiert
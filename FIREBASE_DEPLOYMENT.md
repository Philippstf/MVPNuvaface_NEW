# Firebase Deployment - NuvaFace MVP

## Übersicht

Die NuvaFace-Anwendung wurde für Firebase konfiguriert mit:
- **Firebase Hosting** für das Frontend (UI)
- **Firebase Functions** für das Backend (API)
- **Automatische URL-Rewriting** von `/api/**` zu den Functions

## Projekt-Konfiguration

- **Firebase Projekt**: `nuvafacemvp`
- **URL**: `https://nuvafacemvp.web.app`
- **Projekt-ID**: `nuvafacemvp`

## Deployment-Schritte

### 1. Voraussetzungen

```bash
# Firebase CLI installieren
npm install -g firebase-tools

# Bei Firebase anmelden
firebase login
```

### 2. Automatisches Deployment

```bash
# Einfach das Deployment-Script ausführen
deploy-firebase.bat
```

### 3. Manuelles Deployment

```bash
# Projekt setzen
firebase use nuvafacemvp

# Alles deployen
firebase deploy

# Oder einzeln deployen
firebase deploy --only hosting
firebase deploy --only functions
```

## Wichtige Hinweise

### 🚨 Einschränkungen in Firebase Functions

Die **Gemini-Integration funktioniert NICHT vollständig in Firebase Functions**, da:

1. **Subprocess-Aufrufe** nicht unterstützt werden
2. **Lokale Dateisystem-Operations** eingeschränkt sind
3. **GPU-Support** nicht verfügbar ist
4. **Virtuelle Environments** nicht wie lokal funktionieren

### 📋 Aktueller Status

- ✅ **UI (Frontend)**: Vollständig funktionsfähig
- ✅ **Health Check**: Funktioniert
- ✅ **Face Segmentation**: Sollte funktionieren (CPU-basiert)
- ❌ **Gemini Image Generation**: Nicht verfügbar in Firebase

### 💡 Empfohlene Lösungsansätze

1. **Hybrid-Ansatz**: 
   - UI über Firebase Hosting
   - API auf separatem Server (Google Cloud Run, AWS Lambda, etc.)

2. **Cloud Run Alternative**:
   - Vollständige Kontrolle über die Laufzeitumgebung
   - Docker-Container mit allen Dependencies
   - GPU-Support möglich

3. **Nur UI deployen**:
   - Firebase nur für das Frontend
   - API-Calls an lokalen/dedizierten Server

## Verwendung

Nach dem Deployment:

1. **Lokale Entwicklung**: `http://localhost:8000` (FastAPI Backend)
2. **Firebase Production**: `https://nuvafacemvp.web.app` (UI funktioniert, API eingeschränkt)

## Dateien-Struktur

```
├── firebase.json          # Firebase Konfiguration
├── .firebaserc            # Projekt-Verknüpfung
├── functions/
│   ├── main.py            # Firebase Functions Code
│   └── requirements.txt   # Python Dependencies
├── ui/                    # Frontend (wird als Hosting deployed)
│   ├── index.html
│   ├── app.js            # Automatische API-URL Erkennung
│   └── firebase-config.js # Firebase SDK Config
└── deploy-firebase.bat   # Deployment Script
```

## Nächste Schritte

Für eine vollständige Produktionsumgebung empfehlen wir:

1. **Google Cloud Run** für die API mit Dockerfile
2. **Firebase Hosting** nur für das UI
3. **Cloud Storage** für temporäre Bilder
4. **Secret Manager** für API-Keys
@echo off
echo Deploying both services to Cloud Run...
echo.

set GCLOUD="C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

echo Setting project...
%GCLOUD% config set project nuvafacemvp

echo.
echo ================================
echo DEPLOYING GEMINI SERVICE
echo ================================
%GCLOUD% builds submit --config cloudbuild.yaml .

echo.
echo ================================
echo DEPLOYING MEDICAL AI ASSISTANT
echo ================================
%GCLOUD% builds submit --config cloudbuild-medical.yaml .

echo.
echo ================================
echo DEPLOYMENT COMPLETED
echo ================================
echo GEMINI Service: https://nuvaface-gemini-api-xxxxxxxxxx-uc.a.run.app
echo Medical Assistant: https://nuvaface-medical-assistant-xxxxxxxxxx-uc.a.run.app
echo.
echo Use '%GCLOUD% run services list --region=us-central1' to see actual URLs
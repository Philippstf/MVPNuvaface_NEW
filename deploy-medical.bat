@echo off
echo Deploying Medical AI Assistant to Cloud Run...
echo.

set GCLOUD="C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

echo Setting project...
%GCLOUD% config set project nuvafacemvp

echo.
echo Submitting build for Medical AI Assistant...
%GCLOUD% builds submit --config cloudbuild-medical.yaml --region=us-central1 .

echo.
echo Medical AI Assistant deployment completed!
echo Service should be available at: https://nuvaface-medical-assistant-xxxxxxxxxx-uc.a.run.app
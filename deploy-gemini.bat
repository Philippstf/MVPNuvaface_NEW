@echo off
echo Deploying GEMINI Service to Cloud Run...
echo.

set GCLOUD="C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

echo Setting project...
%GCLOUD% config set project nuvafacemvp

echo.
echo Submitting build for GEMINI Service...
%GCLOUD% builds submit --config cloudbuild.yaml --region=us-central1 .

echo.
echo GEMINI Service deployment completed!
echo Service should be available at: https://nuvaface-gemini-api-xxxxxxxxxx-uc.a.run.app
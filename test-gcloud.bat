@echo off
echo Testing gcloud setup...
echo.

set GCLOUD="C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

echo 1. Current project:
%GCLOUD% config get-value project
echo.

echo 2. Active account:
%GCLOUD% auth list --filter=status:ACTIVE --format="value(account)"
echo.

echo 3. Checking Cloud Build API:
%GCLOUD% services list --enabled --filter="name:cloudbuild" --format="value(name)"
echo.

echo 4. Checking Cloud Run API:
%GCLOUD% services list --enabled --filter="name:run.googleapis" --format="value(name)"
echo.

echo 5. List existing Cloud Run services:
%GCLOUD% run services list --region=us-central1
echo.

echo If APIs are not enabled, run:
echo %GCLOUD% services enable cloudbuild.googleapis.com
echo %GCLOUD% services enable run.googleapis.com
echo.
pause
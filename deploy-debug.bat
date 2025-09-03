@echo off
echo DEBUG: Starting deployment...
echo.

set GCLOUD="C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

echo Step 1: Setting project...
%GCLOUD% config set project nuvafacemvp
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to set project
    exit /b %ERRORLEVEL%
)

echo.
echo Step 2: Checking project...
%GCLOUD% config get-value project

echo.
echo Step 3: Checking if Cloud Build API is enabled...
%GCLOUD% services list --enabled | findstr cloudbuild

echo.
echo Step 4: Testing simple gcloud builds submit (dry run)...
echo Testing with a simple ls command first...
%GCLOUD% builds submit --no-source --config=- <<EOF
steps:
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['version']
EOF

pause
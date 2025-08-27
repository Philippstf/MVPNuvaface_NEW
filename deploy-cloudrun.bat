@echo off
echo Deploying NuvaFace API to Google Cloud Run...

REM Set your Google Cloud project ID
set PROJECT_ID=nuvafacemvp
set SERVICE_NAME=nuvaface-api
set REGION=europe-west1

echo.
echo Project: %PROJECT_ID%
echo Service: %SERVICE_NAME%
echo Region: %REGION%
echo.

REM Check if gcloud CLI is installed
gcloud --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Google Cloud CLI not found. Please install it first:
    echo https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

REM Set the project
echo Setting Google Cloud project...
gcloud config set project %PROJECT_ID%

REM Enable required services
echo Enabling required Google Cloud services...
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

REM Build and deploy
echo Building and deploying to Cloud Run...
gcloud run deploy %SERVICE_NAME% ^
    --source . ^
    --region=%REGION% ^
    --platform=managed ^
    --allow-unauthenticated ^
    --set-env-vars="GOOGLE_API_KEY=%GOOGLE_API_KEY%" ^
    --memory=2Gi ^
    --cpu=2 ^
    --timeout=300 ^
    --max-instances=10

if %errorlevel% equ 0 (
    echo.
    echo ✅ Deployment successful!
    echo.
    echo Your API is now available at:
    gcloud run services describe %SERVICE_NAME% --region=%REGION% --format="value(status.url)"
    echo.
    echo Don't forget to update your Firebase frontend with this URL!
) else (
    echo ❌ Deployment failed!
    pause
    exit /b 1
)

pause
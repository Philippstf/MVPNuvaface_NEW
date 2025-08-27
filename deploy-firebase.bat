@echo off
echo Starting Firebase deployment for NuvaFace MVP...

REM Check if Firebase CLI is installed
firebase --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Firebase CLI not found. Installing...
    npm install -g firebase-tools
)

REM Login to Firebase (if not already logged in)
echo Checking Firebase authentication...
firebase projects:list >nul 2>&1
if %errorlevel% neq 0 (
    echo Please login to Firebase...
    firebase login
)

REM Set the project
echo Setting Firebase project...
firebase use nuvafacemvp

REM Deploy hosting and functions
echo Deploying to Firebase...
firebase deploy

echo.
echo Deployment complete!
echo Your app should be available at: https://nuvafacemvp.web.app
echo.
pause
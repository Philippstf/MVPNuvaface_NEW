# PowerShell Deployment Script for NuvaFace Services
Write-Host "Deploying both services to Cloud Run..." -ForegroundColor Cyan
Write-Host ""

$gcloud = "C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

Write-Host "Setting project..." -ForegroundColor Yellow
& $gcloud config set project nuvafacemvp

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "DEPLOYING GEMINI SERVICE" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "Starting Cloud Build for GEMINI Service..."
& $gcloud builds submit --config cloudbuild.yaml --region=us-central1 .
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ GEMINI Service deployed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ GEMINI Service deployment failed!" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Blue
Write-Host "DEPLOYING MEDICAL AI ASSISTANT" -ForegroundColor Blue
Write-Host "================================" -ForegroundColor Blue
Write-Host "Starting Cloud Build for Medical AI Assistant..."
& $gcloud builds submit --config cloudbuild-medical.yaml --region=us-central1 .
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Medical AI Assistant deployed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Medical AI Assistant deployment failed!" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================" -ForegroundColor Magenta
Write-Host "DEPLOYMENT COMPLETED" -ForegroundColor Magenta
Write-Host "================================" -ForegroundColor Magenta

Write-Host ""
Write-Host "Fetching service URLs..." -ForegroundColor Yellow
$services = & $gcloud run services list --region=us-central1 --format="table(SERVICE:label=SERVICE,URL)" 2>$null

Write-Host $services
Write-Host ""
Write-Host "Done!" -ForegroundColor Green
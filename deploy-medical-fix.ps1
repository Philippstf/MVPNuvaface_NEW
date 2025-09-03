# Quick fix for Medical AI Assistant Dockerfile issue
Write-Host "Fixing and redeploying Medical AI Assistant..." -ForegroundColor Yellow

$gcloud = "C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

Write-Host "Setting project..." -ForegroundColor Cyan
& $gcloud config set project nuvafacemvp

Write-Host ""
Write-Host "Deploying Medical AI Assistant with fixed Dockerfile..." -ForegroundColor Green
& $gcloud builds submit --config cloudbuild-medical.yaml --region=us-central1 .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Medical AI Assistant deployed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Service URL:" -ForegroundColor Cyan
    & $gcloud run services describe nuvaface-medical-assistant --region=us-central1 --format="value(status.url)"
} else {
    Write-Host ""
    Write-Host "❌ Deployment failed! Check the logs above." -ForegroundColor Red
}
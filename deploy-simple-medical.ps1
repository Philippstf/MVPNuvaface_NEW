# Deploy simple Medical AI Assistant
Write-Host "Deploying Simple Medical AI Assistant..." -ForegroundColor Green

$gcloud = "C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

Write-Host "Building and deploying simple version..." -ForegroundColor Cyan
& $gcloud builds submit --config cloudbuild-medical-simple.yaml --region=us-central1 .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Simple Medical Assistant deployed successfully!" -ForegroundColor Green
    Write-Host "URL: https://nuvaface-medical-assistant-212268956806.us-central1.run.app" -ForegroundColor Cyan
} else {
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
}
# Deploy GEMINI Service with updated prompts
Write-Host "Deploying GEMINI Service with improved prompts..." -ForegroundColor Green

$gcloud = "C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

Write-Host "Setting project..." -ForegroundColor Cyan
& $gcloud config set project nuvafacemvp

Write-Host ""
Write-Host "Building and deploying GEMINI Service..." -ForegroundColor Yellow
& $gcloud builds submit --config cloudbuild.yaml --region=us-central1 .

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ GEMINI Service deployed successfully!" -ForegroundColor Green
    Write-Host "URL: https://nuvaface-gemini-api-212268956806.us-central1.run.app" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Updated prompts should now:" -ForegroundColor Yellow
    Write-Host "✅ Remove artificial lip borders/outlines" -ForegroundColor Green
    Write-Host "✅ Keep natural skin transitions" -ForegroundColor Green  
    Write-Host "✅ Maintain desired volume levels" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
}
# Cleanup old service with long name
Write-Host "Removing old service with long name..." -ForegroundColor Yellow

$gcloud = "C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# Delete old service
Write-Host "Deleting: rmgpgab-nuvaface-api-europe-west1-philippstf-mvpnuvaface-newiem"
& $gcloud run services delete rmgpgab-nuvaface-api-europe-west1-philippstf-mvpnuvaface-newiem --region=us-central1 --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Old service deleted successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to delete old service!" -ForegroundColor Red
}

Write-Host ""
Write-Host "Current services:" -ForegroundColor Cyan
& $gcloud run services list --region=us-central1
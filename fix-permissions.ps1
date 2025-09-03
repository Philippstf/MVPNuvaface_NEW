# Automatically fix IAM permissions for Cloud Build and Cloud Run
Write-Host "Fixing IAM permissions for deployment..." -ForegroundColor Green

$gcloud = "C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

$email = & $gcloud config get-value account
Write-Host "Adding permissions for: $email" -ForegroundColor Cyan

Write-Host ""
Write-Host "Adding Cloud Build Editor role..." -ForegroundColor Yellow
& $gcloud projects add-iam-policy-binding nuvafacemvp --member="user:$email" --role="roles/cloudbuild.builds.editor"

Write-Host ""
Write-Host "Adding Cloud Run Admin role..." -ForegroundColor Yellow  
& $gcloud projects add-iam-policy-binding nuvafacemvp --member="user:$email" --role="roles/run.admin"

Write-Host ""
Write-Host "Adding Storage Admin role..." -ForegroundColor Yellow
& $gcloud projects add-iam-policy-binding nuvafacemvp --member="user:$email" --role="roles/storage.admin"

Write-Host ""
Write-Host "Adding Service Account User role..." -ForegroundColor Yellow
& $gcloud projects add-iam-policy-binding nuvafacemvp --member="user:$email" --role="roles/iam.serviceAccountUser"

Write-Host ""
Write-Host "✅ Permissions updated! Try deployment again." -ForegroundColor Green
Write-Host ""
Write-Host "Run './deploy-both.ps1' to test deployment now." -ForegroundColor Cyan
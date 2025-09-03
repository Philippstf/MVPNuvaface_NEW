# Check and fix IAM permissions for Cloud Build and Cloud Run
Write-Host "Checking IAM permissions..." -ForegroundColor Yellow

$gcloud = "C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

Write-Host "Current user:" -ForegroundColor Cyan
& $gcloud config get-value account

Write-Host ""
Write-Host "Current project:" -ForegroundColor Cyan
& $gcloud config get-value project

Write-Host ""
Write-Host "Checking required roles..." -ForegroundColor Yellow

$email = & $gcloud config get-value account

Write-Host ""
Write-Host "Current IAM policy (filtering for your account):" -ForegroundColor Cyan
& $gcloud projects get-iam-policy nuvafacemvp --flatten="bindings[].members" --format="table(bindings.role)" --filter="bindings.members:$email"

Write-Host ""
Write-Host "Required roles for Cloud Build + Cloud Run:" -ForegroundColor Green
Write-Host "- roles/cloudbuild.builds.editor"
Write-Host "- roles/run.admin" 
Write-Host "- roles/storage.admin"
Write-Host "- roles/iam.serviceAccountUser"

Write-Host ""
Write-Host "To add missing roles, run:" -ForegroundColor Yellow
Write-Host "& '$gcloud' projects add-iam-policy-binding nuvafacemvp --member='user:$email' --role='roles/cloudbuild.builds.editor'"
Write-Host "& '$gcloud' projects add-iam-policy-binding nuvafacemvp --member='user:$email' --role='roles/run.admin'"
Write-Host "& '$gcloud' projects add-iam-policy-binding nuvafacemvp --member='user:$email' --role='roles/storage.admin'" 
Write-Host "& '$gcloud' projects add-iam-policy-binding nuvafacemvp --member='user:$email' --role='roles/iam.serviceAccountUser'"
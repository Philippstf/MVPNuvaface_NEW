# Debug the actual IAM permission issue
Write-Host "Debugging IAM permissions issue..." -ForegroundColor Yellow

$gcloud = "C:\Users\phlpp\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

Write-Host "Owner role should include all permissions. Checking deeper..." -ForegroundColor Cyan

Write-Host ""
Write-Host "1. Testing Cloud Build access:" -ForegroundColor Yellow
& $gcloud builds list --limit=3

Write-Host ""
Write-Host "2. Testing Cloud Run access:" -ForegroundColor Yellow  
& $gcloud run services list --region=us-central1 --limit=3

Write-Host ""
Write-Host "3. Checking Cloud Build service account:" -ForegroundColor Yellow
$project_number = & $gcloud projects describe nuvafacemvp --format="value(projectNumber)"
Write-Host "Project number: $project_number"
Write-Host "Cloud Build service account should be: ${project_number}-compute@developer.gserviceaccount.com"

Write-Host ""
Write-Host "4. Check if Cloud Build service account has Cloud Run permissions:" -ForegroundColor Yellow
& $gcloud projects get-iam-policy nuvafacemvp --flatten="bindings[].members" --format="table(bindings.role)" --filter="bindings.members:${project_number}-compute@developer.gserviceaccount.com"

Write-Host ""
Write-Host "5. Specific error context - where did you see 'Berechtigung verweigert'?" -ForegroundColor Red
Write-Host "Was it during:"
Write-Host "a) gcloud builds submit"  
Write-Host "b) Cloud Run deployment"
Write-Host "c) Container startup"
Write-Host "d) Other operation"
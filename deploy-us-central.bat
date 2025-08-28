@echo off
echo Manual deployment to us-central1...

gcloud run deploy rmgpgab-nuvaface-api-europe-west1-philippstf-mvpnuvaface-newiem ^
    --source . ^
    --region=us-central1 ^
    --platform=managed ^
    --allow-unauthenticated ^
    --memory=2Gi ^
    --cpu=2 ^
    --timeout=300 ^
    --max-instances=10

echo Deployment complete!
pause
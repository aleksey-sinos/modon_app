# Load secrets from modon/.env
Get-Content modon/.env | Where-Object { $_ -match '^\s*[^#]\S+=\S' } | ForEach-Object {
    $parts = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
}

$MAPS_KEY   = $env:VITE_GOOGLE_MAPS_API_KEY
$GEMINI_KEY = $env:GEMINI_API_KEY

$RESOURCE_GROUP = "modon-rg"
$ACR_NAME       = "modoncr"
$APP_NAME       = "modon-app"
$ACR_SERVER     = (az acr show --name $ACR_NAME --query loginServer -o tsv)
$TAG            = Get-Date -Format 'yyyyMMddHHmmss'

Write-Host "Building image with tag $TAG..."
docker build `
  -f modon/Dockerfile `
  --build-arg "VITE_GOOGLE_MAPS_API_KEY=$MAPS_KEY" `
  --build-arg "VITE_API_URL=/api" `
  --build-arg "CACHE_BUST=$TAG" `
  -t "$ACR_SERVER/modon-app:$TAG" `
  .

Write-Host "Logging in to ACR..."
$ACR_PASSWORD = (az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
docker login $ACR_SERVER -u $ACR_NAME -p $ACR_PASSWORD

Write-Host "Pushing image..."
docker push "$ACR_SERVER/modon-app:$TAG"

Write-Host "Updating secret..."
az containerapp secret set `
  --name $APP_NAME --resource-group $RESOURCE_GROUP `
  --secrets "gemini-api-key=$GEMINI_KEY"

Write-Host "Deploying $TAG to Container Apps..."
az containerapp update `
  --name $APP_NAME --resource-group $RESOURCE_GROUP `
  --image "$ACR_SERVER/modon-app:$TAG" `
  --set-env-vars "GEMINI_API_KEY=secretref:gemini-api-key"

Write-Host "Done. Image: $ACR_SERVER/modon-app:$TAG"

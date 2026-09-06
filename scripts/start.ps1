$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
Set-Location $rootDir

$ImageName = "pm-app"
$ContainerName = "pm-app"

if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^$ContainerName$") {
    Write-Host "Stopping existing container..."
    docker rm -f $ContainerName | Out-Null
}

if (Test-Path (Join-Path $rootDir ".env")) {
    docker build -t $ImageName .
    docker run --rm -d --name $ContainerName --env-file (Join-Path $rootDir ".env") -p 8000:8000 $ImageName
} else {
    docker build -t $ImageName .
    docker run --rm -d --name $ContainerName -p 8000:8000 $ImageName
}

Write-Host "Application started at http://localhost:8000"

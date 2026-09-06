$ErrorActionPreference = "Stop"

$ContainerName = "pm-app"

if (docker ps -a --format "{{.Names}}" | Select-String -Pattern "^$ContainerName$") {
    docker rm -f $ContainerName | Out-Null
    Write-Host "Stopped container: $ContainerName"
} else {
    Write-Host "Container not running: $ContainerName"
}

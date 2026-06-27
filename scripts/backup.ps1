param(
    [string]$OutputDir = "backups",
    [string]$MongoService = "mongo",
    [string]$BackendUploadVolume = "knowledgebasedmanager_backend_uploads"
)

$ErrorActionPreference = "Stop"

function Resolve-ComposeProjectName {
    $project = docker compose ls --format json | ConvertFrom-Json | Where-Object { $_.ConfigFiles -like "*docker-compose.yml*" } | Select-Object -First 1
    if ($project -and $project.Name) {
        return $project.Name
    }
    return (Split-Path -Leaf (Get-Location)).ToLowerInvariant() -replace "[^a-z0-9]", ""
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path $OutputDir $timestamp
$mongoDir = Join-Path $backupRoot "mongo"
$uploadsDir = Join-Path $backupRoot "uploads"
New-Item -ItemType Directory -Force -Path $mongoDir, $uploadsDir | Out-Null
$mongoArchive = Join-Path $mongoDir "mongo.archive"
$mongoDirAbsolute = (Resolve-Path $mongoDir).Path
$uploadsDirAbsolute = (Resolve-Path $uploadsDir).Path

$projectName = Resolve-ComposeProjectName
$uploadVolume = if ($BackendUploadVolume) { $BackendUploadVolume } else { "${projectName}_backend_uploads" }
$mongoContainer = docker compose ps -q $MongoService
if (-not $mongoContainer) {
    throw "Mongo service container not found. Start the stack with 'docker compose up -d mongo' first."
}

Write-Host "Creating MongoDB dump..."
docker run --rm --network "container:$mongoContainer" -v "${mongoDirAbsolute}:/backup" mongo:7 mongodump --host 127.0.0.1 --archive=/backup/mongo.archive

Write-Host "Archiving uploaded files from volume $uploadVolume..."
docker run --rm -v "${uploadVolume}:/source:ro" -v "${uploadsDirAbsolute}:/backup" alpine sh -c "cd /source && tar -czf /backup/uploads.tar.gz ."

$manifest = [ordered]@{
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    compose_project = $projectName
    mongo_archive = "mongo/mongo.archive"
    uploads_archive = "uploads/uploads.tar.gz"
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 -Path (Join-Path $backupRoot "manifest.json")

Write-Host "Backup complete: $backupRoot"

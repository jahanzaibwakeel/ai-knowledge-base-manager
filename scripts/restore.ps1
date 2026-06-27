param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDir,
    [string]$MongoService = "mongo",
    [string]$BackendUploadVolume = "knowledgebasedmanager_backend_uploads",
    [switch]$ConfirmRestore
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmRestore) {
    throw "Restore is destructive. Re-run with -ConfirmRestore after verifying BackupDir."
}

$mongoArchive = Join-Path $BackupDir "mongo\mongo.archive"
$uploadsArchive = Join-Path $BackupDir "uploads\uploads.tar.gz"
$mongoDirAbsolute = (Resolve-Path (Join-Path $BackupDir "mongo")).Path
$uploadsDirAbsolute = (Resolve-Path (Join-Path $BackupDir "uploads")).Path

if (-not (Test-Path $mongoArchive)) {
    throw "Missing Mongo archive: $mongoArchive"
}
if (-not (Test-Path $uploadsArchive)) {
    throw "Missing uploads archive: $uploadsArchive"
}
$mongoContainer = docker compose ps -q $MongoService
if (-not $mongoContainer) {
    throw "Mongo service container not found. Start the stack with 'docker compose up -d mongo' first."
}

Write-Host "Restoring MongoDB from $mongoArchive..."
docker run --rm --network "container:$mongoContainer" -v "${mongoDirAbsolute}:/backup:ro" mongo:7 mongorestore --host 127.0.0.1 --archive=/backup/mongo.archive --drop

Write-Host "Restoring uploaded files into volume $BackendUploadVolume..."
docker run --rm -v "${BackendUploadVolume}:/target" -v "${uploadsDirAbsolute}:/backup:ro" alpine sh -c "rm -rf /target/* && tar -xzf /backup/uploads.tar.gz -C /target"

Write-Host "Restore complete."

# Operations Scripts

These scripts provide no-cost backup and restore helpers for Docker Compose deployments.

## Backup

```powershell
.\scripts\backup.ps1
```

This creates a timestamped directory under `backups/` with:

- `mongo/mongo.archive`: MongoDB dump
- `uploads/uploads.tar.gz`: uploaded source files from the backend upload volume
- `manifest.json`: backup metadata

## Restore

Restore is destructive because it drops MongoDB collections and replaces uploaded files.

```powershell
.\scripts\restore.ps1 -BackupDir backups\YYYYMMDD-HHMMSS -ConfirmRestore
```

## Volume Name

The default upload volume is `knowledgebasedmanager_backend_uploads`. If your Compose project name is different, pass it explicitly:

```powershell
.\scripts\backup.ps1 -BackendUploadVolume yourproject_backend_uploads
.\scripts\restore.ps1 -BackupDir backups\YYYYMMDD-HHMMSS -BackendUploadVolume yourproject_backend_uploads -ConfirmRestore
```

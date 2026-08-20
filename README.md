# Markee export

Sanitized project export compiled from local Markee sources.

Includes:
- main Markee project under `projects/markee/`
- Markee worktrees under `projects/markee-worktrees/`
- related backups/review/gate artifacts

Excluded deliberately:
- `.git` directories
- dependency/build/cache directories (`node_modules`, `.venv`, `.next`, `dist`, `build`, caches)
- runtime `.env` files and private-key/cert-like files

See `MARKEE_EXPORT_MANIFEST.json`, `MARKEE_EXPORT_FILELIST.txt`, and `MARKEE_EXPORT_EXCLUDED.txt`.

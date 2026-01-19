# Dev Notes

## Gates + Commit Firewall

Install hooks (once per clone):
- powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Install-Hooks.ps1

Run gates (mints .gates/LAST_GREEN.txt; required before commit):
- powershell -NoProfile -ExecutionPolicy Bypass -File .\Run-Gates.ps1

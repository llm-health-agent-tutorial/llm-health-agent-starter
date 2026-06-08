# One-command install for Windows PowerShell. uv-first (provisions Python 3.11), else a
# 3.10-3.12 venv fallback. Run from an elevated-or-normal PowerShell:
#     powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$Kernel = "health-agent"
Write-Host "==> healthagent installer"

if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "==> uv found: provisioning Python 3.11 and syncing from uv.lock (locked)"
    uv sync --locked --extra notebooks --extra dev --python 3.11
    & .\.venv\Scripts\Activate.ps1
} else {
    $pyv = (python -c "import sys;print('%d.%d'%sys.version_info[:2])")
    if ($pyv -in @("3.10", "3.11", "3.12")) {
        Write-Host "==> pip fallback: installing pinned deps from requirements.txt"
        python -m venv .venv
        & .\.venv\Scripts\Activate.ps1
        python -m pip install --upgrade pip
        pip install -r requirements.txt   # pinned deps (derived from uv.lock; includes Jupyter)
        pip install -e . --no-deps        # the project only
    } else {
        Write-Error "System Python is $pyv; this project pins 3.10-3.12. Install uv or conda and re-run."
        exit 1
    }
}

Write-Host "==> registering Jupyter kernel '$Kernel'"
python -m ipykernel install --user --name $Kernel --display-name $Kernel 2>$null

if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host "==> wrote .env (HA_BACKEND=scripted)" }

Write-Host "==> verifying"
ha-check
Write-Host "`nDone. Activate with:  .\.venv\Scripts\Activate.ps1"
Write-Host "Then:                 jupyter lab notebooks\   (pick the '$Kernel' kernel)"

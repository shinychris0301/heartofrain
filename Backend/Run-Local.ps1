param([ValidateRange(1024,65535)][int]$Port=8751)
$ErrorActionPreference='Stop'
$python=Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if(-not(Test-Path -LiteralPath $python)){throw 'Create Backend/.venv and install Backend/requirements.lock first.'}
Push-Location $PSScriptRoot
try{ & $python -m uvicorn hotr_backend.api:create_app --factory --host 127.0.0.1 --port $Port --no-access-log --no-proxy-headers --limit-concurrency 32
    if($LASTEXITCODE -ne 0){throw 'Backend service stopped with an error.'}
}finally{Pop-Location}

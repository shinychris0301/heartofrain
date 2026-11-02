$ErrorActionPreference = 'Stop'
$repoPath = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repoPath '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create .venv with Python 3.12 and install Verification/requirements.txt first. See Verification/README.md.'
}
Push-Location $repoPath
try {
    & $pythonPath -X utf8 'Codex_Handoff/Tools/audit_project.py' --unity Unity --out Verification/Evidence/StaticCurrent
    if ($LASTEXITCODE -ne 0) { throw 'Static inventory failed.' }
    & $pythonPath -X utf8 'Verification/Tools/check_integrity.py' --allow-documented-changes --out Verification/Evidence/Integrity_Current.json
    if ($LASTEXITCODE -ne 0) {
        throw 'Unexpected file/GUID/reference integrity differences; inspect Integrity_Current.json.'
    }
    & $pythonPath -X utf8 'Verification/Tools/review_content.py'
    if ($LASTEXITCODE -ne 0) { throw 'Content or workbook arithmetic checks failed.' }
} finally { Pop-Location }

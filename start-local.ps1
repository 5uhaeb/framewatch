$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend'
$pythonPath = Join-Path $backendRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Set up backend/.venv using the README before starting.' }
$server = Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','main:app','--host','127.0.0.1','--port','8016') -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru
try {
    Set-Location -LiteralPath $frontendRoot
    npm run dev
} finally {
    if (-not $server.HasExited) { Stop-Process -Id $server.Id }
}

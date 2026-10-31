$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$choicegapPython = Join-Path $env:LOCALAPPDATA 'Python\pythoncore-3.14-64\python.exe'
if (-not (Test-Path -LiteralPath $choicegapPython)) {
    $choicegapPython = (Get-Command python -ErrorAction Stop).Source
}
$choicegapEnvironment = Join-Path $PSScriptRoot 'work\choicegap-venv'
$choicegapLocalPython = Join-Path $choicegapEnvironment 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $choicegapLocalPython)) {
    Write-Host 'Preparing the local ChoiceGap environment...'
    & $choicegapPython -m venv $choicegapEnvironment
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the local Python environment.' }
}
& $choicegapLocalPython -c "import importlib.util,sys; sys.exit(0 if importlib.util.find_spec('websockets') else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Installing the declared project dependencies for streaming voice...'
    & $choicegapLocalPython -m pip install -e .
    if ($LASTEXITCODE -ne 0) { throw 'Dependency setup failed. Check your internet connection and try again.' }
}
Write-Host 'Open http://127.0.0.1:8000/?mode=researcher to create a study.'
Write-Host 'Leave this window running. Press Ctrl+C to stop ChoiceGap.'
& $choicegapLocalPython -m choicegap.server

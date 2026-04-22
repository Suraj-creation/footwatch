param(
    [string]$SourceRoot = (Join-Path $PSScriptRoot ".."),
    [string]$BuildRoot = (Join-Path $PSScriptRoot "..\infra\terraform\build")
)

$ErrorActionPreference = "Stop"

$SourceRoot = (Resolve-Path $SourceRoot).Path
$BuildRoot = [System.IO.Path]::GetFullPath($BuildRoot)

$requirementsPath = Join-Path $SourceRoot "requirements.lambda.txt"
$pythonExe = Join-Path $SourceRoot ".venv\Scripts\python.exe"
$servicesPath = Join-Path $SourceRoot "services"
$packageDir = Join-Path $BuildRoot "package"
$zipPath = Join-Path $BuildRoot "backend_bundle.zip"

if (-not (Test-Path $requirementsPath)) {
    throw "Could not find requirements.txt at $requirementsPath"
}

if (-not (Test-Path $pythonExe)) {
    throw "Could not find virtualenv Python at $pythonExe"
}

if (-not (Test-Path $servicesPath)) {
    throw "Could not find services directory at $servicesPath"
}

New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null

if (Test-Path $packageDir) {
    Remove-Item -LiteralPath $packageDir -Recurse -Force
}

if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

New-Item -ItemType Directory -Force -Path $packageDir | Out-Null

& $pythonExe -m pip install `
    --upgrade `
    --only-binary=:all: `
    --platform manylinux2014_x86_64 `
    --implementation cp `
    --python-version 3.11 `
    -r $requirementsPath `
    -t $packageDir
if ($LASTEXITCODE -ne 0) {
    throw "pip install failed with exit code $LASTEXITCODE"
}

Copy-Item -LiteralPath $servicesPath -Destination (Join-Path $packageDir "services") -Recurse -Force

Compress-Archive -Path (Join-Path $packageDir "*") -DestinationPath $zipPath -CompressionLevel Optimal

Write-Output $zipPath

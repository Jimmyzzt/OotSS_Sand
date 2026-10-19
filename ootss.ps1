# Keep uv/Python temporary writes in this workspace (Windows sandbox friendly).
$taskRoot = $PSScriptRoot
$taskTemp = Join-Path $taskRoot 'cache/tmp'
New-Item -ItemType Directory -Path $taskTemp -Force | Out-Null
$env:TEMP = $taskTemp
$env:TMP = $taskTemp
$env:UV_CACHE_DIR = Join-Path $taskRoot 'cache/uv'
$env:UV_LINK_MODE = 'copy'
Push-Location $taskRoot
try {
    uv run --locked python -m ootss @args
    $taskExit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $taskExit

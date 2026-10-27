# Install the /visuals effect skills into your Claude skills directory.
# Usage: ./install.ps1        ($env:CLAUDE_SKILLS_DIR = "C:\path"; ./install.ps1  for a custom location)
$ErrorActionPreference = "Stop"
$Src = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "skills"
if ($env:CLAUDE_SKILLS_DIR) { $Dest = $env:CLAUDE_SKILLS_DIR } else { $Dest = Join-Path $HOME ".claude\skills" }
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Get-ChildItem -Directory $Src | ForEach-Object {
    $Target = Join-Path $Dest $_.Name
    if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }
    Copy-Item -Recurse $_.FullName $Target
    Write-Host "installed $($_.Name) -> $Target" -ForegroundColor Green
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "WARNING: ffmpeg not found on PATH - install it:  winget install Gyan.FFmpeg" -ForegroundColor Yellow
}
& python -c "import cv2, numpy, PIL" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "WARNING: run  pip install -r requirements.txt" -ForegroundColor Yellow }
Write-Host ""
Write-Host "Restart Claude Code, then try:  /orbit"

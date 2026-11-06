# setup_env.ps1
# Sets environment variables to keep all temporary files and caches within D:\gitAnalyserProject

$projectRoot = "D:\gitAnalyserProject"
$cacheRoot = Join-Path $projectRoot ".cache"

$env:TEMP = Join-Path $cacheRoot "tmp"
$env:TMP = Join-Path $cacheRoot "tmp"
$env:PIP_CACHE_DIR = Join-Path $cacheRoot "pip"
$env:npm_config_cache = Join-Path $cacheRoot "npm"
$env:npm_config_prefix = Join-Path $cacheRoot "npm-global"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $cacheRoot "ms-playwright"
$env:PYTHONPYCACHEPREFIX = Join-Path $cacheRoot "pycache"
$env:PYTHONPATH = $projectRoot

# Ensure all cache directories exist
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
New-Item -ItemType Directory -Force -Path $env:PIP_CACHE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path $env:npm_config_cache | Out-Null
New-Item -ItemType Directory -Force -Path $env:npm_config_prefix | Out-Null
New-Item -ItemType Directory -Force -Path $env:PLAYWRIGHT_BROWSERS_PATH | Out-Null
New-Item -ItemType Directory -Force -Path $env:PYTHONPYCACHEPREFIX | Out-Null

# If Python virtual environment exists, prepend it to PATH
$venvScripts = Join-Path $projectRoot ".venv\Scripts"
if (Test-Path $venvScripts) {
    $env:PATH = "$venvScripts;$env:PATH"
}

Write-Host "CodeProvenance environment initialized on D: drive."
Write-Host "  TEMP/TMP:                 $env:TEMP"
Write-Host "  PIP_CACHE_DIR:            $env:PIP_CACHE_DIR"
Write-Host "  npm_config_cache:         $env:npm_config_cache"
Write-Host "  PLAYWRIGHT_BROWSERS_PATH: $env:PLAYWRIGHT_BROWSERS_PATH"
Write-Host "  PYTHONPYCACHEPREFIX:      $env:PYTHONPYCACHEPREFIX"

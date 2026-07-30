# =============================================================================
#  LifeCity Local · Empaquetador (lo corres TÚ, una vez, para distribuir)
# -----------------------------------------------------------------------------
#  Genera LifeCity-Local.zip con lo que el instalador necesita en el PC:
#    package\ai\        -> backend (ai\server.py + módulos) = proxy GPU /detect
#    package\detector\  -> repo 68 (PointNet++ + checkpoints entrenados)
#
#  Luego sube ese zip como Release en GitHub (o Drive con enlace directo) y
#  pon la URL en install.ps1 ($PackageUrl). O deja el zip junto a install.ps1.
# =============================================================================
$ErrorActionPreference = 'Stop'

# ---- Rutas de origen (ajusta si difieren) ----------------------------------
$RepoRoot    = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)  # ...\44. Visor
$AiSrc       = Join-Path $RepoRoot 'ai'
$DetectorSrc = 'G:\Mi unidad\6. REPOS\68 RED NEURONAL + NUBE DE PUNTOS'
# ----------------------------------------------------------------------------

$Out  = Join-Path $env:TEMP 'lifecity-package'
$Pkg  = Join-Path $Out 'package'
$Zip  = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'LifeCity-Local.zip'

function Say($m,$c='Cyan'){ Write-Host "  $m" -ForegroundColor $c }

if (Test-Path $Out) { Remove-Item $Out -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Pkg | Out-Null

# --- Backend (ai\) — sin secretos ni caché ---------------------------------
Say "Copiando backend (ai\)..." 'Yellow'
$aiDst = Join-Path $Pkg 'ai'
New-Item -ItemType Directory -Force -Path $aiDst | Out-Null
Get-ChildItem $AiSrc -Force | Where-Object {
  $_.Name -notin @('__pycache__','keys.bat','data') -and $_.Name -notlike '*.log'
} | ForEach-Object { Copy-Item $_.FullName (Join-Path $aiDst $_.Name) -Recurse -Force }
# keys.bat NO se distribuye (secretos). El proxy GPU no necesita NVIDIA.

# --- Detector (repo 68) — incluye checkpoints -------------------------------
if (Test-Path $DetectorSrc) {
  Say "Copiando detector (repo 68 + modelo)..." 'Yellow'
  $detDst = Join-Path $Pkg 'detector'
  New-Item -ItemType Directory -Force -Path $detDst | Out-Null
  Get-ChildItem $DetectorSrc -Force | Where-Object {
    $_.Name -notin @('__pycache__','.git','.venv','venv','node_modules') -and $_.Name -notlike '*.log'
  } | ForEach-Object { Copy-Item $_.FullName (Join-Path $detDst $_.Name) -Recurse -Force }
  if (-not (Test-Path (Join-Path $detDst 'server.py'))) {
    Say "AVISO: no encontré detector\server.py. Ajusta el módulo uvicorn en start-lifecity-local.ps1 al entrypoint real del repo 68." 'Red'
  }
} else {
  Say "AVISO: no existe $DetectorSrc. El zip irá SIN detector; ajusta \$DetectorSrc." 'Red'
}

# --- Comprimir --------------------------------------------------------------
Say "Comprimiendo -> $Zip" 'Yellow'
if (Test-Path $Zip) { Remove-Item $Zip -Force }
Compress-Archive -Path (Join-Path $Pkg '*') -DestinationPath $Zip -Force
$mb = [math]::Round((Get-Item $Zip).Length / 1MB, 1)
Say "LISTO: $Zip ($mb MB)" 'Green'
Say "Súbelo como Release y pon la URL en install.ps1 (\$PackageUrl), o déjalo aquí junto a install.ps1." 'Cyan'

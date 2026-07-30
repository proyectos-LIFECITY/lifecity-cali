# =============================================================================
#  LifeCity Local · Instalador (PowerShell)
# -----------------------------------------------------------------------------
#  Instala en el PC del usuario SOLO las funciones que necesitan GPU/CUDA:
#    - Detector de elementos (repo 68 · PointNet++)  -> http://127.0.0.1:8068
#    - Backend de proxy GPU (ai/server.py: /detect)  -> http://127.0.0.1:8000
#  El resto de LifeCity (catastro, agentes, IA de texto) corre en la NUBE.
#
#  Qué hace:
#    1) Comprueba/instala Python 3.11 (winget).
#    2) Descarga el paquete LifeCity-Local.zip (backend + detector + modelo).
#    3) Crea un entorno virtual e instala dependencias (PyTorch CUDA incluido).
#    4) Registra una tarea al iniciar sesión para arrancar en segundo plano.
#    5) Arranca los servicios ya mismo (bind SOLO a 127.0.0.1 = sin firewall).
#
#  El visor (https://app.lifecity.com.co) detecta el agente local por
#  http://127.0.0.1:8000/health y usa la GPU automáticamente.
# =============================================================================
$ErrorActionPreference = 'Stop'

# ---- CONFIGURA ESTO (una vez) ----------------------------------------------
# URL del paquete LifeCity-Local.zip (genéralo con build-package.ps1 y súbelo
# como Release en GitHub, a Drive con enlace directo, etc.). Si dejas el zip
# junto a este script, el instalador lo usa sin descargar nada.
$PackageUrl = 'https://github.com/LifeCity/lifecity-local/releases/latest/download/LifeCity-Local.zip'
# ----------------------------------------------------------------------------

$InstallDir = Join-Path $env:LOCALAPPDATA 'LifeCity'
$AppDir     = Join-Path $InstallDir 'app'      # aquí quedan ai\ y detector\
$VenvDir    = Join-Path $InstallDir 'venv'
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path

function Say($m, $c = 'Cyan') { Write-Host "  $m" -ForegroundColor $c }

Write-Host ""
Say "LifeCity Local · instalando en $InstallDir" 'Yellow'
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# --- 1) Python -------------------------------------------------------------
$py = (Get-Command py -ErrorAction SilentlyContinue)
if (-not $py) { $py = (Get-Command python -ErrorAction SilentlyContinue) }
if (-not $py) {
  Say "Python no encontrado. Instalando Python 3.11 (winget)..." 'Yellow'
  try { winget install -e --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements }
  catch { Say "No pude instalar Python automáticamente. Instálalo desde https://www.python.org/downloads/ y reejecuta." 'Red'; Read-Host "Enter para salir"; exit 1 }
  $env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
}
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) { $pythonExe = 'py' }
Say "Python: $pythonExe" 'Green'

# --- 2) Paquete (backend + detector + modelo) ------------------------------
$localZip = Join-Path $ScriptDir 'LifeCity-Local.zip'
$zip = Join-Path $InstallDir 'LifeCity-Local.zip'
if (Test-Path $localZip) {
  Say "Usando paquete local: $localZip" 'Green'
  Copy-Item $localZip $zip -Force
} else {
  Say "Descargando paquete desde $PackageUrl ..." 'Yellow'
  try { Invoke-WebRequest -Uri $PackageUrl -OutFile $zip -UseBasicParsing }
  catch { Say "No pude descargar el paquete. Verifica \$PackageUrl o coloca LifeCity-Local.zip junto a install.ps1." 'Red'; Read-Host "Enter para salir"; exit 1 }
}
Say "Descomprimiendo..." 'Yellow'
if (Test-Path $AppDir) { Remove-Item $AppDir -Recurse -Force }
Expand-Archive -Path $zip -DestinationPath $AppDir -Force

# --- 3) Entorno virtual + dependencias -------------------------------------
if (-not (Test-Path $VenvDir)) {
  Say "Creando entorno virtual..." 'Yellow'
  & $pythonExe -m venv $VenvDir
}
$pip = Join-Path $VenvDir 'Scripts\pip.exe'
$vpython = Join-Path $VenvDir 'Scripts\python.exe'
Say "Instalando dependencias (esto puede tardar; incluye PyTorch)..." 'Yellow'
& $pip install --upgrade pip | Out-Null
# PyTorch con CUDA (usa GPU si hay driver; si no, cae a CPU).
try { & $pip install torch --index-url https://download.pytorch.org/whl/cu121 } catch { Say "PyTorch CUDA falló; instalando CPU." 'Yellow'; & $pip install torch }
if (Test-Path (Join-Path $AppDir 'ai\requirements.txt'))       { & $pip install -r (Join-Path $AppDir 'ai\requirements.txt') }
if (Test-Path (Join-Path $AppDir 'detector\requirements.txt')) { & $pip install -r (Join-Path $AppDir 'detector\requirements.txt') }

# --- 4) Lanzador + arranque al iniciar sesión ------------------------------
Copy-Item (Join-Path $ScriptDir 'start-lifecity-local.ps1') (Join-Path $InstallDir 'start-lifecity-local.ps1') -Force
$startPs = Join-Path $InstallDir 'start-lifecity-local.ps1'
Say "Registrando arranque automático al iniciar sesión..." 'Yellow'
$action  = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$startPs`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
try {
  Register-ScheduledTask -TaskName 'LifeCity Local' -Action $action -Trigger $trigger -Settings $settings -RunLevel Limited -Force | Out-Null
  Say "Tarea 'LifeCity Local' registrada." 'Green'
} catch { Say "No pude registrar la tarea (arrancarás manualmente con start-lifecity-local.ps1)." 'Red' }

# --- 5) Arrancar ahora -----------------------------------------------------
Say "Arrancando servicios locales..." 'Yellow'
Start-Process powershell -ArgumentList "-NoProfile","-WindowStyle","Hidden","-ExecutionPolicy","Bypass","-File","`"$startPs`""
Start-Sleep -Seconds 6

# --- Verificación ----------------------------------------------------------
try {
  $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 8
  if ($r.StatusCode -eq 200) { Say "✓ Agente local respondiendo en http://127.0.0.1:8000" 'Green' }
} catch { Say "El agente aún no responde; puede tardar en el primer arranque. Reabre el visor en 1 min." 'Yellow' }

Write-Host ""
Say "LISTO. Vuelve al visor y usa el detector / la nube de puntos." 'Green'
Say "Se ejecuta solo al iniciar Windows. Para quitarlo: Programador de tareas → 'LifeCity Local'." 'Cyan'
Read-Host "Enter para cerrar"

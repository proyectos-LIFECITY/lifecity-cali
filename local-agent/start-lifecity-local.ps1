# =============================================================================
#  LifeCity Local · Lanzador en segundo plano
#  Arranca los dos servicios GPU en loopback (127.0.0.1 = sin firewall):
#    - Detector PointNet++   :8068   (detector\ del paquete)
#    - Backend proxy GPU      :8000   (ai\server.py -> /detect)
#  Se ejecuta al iniciar sesión (tarea 'LifeCity Local') o a mano.
# =============================================================================
$ErrorActionPreference = 'SilentlyContinue'
$InstallDir = Join-Path $env:LOCALAPPDATA 'LifeCity'
$AppDir  = Join-Path $InstallDir 'app'
$Venv    = Join-Path $InstallDir 'venv\Scripts\python.exe'
$Logs    = Join-Path $InstallDir 'logs'
New-Item -ItemType Directory -Force -Path $Logs | Out-Null

function Running($port) {
  try { (Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue).TcpTestSucceeded } catch { $false }
}

# --- Detector PointNet++ (:8068) ------------------------------------------
$detDir = Join-Path $AppDir 'detector'
if ((Test-Path $detDir) -and -not (Running 8068)) {
  # Se espera detector\server.py con app FastAPI (repo 68). Bind a loopback.
  Start-Process -WindowStyle Hidden -FilePath $Venv `
    -ArgumentList "-m","uvicorn","server:app","--host","127.0.0.1","--port","8068" `
    -WorkingDirectory $detDir `
    -RedirectStandardOutput (Join-Path $Logs 'detector.out.log') `
    -RedirectStandardError  (Join-Path $Logs 'detector.err.log')
}

# --- Backend proxy GPU (:8000) --------------------------------------------
$aiDir = Join-Path $AppDir 'ai'
if ((Test-Path $aiDir) -and -not (Running 8000)) {
  $env:DETECTOR_URL = 'http://127.0.0.1:8068'   # el proxy /detect apunta al detector local
  $env:PORT = '8000'
  Start-Process -WindowStyle Hidden -FilePath $Venv `
    -ArgumentList "-m","uvicorn","server:app","--host","127.0.0.1","--port","8000" `
    -WorkingDirectory $aiDir `
    -RedirectStandardOutput (Join-Path $Logs 'ai.out.log') `
    -RedirectStandardError  (Join-Path $Logs 'ai.err.log')
}

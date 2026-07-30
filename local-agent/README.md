# LifeCity Local · agente GPU para el PC

Casi todo LifeCity corre en la **nube** (backend FastAPI en Render). Las funciones
que necesitan **GPU/CUDA** corren en el **PC del usuario** mediante este agente:

- **Detector de elementos** (repo 68 · PointNet++) → `http://127.0.0.1:8068`
- **Backend proxy GPU** (`ai/server.py`, endpoint `/detect`) → `http://127.0.0.1:8000`

El visor (`https://app.lifecity.com.co`) detecta el agente por
`http://127.0.0.1:8000/health` y usa la GPU automáticamente. Si no está,
ofrece descargarlo (ver `descargar.html`).

## Por qué en localhost (y no en la nube)
Los tiers de nube no dan GPU gratis y la red neuronal necesita CUDA. Además así
la nube nunca toca los PCs de los usuarios: cada quien procesa sus nubes de
puntos en su propia máquina, con sus permisos, escuchando solo en `127.0.0.1`
(sin abrir puertos a internet ni reglas de firewall entrantes).

## Archivos
| Archivo | Rol |
|---|---|
| `LifeCity-Local-Setup.bat` | Bootstrap de doble clic (eleva permisos y llama a `install.ps1`). |
| `install.ps1` | Instala Python + venv + PyTorch, descomprime el paquete y registra el arranque al iniciar sesión. |
| `start-lifecity-local.ps1` | Lanzador en segundo plano (detector :8068 + backend :8000, bind a 127.0.0.1). |
| `build-package.ps1` | **Lo corres tú**: empaqueta `ai/` + repo 68 (con modelo) en `LifeCity-Local.zip`. |

## Publicar (una vez, tú)
```powershell
# 1) Genera el paquete distribuible (backend + detector + checkpoints)
powershell -ExecutionPolicy Bypass -File "local-agent\build-package.ps1"
# -> crea local-agent\LifeCity-Local.zip
```
Luego:
- **Opción A (recomendada):** sube `LifeCity-Local.zip` como *Release* en GitHub y
  pon esa URL en `install.ps1` → `$PackageUrl`.
- **Opción B:** deja `LifeCity-Local.zip` junto a `install.ps1`; el instalador lo usa sin descargar.

> Ajusta en `build-package.ps1` la ruta `$DetectorSrc` si el repo 68 está en otra
> carpeta, y confirma que el entrypoint del detector es `detector\server.py` con
> una app FastAPI llamada `app` (si no, edita el módulo uvicorn en
> `start-lifecity-local.ps1`).

## Desinstalar
Programador de tareas de Windows → elimina la tarea **“LifeCity Local”** y borra
`%LOCALAPPDATA%\LifeCity`.

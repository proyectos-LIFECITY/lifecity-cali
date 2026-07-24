# Detector de elementos (red neuronal) — repo 68 · PointNet++

El editor de masas usa **la misma red neuronal entrenada** del repo 68
(`68 RED NEURONAL + NUBE DE PUNTOS`), un **PointNet++** que segmenta la nube en
6 clases: suelo, cielo, muro, columna, viga, otros.

## Cómo se conecta
- El detector real corre en **su propio servidor con GPU** (`http://localhost:8068`).
- `ai/server.py` expone `/detect` y `/detect/status` como **proxy** (`ai/detector.py`):
  convierte la nube (PLY o ASCII XYZ) y la reenvía a `:8068/api/detect`, devolviendo
  clases + cantidades de obra.
- En el editor (Remodelación / nube de puntos) el botón **🧠 Detectar elementos** (PRO)
  envía la nube, muestra la segmentación y **crea objetos BIM existentes** (columnas/vigas)
  desde las cantidades. El enlace **"Abrir detector completo"** lleva a `:8068` para
  segmentar, **corregir** (feedback) y **reentrenar**.

## Arranque
- `Iniciar LifeCity.bat` ya lanza también el detector (si existe el repo 68).
- Manual: `EJECUTAR_LOCAL.bat` del repo 68 (usa `C:\detector-app` con torch+CUDA en tu RTX 3060).

## ¿Se puede entrenar localmente? — SÍ
El modelo se entrena y reentrena **en tu propia máquina/GPU**, de dos formas:

1. **Reentrenamiento en línea (feedback):** en el detector (`:8068`) corriges clases mal
   detectadas → `POST /api/feedback` guarda muestras → `POST /api/retrain` afina el modelo
   con esas correcciones. Es el "motor de entrenamiento" incremental.
2. **Entrenamiento completo (offline):** desde el repo 68:
   ```bat
   cd "G:\Mi unidad\6. REPOS\68 RED NEURONAL + NUBE DE PUNTOS"
   "C:\detector-app\Scripts\python.exe" scripts\build_dataset.py   REM auto-etiqueta nubes -> dataset
   "C:\detector-app\Scripts\python.exe" scripts\train.py --epochs 30
   ```
   Genera `checkpoints/model_best.pt`, que el servidor carga al reiniciar.

> Nota honesta: es un feature **local** (necesita GPU + el servidor del repo 68). No corre
> en GitHub Pages. En el sitio web el botón llama a `http://localhost:8000/detect` — funciona
> con `Iniciar LifeCity.bat` abierto (Chrome permite localhost desde https; Firefox no).

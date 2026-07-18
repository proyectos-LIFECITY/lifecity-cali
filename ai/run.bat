@echo off
title LifeCity - Agente de masas (IA) en http://localhost:8000
cd /d "G:\Mi unidad\6. REPOS\44. Visor Propiedades Cali\ai"
echo ==================================================
echo   LifeCity - Agente de masas (IA)
echo   Endpoint:  http://localhost:8000/suggest
echo   (deja esta ventana abierta mientras lo usas)
echo ==================================================
echo.
echo Para Nemotron REAL, antes de correr:
echo   pip install -r requirements.txt
echo   set NVIDIA_API_KEY=nvapi-xxxx
echo   set NEMOTRON_MODEL=id-exacto-del-modelo
echo.
python -m uvicorn server:app --host 127.0.0.1 --port 8000

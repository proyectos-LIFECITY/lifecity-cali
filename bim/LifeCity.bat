@echo off
title LifeCity BIM 5D - servidor local (no cierres esta ventana)
cd /d "G:\Mi unidad\6. REPOS\50. LifeCity BIM 5D"
echo ============================================
echo   LifeCity BIM 5D - Plataforma Urbana AEC
echo   Servidor local en http://localhost:8123
echo   No cierres esta ventana mientras la uses.
echo ============================================
start "" "http://localhost:8123/cali_aec_viewer.html"
python serve.py

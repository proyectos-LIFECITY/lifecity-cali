@echo off
title LifeCity - servidor local (no cierres esta ventana)
cd /d "G:\Mi unidad\6. REPOS\44. Visor Propiedades Cali"
echo ============================================
echo   LifeCity - Plataforma Urbana AEC (Cali)
echo   Servidor local en http://localhost:8123
echo   No cierres esta ventana mientras la uses.
echo ============================================
start "" "http://localhost:8123/"
python serve.py

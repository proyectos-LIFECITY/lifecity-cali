# LifeCity · Plataforma Urbana AEC (Cali)

Visor 3D de propiedades y catastro de Cali con estudio de masas tipo Revit, fotos geolocalizadas por Telegram y login.

## Páginas
| Archivo | Qué hace |
|---|---|
| `login.html` | Inicio de sesión / registro (LifeCity). Puerta de entrada a la plataforma. |
| `cali_aec_viewer.html` | Visor 3D: catastro IDESC (terrenos + número predial), búsqueda de lotes, basemap OSM, índices POT (ICB/ICA), propiedades guardadas, IFC, nubes de puntos y fotos de Telegram. |
| `masas.html` | Estudio de masas conceptual (tipo Revit): geometría del lote, creación de masas, **nube de puntos (puntos/malla)**, **niveles** y **muros anclados** a niveles. |
| `auth.js` | Guard de sesión (redirige a `login.html` si no hay sesión). |
| `n8n/` | Workflow y guía para las fotos de Telegram (ver `n8n/README.md`). |

## Login (lifecity.com.co)
- **Demo local:** `demo@lifecity.com.co` / `lifecity`. Las cuentas se guardan en el navegador (localStorage) — sirve para demo/piloto en un mismo equipo.
- **Auth real (multi-dispositivo):** en `login.html`, arriba del `<script>`, define:
  ```js
  const SUPABASE_URL = 'https://TU-proyecto.supabase.co';
  const SUPABASE_ANON_KEY = 'TU_ANON_KEY';
  ```
  Con eso `login.html` usa **Supabase Auth** (registro/login/confirmación por correo) sin más cambios. Crea el proyecto gratis en supabase.com → Settings → API para las dos claves.
- El guard (`auth.js`) solo verifica la sesión local que deja el login; funciona igual en ambos modos.

## Desplegar en lifecity.com.co
Son archivos estáticos (HTML/JS). Sube toda la carpeta a tu hosting (o subdominio, p.ej. `app.lifecity.com.co`) y entra por `login.html`. No requiere servidor; solo el navegador consume:
- WFS catastro/POT de la Alcaldía (IDESC), tiles de OpenStreetMap y (opcional) el webhook de n8n para fotos.

## Notas
- Coordenadas en **EPSG:4326 (WGS84)** = coinciden con OpenStreetMap.
- El login local es una **puerta de front-end** (no cifra datos en el servidor). Para producción real usa el modo Supabase.

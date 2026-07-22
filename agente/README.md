# Agente de mapas · Nemotron + LangChain

Agente que **visualiza las construcciones reales de Cali**, lee su **nº de pisos real**,
genera **masas**, las **guarda en el visor principal** y las **publica en OpenStreetMap**.

## Pipeline
1. **Construcciones reales + pisos** → catastro IDESC (`cat_bas_terrenos`, campo `total_pis1`).
   Google Maps no expone el nº de pisos por API; el dato fiable es el catastro. Google Maps/Street View se usan para *visualizar*.
2. **Nemotron (LangChain)** ajusta la altura de piso por uso y el tipo (fallback determinista si el LLM no está).
3. Salida: masas con huella (ring lon/lat) + pisos + `building:levels` para OSM.

## Backend
`ai/server.py` → `POST /agent/maps`  body `{lat, lon, radius?, limit?, gkey?, use_llm?}`.
Motor: `ai/agent_maps.py`. Arranca con `Iniciar LifeCity.bat` (carga tu `keys.bat` para Nemotron).
`gkey` opcional = Google Maps Static/Street View API key (si no, se usan enlaces públicos de Google Maps).

## Uso (página)
`agente/agente.html` (bajo el login): busca una zona de Cali → **Analizar** → lista de construcciones
reales con pisos → **Guardar en el visor principal** y/o **Publicar en OSM** (OAuth out-of-band).

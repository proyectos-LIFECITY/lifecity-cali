# LifeCity BIM 5D · Repo 50

Plataforma unificada que combina tres repos en una sola app web estática (sin build, Three.js por CDN):

| Origen | Qué aporta |
|---|---|
| **Repo 44 · Visor Propiedades Cali** | Motor de búsqueda de terrenos (catastro IDESC WFS, POT ICB/ICA, basemap OSM), login (Supabase/local) y dashboard de estudios. |
| **Repo 49 · Nube de puntos a BIM** | Creación semiautomática de objetos BIM desde nube de puntos (selección de caja → bounding box → elemento del catálogo), estados existente/nuevo, plano por nivel. |
| **Repo 1 · BIM + APU Colombia** | Base de datos APU desde Excel (SheetJS), asignación de APU por elemento y presupuesto consolidado. |

## Páginas

- **`index.html`** → redirige al visor.
- **`login.html`** — autenticación (Supabase o modo local demo `demo@lifecity.com.co` / `lifecity`).
- **`cali_aec_viewer.html`** — visor de terrenos de Cali: búsqueda por predial/dirección, geometría del lote, índices POT, estudios guardados. Desde un predio se abre el editor con **"Estudio de masas"**.
- **`masas.html`** — **Editor BIM 5D** (el corazón de la repo 50):
  - **Masas conceptuales**: extrusión de la huella del lote con retiro, pisos, apilado; verificación contra edificabilidad máxima POT (ICB+ICA).
  - **Nube de puntos**: importa `.ply .pcd .xyz .csv`, vista puntos o malla Delaunay, y **gizmo para mover / rotar / escalar** la nube y posicionarla en el terreno (también sliders manuales y "centrar en lote").
  - **Objetos BIM semiautomáticos (repo 49)**: activa *Selección de caja*, arrastra sobre la nube y el elemento elegido del catálogo (muro, columna, viga, losa, cubierta, puerta, ventana, sanitario…) se crea ajustado al bounding-box de los puntos. Cada objeto se marca **NUEVO** o **EXISTENTE** (filtro global en la barra superior; los existentes se dibujan grises/punteados).
  - **Niveles y planos por nivel**: niveles tipo Revit (datums) y pestaña **Planta** con un plano 2D por cada nivel. Todo lo que se dibuja en planta (muros, columnas, objetos, habitaciones, tuberías) aparece en 3D y viceversa; arrastrar en planta mueve el objeto en 3D.
  - **Panel MEP tipo CYPE**: sistemas hidráulica fría/caliente, sanitaria, ventilación, eléctrica y gas; trazado de tuberías multi-punto (3D o planta) con diámetro, salidas/puntos y tableros. Cada red suma metros lineales al presupuesto.
  - **Presupuesto 5D (repo 1)**: base APU por Excel (`Código | Descripción | Unidad | Valor`) o demo integrada; asignación de APU por elemento (o automática por categoría/sistema); tabla de presupuesto con cantidades del modelo y export CSV.
  - **Esquema de rentas + Facility Management**: dibuja habitaciones/unidades (2 clics), asigna **arrendatario, periodo (inicio→fin), canon mensual y documentos adjuntos (contratos en PDF/imagen, guardados en el estudio)**. El **dashboard de rentas** muestra en tiempo real qué unidades están RENTADAS (hay arrendatario y hoy ∈ periodo) vs LIBRES, % ocupación, ingreso mensual actual y canon potencial. En 3D y planta las unidades se colorean rojo (rentada) / verde (libre).
  - **Exportes**: IFC 2x3 (niveles + muros + objetos), lámina imprimible A3 (ISO/cenital/frontal + cuadros), JSON del proyecto completo.
  - **Guardar proyecto**: persiste en `localStorage` (`cali_massing_studies`) y reaparece en el dashboard del visor.

## Tipos de proyecto (Requerimiento de Adquisición LifeCity)

Al abrir un proyecto nuevo el editor pregunta el perfil (según el requerimiento del inversionista, $1.500M COP, zonas Oeste/Centro de Cali):

- **Perfil 1 · Obra nueva** — lote 12×12+ mixto, esquinero o entre culatas. Activa el panel **"Obra nueva · Normas POT"**:
  - **Frente del lote seleccionable** (clic en un borde); laterales 1/2 y posterior se deducen por paralelismo. Overlay 3D con colores y longitudes.
  - **Masa normativa POT** (Acuerdo 0373/2014, tablas del Playbook LifeCity): aislamiento **posterior** por pisos (1-2→3m, 3-5→4.5m, 6-8→6m, 9-10→7.5m, 11-12→10m, 13+→H/3) y **lateral** por pisos totales (1-3→0m entre medianeros, 4-8→4m, 9-11→7m, 12-13→9m, 14+→H/3). Advertencia educativa del error frecuente #1 (aplicar 0m a los primeros 3 pisos de un edificio alto).
  - **Voladizo desde nivel 2**: Vmáx = 0,25 × antejardín; sin antejardín se rechaza (error frecuente #4).
  - **Patios**: toggles a LATERAL 1 y LATERAL 2 con la dimensión mínima de la norma según pisos (1-3→2m/6m², 4-8→3m/9m², 9-11→3m/16m², 12+→5m/25m²); se restan del área construida y se validan contra los retiros.
  - **Manejo de errores**: retiros que colapsan el lote, frente sin definir, patio que no cabe, voladizo sin antejardín — todo con mensajes claros.
- **Perfil 2 · Remodelación / Multifamiliar (7+ unidades)** — abre directamente la **nube de puntos** (importar → escalar/rotar/mover con gizmo → objetos BIM existentes/nuevos por selección de caja).

**Asistente de fondeo**: wizard con las preguntas del requerimiento (zona, frente/fondo, precio, uso, configuración, estado, unidades, tradición, fotos), semáforo de cumplimiento por criterio y **ficha técnica imprimible** para presentar al inversionista.

## Servidor MCP — diseño de habitaciones con Claude

En `mcp/` hay un servidor MCP (Node stdio, `@modelcontextprotocol/sdk`) que conecta el proyecto con **Claude Desktop / Claude Code** para generar **opciones de diseño por habitación** (ver `mcp/README.md`):

1. `masas.html` → "Exportar para Claude (MCP)" → guardar en `mcp/proyectos/`.
2. Claude usa `listar_habitaciones` / `agregar_opcion_diseno` — con la **regla dura validada por el servidor: toda habitación y la sala deben tener VENTANA** en el perímetro, y los objetos deben caber dentro del espacio.
3. `masas.html` → "Importar diseño de Claude (MCP)" → los objetos aparecen en 3D y planta.

## Ejecutar

```
python serve.py        # http://localhost:8123
```
o doble clic en `LifeCity.bat`. Entrar por `login.html` (o directo al visor).

## Notas técnicas

- Handoff visor→editor por `localStorage.cali_massing_handoff` (anillo lat/lon del predio + ICB/ICA (+ `.study` para restaurar)).
- Coordenadas: EPSG:4326 → ENU local (norte = -Z), origen en el centroide del predio.
- La nube de puntos no se persiste (archivo local); sí se guarda su transformación.
- WFS catastro: `https://ws-idesc.cali.gov.co/geoserver/ows`, capa `catastro:cat_bas_terrenos` (ver memoria del visor).

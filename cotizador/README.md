# Repo 52 · Cotizador TRC y Decenal — Plugin de Claude Code + Web App

Dos herramientas complementarias para cotizar pólizas de **Todo Riesgo Construcción (TRC/adecuaciones)** y **Seguro Decenal de Daños** para los proyectos de **LifeCity BIM 5D (repo 50)**:

1. **Plugin `cotizador-seguros`** de Claude Code (comandos `/cotizar-*`, con navegación asistida en las webs de aseguradoras).
2. **Web app independiente** (`webapp/`) — no requiere Claude: sube el modelo 3D, genera presupuesto y cronograma, controla los entregables del decenal y envía los correos.

## Web app independiente

```
webapp\Cotizador.bat        (o: python webapp/server.py)  →  http://localhost:8124
```

- **Modelo 3D**: sube el **IFC** del proyecto o el **JSON exportado por masas.html (repo 50)**; extrae niveles, sótanos, áreas y cantidades por categoría, con esquema volumétrico 3D. Todo editable a mano.
- **Datos de póliza**: formularios TRC (12 puntos) y Decenal (cuestionario Seguros Mundial); botón "aplicar modelo" autocompleta (campos con borde azul).
- **Presupuesto**: importa base APU (Excel/CSV `Código|Descripción|Unidad|Valor` — demo en `webapp/ejemplos/apus_demo.csv`), genera ítems desde el modelo, tabla de **13 costos indirectos del decenal**, export CSV/Excel.
- **Cronograma tipo Project**: Gantt editable generado desde el modelo (estructura por nivel), export CSV para MS Project. Alimenta vigencia TRC y plazo decenal.
- **Documentos**: checklist de los 14 entregables del decenal con % de avance y validación de indirectos.
- **Aseguradoras**: tabla de 12 aseguradoras colombianas con link, resumen del riesgo al portapapeles y tracking de estado/prima.
- **Correo**: plantillas de "avance de entregables" y "solicitud de cotización" (la decenal solo se habilita al 100% de documentos). Envío por `mailto:` o **SMTP real con adjuntos** (crear `webapp/config.email.json` desde `config.email.example.json` con App Password de Gmail).
- **Proyectos**: se guardan en el navegador y en `webapp/proyectos/*.json` — los comandos del plugin los leen como fuente principal.

## Plugin de Claude Code

## Instalación (queda disponible en TODOS los proyectos)

```bash
claude plugin marketplace add "G:\Mi unidad\6. REPOS\52. COTIZADOR TO RIESGO Y DECENAL"
claude plugin install cotizador-seguros@lifecity-seguros
```

Para actualizar después de editar el plugin:

```bash
claude plugin marketplace update lifecity-seguros
claude plugin update cotizador-seguros
```

## Comandos

| Comando | Qué hace |
|---|---|
| `/cotizar-todo-riesgo [proyecto]` | Recopila los 12 datos que piden las aseguradoras para TRC/adecuaciones (tomador, NIT, ingresos, nómina, actividad, cronograma, presupuesto, vigencia, siniestralidad, dirección, límite), autocompletando desde el proyecto LifeCity BIM 5D, y genera la solicitud de cotización. |
| `/cotizar-decenal [carpeta docs]` | Verifica el checklist de 14 documentos del decenal, valida el desglose de costos indirectos (13 capítulos) y diligencia el cuestionario de Seguros Mundial por secciones. Genera el estado de documentos, los datos del cuestionario y el borrador de correo a ingenieria@segurosmundial.com.co. |
| `/cotizacion-preliminar-web [trc\|decenal]` | Entra a las páginas de las aseguradoras colombianas (Sura, Bolívar, AXA Colpatria, Mapfre, Allianz, HDI, Chubb, Seguros Mundial, SBS, Zurich…) con el navegador (Chrome MCP), diligencia formularios de cotización/contacto con los datos recopilados (siempre pide confirmación antes de enviar) y entrega una tabla comparativa. |

## Integración con el repo 50 (LifeCity BIM 5D)

Los comandos autocompletan datos del proyecto desde:

1. El servidor MCP **`lifecity-bim`** (`listar_proyectos`, `leer_proyecto`), o
2. Los JSON exportados en `50. LifeCity BIM 5D/mcp/proyectos/*.json` (dirección del predio, niveles/plantas, áreas de habitaciones, presupuesto 5D por APUs, notas de diseño).

## Estructura

```
.claude-plugin/marketplace.json        ← marketplace "lifecity-seguros"
cotizador-seguros/
  .claude-plugin/plugin.json
  commands/
    cotizar-todo-riesgo.md
    cotizar-decenal.md
    cotizacion-preliminar-web.md
  skills/cotizador-seguros/
    SKILL.md                           ← se activa al hablar de cotizar seguros de obra
    references/cuestionario-decenal.md ← cuestionario Seguros Mundial completo + checklists
    references/aseguradoras.md         ← aseguradoras colombianas, URLs y canales
```

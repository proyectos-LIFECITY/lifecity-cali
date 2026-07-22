#!/usr/bin/env node
/* ============================================================
   LifeCity BIM · Servidor MCP (stdio)
   ------------------------------------------------------------
   Conecta Claude (Desktop / Code) con los proyectos del editor
   BIM 5D para GENERAR OPCIONES DE DISEÑO por habitación.

   Flujo:
   1. En masas.html → "Exportar para Claude (MCP)" y guarda el
      JSON en  mcp/proyectos/.
   2. Claude usa estas tools para leer las habitaciones y
      escribir opciones de diseño (objetos BIM) en el archivo.
   3. En masas.html → "Importar diseño de Claude (MCP)".

   REGLA DURA DE DISEÑO (se valida aquí y en el editor):
   → Toda habitación (uso="habitacion") y la sala (uso="sala")
     deben tener al menos UNA VENTANA (typeId "ventana"),
     colocada en el perímetro del espacio (fachada o patio).
   ============================================================ */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJ_DIR = path.join(__dirname, "proyectos");
if (!fs.existsSync(PROJ_DIR)) fs.mkdirSync(PROJ_DIR, { recursive: true });

/* Catálogo (mismos typeId que el editor masas.html) */
const CATALOG = {
  "muro-mamposteria": { label: "Muro mampostería", dims: { w: 3, h: 2.4, d: 0.15 } },
  "muro-concreto":    { label: "Muro concreto",    dims: { w: 3, h: 2.4, d: 0.2 } },
  "muro-drywall":     { label: "Muro drywall",     dims: { w: 3, h: 2.4, d: 0.1 } },
  "columna-concreto": { label: "Columna concreto", dims: { w: 0.3, h: 3, d: 0.3 } },
  "viga-concreto":    { label: "Viga concreto",    dims: { w: 3, h: 0.4, d: 0.3 } },
  "losa-entrepiso":   { label: "Losa entrepiso",   dims: { w: 4, h: 0.15, d: 4 } },
  "puerta":           { label: "Puerta",           dims: { w: 0.9, h: 2.1, d: 0.1 } },
  "ventana":          { label: "Ventana",          dims: { w: 1.2, h: 1.2, d: 0.1 } },
  "sanitario":        { label: "Sanitario",        dims: { w: 0.4, h: 0.75, d: 0.65 } },
  "lavamanos":        { label: "Lavamanos",        dims: { w: 0.55, h: 0.85, d: 0.5 } },
  "lavaplatos":       { label: "Lavaplatos mesón", dims: { w: 0.8, h: 0.9, d: 0.5 } },
};

const filePath = (archivo) => {
  const safe = path.basename(archivo);              // sin traversal
  const p = path.join(PROJ_DIR, safe.endsWith(".json") ? safe : safe + ".json");
  return p;
};
const readProject = (archivo) => JSON.parse(fs.readFileSync(filePath(archivo), "utf8"));
const writeProject = (archivo, data) => fs.writeFileSync(filePath(archivo), JSON.stringify(data, null, 2), "utf8");
const text = (s) => ({ content: [{ type: "text", text: typeof s === "string" ? s : JSON.stringify(s, null, 2) }] });
const err = (s) => ({ content: [{ type: "text", text: "ERROR: " + s }], isError: true });

const server = new McpServer({
  name: "lifecity-bim",
  version: "1.0.0",
});

server.tool(
  "listar_proyectos",
  "Lista los proyectos LifeCity disponibles en mcp/proyectos/ (exportados desde el editor BIM 5D).",
  {},
  async () => {
    const files = fs.readdirSync(PROJ_DIR).filter((f) => f.endsWith(".json"));
    if (!files.length) return text("No hay proyectos. Exporta uno desde masas.html → 'Exportar para Claude (MCP)' y guárdalo en mcp/proyectos/.");
    return text(files.map((f) => {
      try { const p = JSON.parse(fs.readFileSync(path.join(PROJ_DIR, f), "utf8"));
        return `• ${f} — ${p.predio?.direpred || "sin dirección"} · ${p.projectType === "obra" ? "Obra nueva" : p.projectType === "remo" ? "Remodelación" : "sin tipo"} · ${p.rooms?.length || 0} habitación(es) · ${p.levels?.length || 0} nivel(es)`; }
      catch { return `• ${f} — (ilegible)`; }
    }).join("\n"));
  }
);

server.tool(
  "leer_proyecto",
  "Devuelve el proyecto completo (niveles, masas, objetos BIM, MEP, habitaciones, presupuesto). Úsalo para entender el contexto antes de diseñar.",
  { archivo: z.string().describe("Nombre del archivo en mcp/proyectos/, p.ej. '760010100..._lifecity.json'") },
  async ({ archivo }) => {
    try { return text(readProject(archivo)); }
    catch (e) { return err("No pude leer '" + archivo + "': " + e.message); }
  }
);

server.tool(
  "listar_habitaciones",
  "Lista las habitaciones/espacios del proyecto con su geometría (centro x,z + ancho w × fondo d en metros), nivel y uso. El diseño de cada espacio debe caber dentro de su rectángulo.",
  { archivo: z.string() },
  async ({ archivo }) => {
    try {
      const p = readProject(archivo);
      if (!p.rooms?.length) return text("El proyecto no tiene habitaciones. Pide al usuario dibujarlas en el editor (Rentas · Habitaciones).");
      const lv = Object.fromEntries((p.levels || []).map((l) => [l.id, l.name]));
      return text(p.rooms.map((r) =>
        `roomId=${r.id} · "${r.name}" · uso=${r.uso || "habitacion"} · nivel=${lv[r.level] || r.level} · centro=(${r.x.toFixed(2)}, ${r.z.toFixed(2)}) · ${r.w.toFixed(2)}×${r.d.toFixed(2)} m` +
        ((r.uso === "habitacion" || r.uso === "sala") ? "  ⚠ requiere VENTANA" : "")
      ).join("\n") + "\n\nCatálogo typeId disponibles: " + Object.entries(CATALOG).map(([k, v]) => `${k} (${v.dims.w}×${v.dims.h}×${v.dims.d}m)`).join(", "));
    } catch (e) { return err(e.message); }
  }
);

const ObjetoSchema = z.object({
  typeId: z.enum(Object.keys(CATALOG)).describe("Tipo del catálogo LifeCity"),
  x: z.number().describe("Centro X absoluto (m) — dentro del rectángulo de la habitación"),
  z: z.number().describe("Centro Z absoluto (m)"),
  w: z.number().optional().describe("Ancho (m); por defecto el del catálogo"),
  h: z.number().optional().describe("Alto (m)"),
  d: z.number().optional().describe("Fondo (m)"),
  rotY: z.number().optional().describe("Rotación en radianes sobre Y"),
});

server.tool(
  "agregar_opcion_diseno",
  "Escribe UNA opción de diseño para una habitación específica: lista de objetos BIM (cama=usa muro-drywall bajo o losa como proxy si no hay tipo, closet=muro-drywall, ventana, puerta, sanitario...). REGLA DURA: si la habitación es uso=habitacion o uso=sala, la opción DEBE incluir al menos una 'ventana' en el perímetro (|x-cx|≈w/2 o |z-cz|≈d/2). Los objetos quedan marcados fromClaude para importarlos en el editor.",
  {
    archivo: z.string(),
    roomId: z.number().describe("roomId de listar_habitaciones"),
    opcion: z.string().describe("Nombre corto de la opción, p.ej. 'Opción A — cama frente a ventana'"),
    descripcion: z.string().optional().describe("Explicación breve de la distribución para el usuario"),
    objetos: z.array(ObjetoSchema).min(1),
  },
  async ({ archivo, roomId, opcion, descripcion, objetos }) => {
    try {
      const p = readProject(archivo);
      const room = (p.rooms || []).find((r) => r.id === roomId);
      if (!room) return err(`roomId ${roomId} no existe. Usa listar_habitaciones.`);
      // 1) dentro de la habitación (tolerancia 0.3 m para ventanas en el borde)
      const tol = 0.3;
      for (const o of objetos) {
        if (Math.abs(o.x - room.x) > room.w / 2 + tol || Math.abs(o.z - room.z) > room.d / 2 + tol)
          return err(`El objeto ${o.typeId} en (${o.x},${o.z}) queda FUERA de "${room.name}" (centro ${room.x},${room.z} · ${room.w}×${room.d} m). Reposiciónalo.`);
      }
      // 2) regla de ventanas
      const needsWindow = (room.uso || "habitacion") === "habitacion" || room.uso === "sala";
      const hasWindow = objetos.some((o) => o.typeId === "ventana") ||
        (p.bim || []).some((b) => b.roomId === roomId && b.typeId === "ventana");
      if (needsWindow && !hasWindow)
        return err(`"${room.name}" es ${room.uso}: la opción DEBE incluir una 'ventana' en el perímetro del espacio (regla de iluminación/ventilación).`);
      // 3) escribir
      p.bim = p.bim || [];
      let n = 0;
      for (const o of objetos) {
        const cat = CATALOG[o.typeId];
        p.bim.push({
          id: `mcp-${Date.now()}-${n++}`, typeId: o.typeId, existing: false,
          level: room.level, x: o.x, z: o.z,
          w: o.w ?? cat.dims.w, h: o.h ?? cat.dims.h, d: o.d ?? cat.dims.d,
          rotY: o.rotY ?? 0, apu: null,
          fromClaude: true, optionName: opcion, roomId,
        });
      }
      p.designNotes = p.designNotes || [];
      p.designNotes.push({ roomId, opcion, descripcion: descripcion || "", fecha: new Date().toISOString() });
      writeProject(archivo, p);
      return text(`✓ Opción "${opcion}" guardada en "${room.name}": ${objetos.length} objeto(s), regla de ventanas OK. El usuario la importa con "Importar diseño de Claude (MCP)" en masas.html.`);
    } catch (e) { return err(e.message); }
  }
);

server.tool(
  "validar_proyecto",
  "Valida el proyecto contra la regla de ventanas (toda habitación y sala con ventana) y reporta pendientes de diseño.",
  { archivo: z.string() },
  async ({ archivo }) => {
    try {
      const p = readProject(archivo);
      const faltan = (p.rooms || []).filter((r) =>
        ((r.uso || "habitacion") === "habitacion" || r.uso === "sala") &&
        !(p.bim || []).some((b) => b.roomId === r.id && b.typeId === "ventana"));
      const lines = [
        `Proyecto: ${p.predio?.direpred || archivo} · tipo ${p.projectType || "—"}`,
        `Habitaciones: ${(p.rooms || []).length} · Objetos BIM: ${(p.bim || []).length} (${(p.bim || []).filter((b) => b.fromClaude).length} de Claude)`,
        faltan.length ? `✕ SIN VENTANA (pendiente diseño): ${faltan.map((r) => `"${r.name}" (roomId=${r.id})`).join(", ")}` : "✓ Regla de ventanas: todas las habitaciones y salas tienen ventana o aún no tienen diseño asignado.",
      ];
      return text(lines.join("\n"));
    } catch (e) { return err(e.message); }
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("LifeCity BIM MCP listo (stdio) · proyectos en " + PROJ_DIR);

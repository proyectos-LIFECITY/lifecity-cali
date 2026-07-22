/**
 * API de APUs (Gobernación) sobre Cloudflare D1 — para la webapp del
 * Cotizador TRC y Decenal (repo 52).
 *
 * GET  /api/apus?q=texto        -> lista actividades (id, nombre, unidad, precio_total), filtro por nombre
 * GET  /api/apu/:id             -> actividad + insumos (con precios de proveedores si existen)
 * POST /api/apus                -> crea un NUEVO APU {nombre, unidad, insumos:[{codigo,nombre,tipo,unidad,rendimiento,desperdicio,precio_unitario}]}
 * GET  /api/materiales          -> catálogo de insumos únicos con precios de proveedores
 * POST /api/precios             -> [{insumo_codigo, proveedor, precio, unidad?}] upsert precios de proveedores
 */
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};
const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8", ...CORS } });

export default {
  async fetch(req, env) {
    if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
    const url = new URL(req.url);
    const p = url.pathname;
    try {
      if (p === "/api/apus" && req.method === "GET") {
        const q = (url.searchParams.get("q") || "").trim();
        const lim = Math.min(parseInt(url.searchParams.get("limit") || "60"), 500);
        const rs = q
          ? await env.DB.prepare("SELECT id,nombre,unidad,precio_total FROM actividades WHERE nombre LIKE ? ORDER BY nombre LIMIT ?").bind(`%${q}%`, lim).all()
          : await env.DB.prepare("SELECT id,nombre,unidad,precio_total FROM actividades ORDER BY nombre LIMIT ?").bind(lim).all();
        return json(rs.results);
      }

      if (p === "/api/apus" && req.method === "POST") {
        const b = await req.json();
        if (!b || !b.nombre || !Array.isArray(b.insumos) || !b.insumos.length)
          return json({ error: "se espera {nombre, unidad, insumos[]}" }, 400);
        const insumos = b.insumos.filter(x => x.nombre && isFinite(parseFloat(x.precio_unitario)) && parseFloat(x.rendimiento) > 0);
        if (!insumos.length) return json({ error: "sin insumos válidos (nombre, rendimiento>0, precio)" }, 400);
        const parcial = x => Math.round(parseFloat(x.rendimiento) * (1 + (parseFloat(x.desperdicio) || 0)) * parseFloat(x.precio_unitario));
        const total = insumos.reduce((s, x) => s + parcial(x), 0);
        const r = await env.DB.prepare("INSERT INTO actividades(nombre,unidad,precio_total) VALUES(?,?,?)")
          .bind(String(b.nombre).slice(0, 200), String(b.unidad || "").slice(0, 12), total).run();
        const id = r.meta.last_row_id;
        const stmt = env.DB.prepare("INSERT INTO insumos(actividad_id,codigo,nombre,tipo,unidad,rendimiento,desperdicio,precio_unitario,precio_parcial) VALUES(?,?,?,?,?,?,?,?,?)");
        await env.DB.batch(insumos.map(x => stmt.bind(
          id, String(x.codigo || "").slice(0, 24), String(x.nombre).slice(0, 160),
          ["MO", "MQ", "MAT"].includes(x.tipo) ? x.tipo : "MAT", String(x.unidad || "").slice(0, 12),
          parseFloat(x.rendimiento), parseFloat(x.desperdicio) || 0, parseFloat(x.precio_unitario), parcial(x))));
        return json({ ok: true, id, nombre: b.nombre, unidad: b.unidad || "", precio_total: total });
      }

      const mApu = p.match(/^\/api\/apu\/(\d+)$/);
      if (mApu && req.method === "GET") {
        const id = parseInt(mApu[1]);
        const act = await env.DB.prepare("SELECT id,nombre,unidad,precio_total FROM actividades WHERE id=?").bind(id).first();
        if (!act) return json({ error: "no existe" }, 404);
        const ins = await env.DB.prepare(
          "SELECT i.codigo,i.nombre,i.tipo,i.unidad,i.rendimiento,i.desperdicio,i.precio_unitario,i.precio_parcial FROM insumos i WHERE i.actividad_id=?"
        ).bind(id).all();
        const precios = await env.DB.prepare(
          "SELECT p.insumo_codigo,p.proveedor,p.precio,p.fecha FROM precios_proveedores p JOIN insumos i ON i.codigo=p.insumo_codigo WHERE i.actividad_id=? GROUP BY p.insumo_codigo,p.proveedor"
        ).bind(id).all();
        return json({ ...act, insumos: ins.results, precios_proveedores: precios.results });
      }

      if (p === "/api/materiales" && req.method === "GET") {
        const mats = await env.DB.prepare(
          "SELECT codigo, MIN(nombre) nombre, tipo, MIN(unidad) unidad, AVG(precio_unitario) precio_unitario FROM insumos GROUP BY codigo, tipo ORDER BY nombre"
        ).all();
        const precios = await env.DB.prepare("SELECT insumo_codigo,proveedor,precio,fecha FROM precios_proveedores").all();
        return json({ materiales: mats.results, precios_proveedores: precios.results });
      }

      if (p === "/api/precios" && req.method === "POST") {
        const body = await req.json();
        if (!Array.isArray(body) || !body.length) return json({ error: "se espera un arreglo de precios" }, 400);
        const hoy = new Date().toISOString().slice(0, 10);
        const stmt = env.DB.prepare(
          "INSERT INTO precios_proveedores(insumo_codigo,proveedor,precio,unidad,fecha) VALUES(?,?,?,?,?) " +
          "ON CONFLICT(insumo_codigo,proveedor) DO UPDATE SET precio=excluded.precio, unidad=excluded.unidad, fecha=excluded.fecha"
        );
        const batch = body
          .filter(x => x.insumo_codigo && x.proveedor && isFinite(parseFloat(x.precio)))
          .map(x => stmt.bind(String(x.insumo_codigo), String(x.proveedor).slice(0, 60), parseFloat(x.precio), x.unidad ? String(x.unidad) : null, hoy));
        if (!batch.length) return json({ error: "sin filas válidas" }, 400);
        await env.DB.batch(batch);
        return json({ ok: true, actualizados: batch.length, fecha: hoy });
      }

      return json({ error: "ruta no encontrada", rutas: ["/api/apus?q=", "/api/apu/:id", "/api/materiales", "POST /api/precios"] }, 404);
    } catch (e) {
      return json({ error: String(e) }, 500);
    }
  },
};

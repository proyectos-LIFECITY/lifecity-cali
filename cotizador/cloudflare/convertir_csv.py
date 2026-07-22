#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte APUS_Extraidos_v2.csv (APU Gobernación, formato colombiano:
puntos = miles, comas = decimales) en:
  - seed.sql       -> para Cloudflare D1 (tablas actividades / insumos / precios_proveedores)
  - apus_local.json-> respaldo local para la webapp (funciona sin Cloudflare)
"""
import csv, json, os, re, sys

CSV = r"G:\Mi unidad\0. Documentos\01_PROYECTOS_CLIENTES\APU Gobernacion\APUS_Extraidos_v2.csv"
OUT = os.path.dirname(os.path.abspath(__file__))

def num_co(s):
    """'106.594' -> 106594 ; '6,000' -> 6.0 ; '0,00' -> 0.0"""
    s = (s or "").strip().replace(" ", "")
    if not s:
        return 0.0
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0

def tipo_insumo(codigo):
    c = codigo.upper()
    if c.startswith("MO"):
        return "MO"       # mano de obra
    if c.startswith("MQ"):
        return "MQ"       # maquinaria / equipo / herramienta
    return "MAT"          # material

def esc(s):
    return s.replace("'", "''")

acts = {}
with open(CSV, encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        act = (row["Actividad"] or "").strip()
        if not act:
            continue
        a = acts.setdefault(act, {
            "codigo": act.split("-", 3)[:3] and "-".join(act.split("-")[:3]) or act,
            "nombre": act,
            "unidad": (row["Unidad_Actividad"] or "").strip(),
            "precio_total": num_co(row["Precio_Total_Actividad"]),
            "insumos": []})
        ins_full = (row["Insumo"] or "").strip()
        m = re.match(r"^([A-Z0-9]+)-(.+)$", ins_full)
        cod_i, nom_i = (m.group(1), m.group(2).strip()) if m else (ins_full[:12], ins_full)
        a["insumos"].append({
            "codigo": cod_i,
            "nombre": nom_i,
            "tipo": tipo_insumo(cod_i),
            "unidad": (row["Unidad_Insumo"] or "").strip(),
            "rendimiento": num_co(row["Cantidad_Rendimiento"]),
            "desperdicio": num_co(row["Desperdicio"]),
            "precio_unitario": num_co(row["Precio_Unitario"]),
            "precio_parcial": num_co(row["Precio_Parcial"])})

acts = list(acts.values())
print(f"Actividades: {len(acts)} · Filas insumo: {sum(len(a['insumos']) for a in acts)}")

# ---------- JSON local ----------
with open(os.path.join(OUT, "..", "webapp", "ejemplos", "apus_gobernacion.json"), "w", encoding="utf-8") as f:
    json.dump(acts, f, ensure_ascii=False)

# ---------- seed.sql ----------
lines = [
    "DROP TABLE IF EXISTS precios_proveedores;",
    "DROP TABLE IF EXISTS insumos;",
    "DROP TABLE IF EXISTS actividades;",
    "CREATE TABLE actividades(id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, unidad TEXT, precio_total REAL);",
    "CREATE TABLE insumos(id INTEGER PRIMARY KEY AUTOINCREMENT, actividad_id INTEGER NOT NULL REFERENCES actividades(id), codigo TEXT, nombre TEXT, tipo TEXT, unidad TEXT, rendimiento REAL, desperdicio REAL, precio_unitario REAL, precio_parcial REAL);",
    "CREATE TABLE precios_proveedores(insumo_codigo TEXT NOT NULL, proveedor TEXT NOT NULL, precio REAL NOT NULL, unidad TEXT, fecha TEXT, PRIMARY KEY(insumo_codigo, proveedor));",
    "CREATE INDEX idx_insumos_act ON insumos(actividad_id);",
    "CREATE INDEX idx_insumos_cod ON insumos(codigo);",
]
for i, a in enumerate(acts, 1):
    lines.append(f"INSERT INTO actividades VALUES({i},'{esc(a['nombre'])}','{esc(a['unidad'])}',{a['precio_total']});")
vals = []
for i, a in enumerate(acts, 1):
    for ins in a["insumos"]:
        vals.append(f"({i},'{esc(ins['codigo'])}','{esc(ins['nombre'])}','{ins['tipo']}','{esc(ins['unidad'])}',{ins['rendimiento']},{ins['desperdicio']},{ins['precio_unitario']},{ins['precio_parcial']})")
# lotes de 500 para no exceder límites de D1
for j in range(0, len(vals), 500):
    lines.append("INSERT INTO insumos(actividad_id,codigo,nombre,tipo,unidad,rendimiento,desperdicio,precio_unitario,precio_parcial) VALUES\n" + ",\n".join(vals[j:j+500]) + ";")

with open(os.path.join(OUT, "seed.sql"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Escritos: cloudflare/seed.sql y webapp/ejemplos/apus_gobernacion.json")

"""
LifeCity · Agente de consultas en lenguaje natural sobre la base de datos (catastro IDESC)
=========================================================================================
Traduce preguntas ("muéstrame los terrenos con índice de construcción 3", "predios de
5 pisos en San Fernando", "lotes de más de 300 m2") a una consulta SEGURA contra el WFS
de Cali y devuelve los resultados. Nemotron (LangChain) hace la traducción; si no está,
un parser determinista cubre los casos comunes.
"""
from __future__ import annotations
import os, json, re, math, urllib.request, urllib.parse

WFS = "https://ws-idesc.cali.gov.co/geoserver/ows"
R = 6378137.0

LAYERS = {
    # índice de construcción básico/adicional (zonas POT) — valores string con coma ("3", "3,5")
    "edificabilidad": {"name": "pot_2014:nur_edificabilidad_icb",
                       "props": "icb,ica,the_geom", "fields": {"icb": "str", "ica": "str"}},
    # terrenos/predios — pisos reales, área, barrio, comuna, dirección, uso
    "terrenos": {"name": "catastro:cat_bas_terrenos",
                 "props": "npn,direpred,nom_barrio,comuna,total_pis1,uso_princi,shape_area,the_geom",
                 "fields": {"total_pis1": "int", "shape_area": "num", "nom_barrio": "str",
                            "comuna": "str", "direpred": "str", "uso_princi": "str"}},
    "tratamientos": {"name": "pot_2014:nur_tratamientos_urbanisticos",
                     "props": "codigo,tratamient,the_geom", "fields": {"tratamient": "str", "codigo": "str"}},
}

SCHEMA_TXT = (
    "Capas y campos:\n"
    "- edificabilidad: icb (índice construcción BÁSICO), ica (adicional). Valores exactos como '2', '3', '3,5'.\n"
    "- terrenos: total_pis1 (nº de pisos, entero), shape_area (área m2), nom_barrio, comuna, direpred (dirección), uso_princi (RESIDENCIAL/COMERCIAL/...).\n"
    "- tratamientos: tratamient (CONSERVACION/RENOVACION URBANA...), codigo.\n"
    "Operadores: =, >, <, >=, <=, like."
)


def _esc(v):
    return str(v).replace("'", "''")


def _num_comma(v):
    s = str(v).strip().replace(".", ",")
    return s[:-2] if s.endswith(",0") else s


def nl_to_spec(pregunta: str) -> dict:
    """Devuelve {'layer','filters':[{field,op,value}],'limit'} y de dónde salió."""
    # 1) Nemotron
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        import massing_agent
        system = ("Traduces preguntas sobre catastro de Cali a una consulta JSON. " + SCHEMA_TXT +
                  " Responde SOLO JSON: {\"layer\":str,\"filters\":[{\"field\":str,\"op\":str,\"value\":str|num}],\"limit\":int}."
                  " Para índice de construcción usa layer 'edificabilidad', campo 'icb', op '=', value como texto ('3').")
        llm = massing_agent._get_llm()
        resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=pregunta)])
        spec = massing_agent._extract_json(getattr(resp, "content", str(resp)))
        spec["_agente"] = "Nemotron"
        if spec.get("layer") in LAYERS and spec.get("filters"):
            return spec
    except Exception as e:
        pass
    # 2) Fallback determinista
    q = pregunta.lower()
    filt = []
    layer = None
    m = re.search(r"(?:indice|índice|icb|construc\w*)\D{0,12}(\d+(?:[.,]\d+)?)", q)
    if m and ("indic" in q or "icb" in q or "construc" in q):
        layer = "edificabilidad"; filt.append({"field": "icb", "op": "=", "value": _num_comma(m.group(1))})
    ma = re.search(r"(?:ica|adicional)\D{0,10}(\d+(?:[.,]\d+)?)", q)
    if ma:
        layer = "edificabilidad"; filt.append({"field": "ica", "op": "=", "value": _num_comma(ma.group(1))})
    mp = re.search(r"(\d+)\s*pisos?", q)
    if mp:
        layer = "terrenos"; op = ">=" if ("más" in q or "mas" in q or "mayor" in q) else "="
        filt.append({"field": "total_pis1", "op": op, "value": int(mp.group(1))})
    marea = re.search(r"(\d{2,6})\s*(?:m2|m²|metros)", q)
    if marea:
        layer = "terrenos"; op = ">" if ("más" in q or "mas" in q or "mayor" in q) else ("<" if ("menos" in q or "menor" in q) else "=")
        filt.append({"field": "shape_area", "op": op, "value": int(marea.group(1))})
    mb = re.search(r"barrio\s+([a-záéíóúñ0-9 ]{3,30})", q)
    if mb:
        layer = "terrenos"; filt.append({"field": "nom_barrio", "op": "like", "value": mb.group(1).strip().title()})
    mc = re.search(r"comuna\s+(\d{1,2})", q)
    if mc:
        layer = "terrenos"; filt.append({"field": "comuna", "op": "=", "value": mc.group(1).zfill(2)})
    for uso in ["residencial", "comercial", "industrial", "institucional"]:
        if uso in q:
            layer = "terrenos"; filt.append({"field": "uso_princi", "op": "like", "value": uso.upper()})
    return {"layer": layer, "filters": filt, "limit": 150, "_agente": "reglas"}


def _cql(spec, bbox):
    layer = LAYERS[spec["layer"]]
    parts = []
    for f in spec.get("filters", []):
        field, op, val = f.get("field"), (f.get("op") or "=").lower(), f.get("value")
        if field not in layer["fields"]:
            continue
        typ = layer["fields"][field]
        if typ in ("int", "num"):
            parts.append(f"{field}{op if op in ('>','<','>=','<=','=') else '='}{float(val)}")
        else:
            if op == "like":
                parts.append(f"{field} LIKE '{_esc(val)}%'")
            else:
                parts.append(f"{field}='{_esc(val)}'")
    if bbox:
        w, s, e, n = bbox
        parts.append(f"BBOX(the_geom,{w},{s},{e},{n},'EPSG:4326')")
    return " AND ".join(parts) if parts else "INCLUDE"


def run_query(spec, bbox=None):
    layer = LAYERS[spec["layer"]]
    cql = _cql(spec, bbox)
    q = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": layer["name"],
         "outputFormat": "application/json", "srsName": "EPSG:4326", "propertyName": layer["props"],
         "count": int(spec.get("limit") or 150), "CQL_FILTER": cql}
    url = WFS + "?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=50) as r:
        data = json.loads(r.read().decode())
    results = []
    for feat in data.get("features", []):
        p = feat.get("properties", {}) or {}
        g = feat.get("geometry")
        ring = None
        cx = cy = None
        if g:
            ring = g["coordinates"][0][0] if g.get("type") == "MultiPolygon" else g["coordinates"][0]
            cx = sum(pt[0] for pt in ring) / len(ring); cy = sum(pt[1] for pt in ring) / len(ring)
        results.append({**{k: p.get(k) for k in p if k != "the_geom"},
                        "centroid": {"lat": cy, "lon": cx} if cx else None, "ring": ring})
    return {"cql": cql, "n": len(results), "results": results}


def ask(pregunta: str, bbox=None) -> dict:
    spec = nl_to_spec(pregunta)
    if not spec.get("layer") or not spec.get("filters"):
        return {"ok": False, "agente": spec.get("_agente", "?"),
                "mensaje": "No entendí la consulta. Prueba: 'terrenos con índice de construcción 3', "
                           "'predios de 5 pisos en comuna 4', 'lotes de más de 300 m2 en barrio Granada'.",
                "results": []}
    # terrenos: si no hay bbox, limita a una zona para no escanear 736k predios
    if spec["layer"] == "terrenos" and not bbox:
        bbox = (-76.545, 3.435, -76.520, 3.460)  # centro de Cali por defecto
    out = run_query(spec, bbox)
    out.update({"ok": True, "agente": spec.get("_agente", "?"), "layer": spec["layer"], "spec": spec})
    return out

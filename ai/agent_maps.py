"""
LifeCity · Agente de mapas (LangChain + Nemotron)
=================================================
Pipeline:
  1) Lee construcciones REALES de Cali del catastro IDESC (huella + nº de pisos reales
     en el campo `total_pis1`). Google Maps/Street View se usan para VISUALIZAR
     (Google no expone el nº de pisos por API; el dato fiable es el catastro).
  2) Nemotron (vía LangChain) razona la volumetría (altura de piso por uso, notas).
     Si el LLM no está disponible, usa reglas deterministas.
  3) Devuelve masas listas para: crear en el editor, publicar en OSM (building:levels)
     y guardar en el visor principal.
"""
from __future__ import annotations
import os, json, math, urllib.request, urllib.parse

WFS = "https://ws-idesc.cali.gov.co/geoserver/ows"
LAYER = "catastro:cat_bas_terrenos"
PROPS = "npn,direpred,nom_barrio,comuna,total_pis1,pisopred,uso_princi,shape_area,the_geom"
R = 6378137.0

# altura de piso por uso (m) — punto de partida; Nemotron puede ajustarlo
FLOOR_H_BY_USE = {"residencial": 2.7, "comercial": 3.6, "mixto": 3.0, "industrial": 5.0, "institucional": 3.6}


def _wfs(cql: str, count: int = 30) -> dict:
    q = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": LAYER,
         "outputFormat": "application/json", "srsName": "EPSG:4326", "propertyName": PROPS,
         "count": count, "CQL_FILTER": cql}
    url = WFS + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_buildings(lat: float, lon: float, radius: float = 120, limit: int = 20) -> list:
    dlat = radius / R * 180 / math.pi
    dlon = radius / (R * math.cos(math.radians(lat))) * 180 / math.pi
    cql = f"BBOX(the_geom,{lon-dlon},{lat-dlat},{lon+dlon},{lat+dlat},'EPSG:4326')"
    data = _wfs(cql, count=max(limit * 6, 60))  # pedimos de más porque hay propiedad horizontal
    by_footprint = {}
    for f in data.get("features", []):
        p = f.get("properties", {}) or {}
        g = f.get("geometry")
        if not g:
            continue
        ring = g["coordinates"][0][0] if g.get("type") == "MultiPolygon" else g["coordinates"][0]
        # firma de la huella (edificio) para agrupar unidades de propiedad horizontal
        sig = (round(ring[0][0], 6), round(ring[0][1], 6), round(float(p.get("shape_area") or 0), 1), len(ring))
        try:
            floors = int(p.get("total_pis1")) if p.get("total_pis1") not in (None, "") else None
        except Exception:
            floors = None
        if sig in by_footprint:
            b = by_footprint[sig]
            b["unidades"] += 1
            if floors and (b["pisos"] or 0) < floors:
                b["pisos"] = floors
            continue
        cx = sum(pt[0] for pt in ring) / len(ring)
        cy = sum(pt[1] for pt in ring) / len(ring)
        by_footprint[sig] = {
            "npn": p.get("npn"), "direccion": p.get("direpred"), "barrio": p.get("nom_barrio"),
            "comuna": p.get("comuna"), "pisos": floors, "uso": (p.get("uso_princi") or "").strip() or None,
            "area": round(float(p.get("shape_area") or 0)), "ring": ring,
            "centroid": {"lat": cy, "lon": cx}, "unidades": 1,
        }
    return list(by_footprint.values())[:limit]


def _pip(ring, lon, lat) -> bool:
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]; x2, y2 = ring[(i + 1) % n]
        if ((y1 > lat) != (y2 > lat)) and (lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1):
            inside = not inside
    return inside


def predio_at(lat: float, lon: float):
    """Predio del catastro en el punto (para las fotos de Telegram): el que CONTIENE
    la coordenada; si ninguno, el más cercano en un radio de 25 m."""
    bs = fetch_buildings(lat, lon, radius=25, limit=10)
    for b in bs:
        if _pip(b["ring"], lon, lat):
            return b
    return bs[0] if bs else None


def gmaps(lat: float, lon: float, gkey: str | None = None) -> dict:
    link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    streetview = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}"
    static = None
    if gkey:
        static = (f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}"
                  f"&zoom=19&size=360x240&maptype=satellite&markers=color:red%7C{lat},{lon}&key={gkey}")
        streetview = f"https://maps.googleapis.com/maps/api/streetview?size=360x240&location={lat},{lon}&fov=80&key={gkey}"
    return {"maps": link, "streetview": streetview, "static": static}


def _floor_h(use: str | None) -> float:
    u = (use or "").lower()
    for k, v in FLOOR_H_BY_USE.items():
        if k in u:
            return v
    return 3.0


def _llm_notes(buildings: list) -> dict:
    """Nemotron (LangChain) razona sobre el conjunto: devuelve {npn: {floor_h, tipo, nota}}.
    Si no hay LLM disponible, lanza y el caller usa reglas deterministas."""
    from langchain_core.messages import SystemMessage, HumanMessage
    import massing_agent
    resumen = [{"npn": b["npn"], "pisos": b["pisos"], "uso": b["uso"], "area": b["area"],
                "dir": b["direccion"]} for b in buildings[:12]]
    system = ("Eres un agente urbanista. Para cada construcción real de Cali (con nº de pisos del catastro), "
              "decide la ALTURA DE PISO en metros según el uso (residencial ~2.7, comercial ~3.6, industrial ~5) "
              "y un tipo. Responde SOLO JSON: {\"items\":[{\"npn\":str,\"floor_h\":num,\"tipo\":str}]}.")
    human = "Construcciones: " + json.dumps(resumen, ensure_ascii=False)
    llm = massing_agent._get_llm()
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    data = massing_agent._extract_json(getattr(resp, "content", str(resp)))
    return {it.get("npn"): it for it in data.get("items", [])}


def plan_masses(buildings: list, use_llm: bool = True) -> tuple[list, str]:
    notes, note = {}, "reglas deterministas (altura de piso por uso)"
    if use_llm:
        try:
            notes = _llm_notes(buildings)
            note = "Nemotron (LangChain) asignó altura de piso por uso"
        except Exception as e:
            note = f"fallback sin LLM: {str(e)[:80]}"
    masses = []
    for b in buildings:
        floors = b["pisos"] or 3
        n = notes.get(b["npn"], {})
        fh = float(n.get("floor_h") or _floor_h(b["uso"]))
        h = round(floors * fh, 1)
        masses.append({
            "npn": b["npn"], "direccion": b["direccion"], "barrio": b["barrio"], "comuna": b["comuna"],
            "centroid": b["centroid"], "ring": b["ring"], "area": b["area"],
            "pisos": floors, "altura_piso": fh, "altura": h, "tipo": n.get("tipo") or b.get("uso") or "s/d",
            "osm_tags": {"building": "yes", "building:levels": str(floors), "height": str(h),
                         "ref:catastro:npn": b["npn"] or ""},
        })
    return masses, note


def run(lat: float, lon: float, radius: float = 120, limit: int = 20, gkey: str | None = None, use_llm: bool = True) -> dict:
    buildings = fetch_buildings(lat, lon, radius, limit)
    for b in buildings:
        b["gmaps"] = gmaps(b["centroid"]["lat"], b["centroid"]["lon"], gkey)
    masas, note = plan_masses(buildings, use_llm=use_llm)
    return {"center": {"lat": lat, "lon": lon}, "n": len(buildings), "buildings": buildings,
            "masas": masas, "agente": note}


if __name__ == "__main__":
    import sys
    la = float(sys.argv[1]) if len(sys.argv) > 1 else 3.4516
    lo = float(sys.argv[2]) if len(sys.argv) > 2 else -76.5320
    print(json.dumps(run(la, lo, radius=100, limit=8, use_llm=False), ensure_ascii=False, indent=2)[:1500])

"""
LifeCity · Agente de masas (LangChain + Nemotron)
=================================================
Genera propuestas volumétricas para un predio a partir de:
  - la normativa (área de lote, ICB, ICA) y el anillo del lote,
  - ejemplos aprendidos del editor (dataset .jsonl que exporta masas.html).

NO es una red entrenada desde cero (eso requiere un pipeline de ML aparte);
es un agente LLM que razona con la normativa + tus ejemplos (few-shot) y
devuelve masas/sólidos en JSON que el editor aplica. El dataset que graba el
editor sirve tanto de few-shot como, más adelante, para FINE-TUNING real.

Modelo: "Nemotron 3 Ultra" vía NVIDIA (langchain-nvidia-ai-endpoints).
Ajusta NEMOTRON_MODEL al id EXACTO que tengas disponible en build.nvidia.com / NIM.
"""
from __future__ import annotations
import os, json, pathlib, re
from typing import Any

DATASET = pathlib.Path(__file__).parent / "dataset.jsonl"
NEMOTRON_MODEL = os.getenv("NEMOTRON_MODEL", "nvidia/llama-3.1-nemotron-ultra-253b-v1")

SYSTEM = """Eres un arquitecto urbanista experto en normativa colombiana (POT) y volumetría.
Dada la información de un predio (área, índice de construcción básico ICB y adicional ICA)
propones una volumetría (masas) que APROVECHA la edificabilidad SIN exceder el máximo del POT.
Edificabilidad máxima = área_lote * (ICB + ICA). No superes ese valor.
Responde SOLO un JSON válido con esta forma exacta:
{"masses":[{"floors":int,"floorH":float,"offset":float,"baseZ":float}], "solids":[]}
- floors: número de pisos; floorH: altura de piso (m, ~3); offset: retiro/aislamiento (m);
- baseZ: cota base (m) para apilar (0 = suelo).
No incluyas explicaciones fuera del JSON."""

def _few_shot(limit: int = 6) -> list[dict]:
    if not DATASET.exists():
        return []
    ex = []
    for line in DATASET.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ex.append(json.loads(line))
        except Exception:
            pass
    return ex[-limit:]

def _get_llm():
    """Devuelve un chat model de LangChain. Prefiere Nemotron (NVIDIA);
    si no hay langchain-nvidia, usa un endpoint OpenAI-compatible."""
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA
        return ChatNVIDIA(model=NEMOTRON_MODEL, temperature=0.3,
                          api_key=os.getenv("NVIDIA_API_KEY"))
    except Exception:
        from langchain_openai import ChatOpenAI  # fallback OpenAI-compatible / NIM local
        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", NEMOTRON_MODEL),
                          temperature=0.3,
                          base_url=os.getenv("OPENAI_BASE_URL"),
                          api_key=os.getenv("OPENAI_API_KEY", "not-needed"))

def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("El modelo no devolvió JSON")
    return json.loads(m.group(0))

def suggest(predio: dict) -> dict:
    """predio: {npn, area, icb, ica, ring?, levels?}. -> {masses, solids}"""
    from langchain_core.messages import SystemMessage, HumanMessage
    area = float(predio.get("area") or 0)
    icb = float(predio.get("icb") or 0)
    ica = float(predio.get("ica") or 0)
    max_pot = area * (icb + ica)

    ejemplos = _few_shot()
    ex_txt = ""
    for e in ejemplos:
        try:
            inp = e.get("input", {}).get("predio", {})
            out = {"masses": e.get("output", {}).get("masses", [])}
            ex_txt += f"\nEJEMPLO -> predio {json.dumps(inp, ensure_ascii=False)} => {json.dumps(out, ensure_ascii=False)}"
        except Exception:
            pass

    human = (f"Predio: área={area} m², ICB={icb}, ICA={ica}. "
             f"Edificabilidad máxima POT = {round(max_pot)} m². "
             f"Propón masas que se acerquen a ese máximo sin excederlo."
             + (f"\nEjemplos previos del usuario:{ex_txt}" if ex_txt else ""))

    llm = _get_llm()
    resp = llm.invoke([SystemMessage(content=SYSTEM), HumanMessage(content=human)])
    data = _extract_json(getattr(resp, "content", str(resp)))
    data.setdefault("masses", [])
    data.setdefault("solids", [])
    return data

# ===================== INTERIORES (Nemotron) =====================
DATA_DIR = pathlib.Path(__file__).parent / "data"
INTER_LOG = DATA_DIR / "interactions.jsonl"

INTERIOR_SYSTEM = """Eres el arquitecto de interiores de LifeCity BIM (Cali, Colombia).
Diseñas UN espacio colocando elementos BIM del catálogo en coordenadas ABSOLUTAS en metros (plano XZ; el alto va en h).
Catálogo (typeId disponibles): {catalogo}.
REGLAS DURAS:
1) Si el uso es "habitacion" o "sala", incluye al menos una "ventana" en el PERÍMETRO (x≈cx±w/2 o z≈cz±d/2), rotY 0 si el borde es paralelo a X, 1.5708 si es paralelo a Z.
2) TODOS los objetos dentro del rectángulo (|x-cx|<=w/2, |z-cz|<=d/2).
3) "puerta" en un borde; "sanitario"/"lavamanos" solo en baños; "lavaplatos" solo en cocinas.
4) 4 a 8 objetos, distribución funcional y realista.
Responde SOLO JSON: {{"opcion":str,"descripcion":str,"objetos":[{{"typeId":str,"x":num,"z":num,"w":num,"h":num,"d":num,"rotY":num}}]}}"""

def _interior_examples(limit: int = 6) -> str:
    if not INTER_LOG.exists():
        return ""
    picks = []
    for line in INTER_LOG.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
            if r.get("event") == "interior_apply" and r.get("data", {}).get("objetos"):
                d = r["data"]
                picks.append(f'\nEJEMPLO -> uso={d.get("uso")} brief="{d.get("brief","")}" => {json.dumps(d.get("objetos"), ensure_ascii=False)}')
        except Exception:
            pass
    return "".join(picks[-limit:])

def suggest_interiors(payload: dict) -> dict:
    """payload: {room:{name,uso,x,z,w,d,level}, brief, catalog:[{id,label,w,h,d}], predio}
    -> {opcion, descripcion, objetos:[{typeId,x,z,w,h,d,rotY}]}"""
    from langchain_core.messages import SystemMessage, HumanMessage
    room = payload.get("room", {}) or {}
    brief = payload.get("brief", "") or ""
    catalog = payload.get("catalog", []) or []
    cat_txt = "; ".join(f"{c.get('id')}={c.get('label','')}({c.get('w')}x{c.get('h')}x{c.get('d')}m)" for c in catalog) \
        or "ventana, puerta, muro-drywall, sanitario, lavamanos, lavaplatos"
    ids = [c.get("id") for c in catalog] or ["ventana", "puerta", "muro-drywall", "sanitario", "lavamanos", "lavaplatos"]
    system = INTERIOR_SYSTEM.format(catalogo=cat_txt)
    human = (f'Espacio "{room.get("name","")}" uso={room.get("uso","habitacion")} '
             f'centro=({room.get("x")},{room.get("z")}) w={room.get("w")} d={room.get("d")}. '
             + (f"Indicaciones: {brief}. " if brief else "Propón la mejor distribución. ")
             + f"typeId permitidos: {ids}."
             + (f"\nEjemplos aprendidos:{_interior_examples()}"))
    llm = _get_llm()
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    data = _extract_json(getattr(resp, "content", str(resp)))
    data.setdefault("objetos", [])
    data.setdefault("opcion", "Diseño Nemotron")
    data.setdefault("descripcion", "")
    return data

def interiors_fallback(payload: dict) -> dict:
    """Distribución determinista (sin LLM) que respeta la regla de ventana."""
    room = payload.get("room", {}) or {}
    cx, cz = float(room.get("x", 0)), float(room.get("z", 0))
    w, d = float(room.get("w", 3)), float(room.get("d", 3))
    uso = room.get("uso", "habitacion")
    objs = [
        {"typeId": "ventana", "x": cx, "z": cz - d / 2, "w": min(1.2, w * 0.5), "h": 1.2, "d": 0.15, "rotY": 0},
        {"typeId": "puerta", "x": cx - w / 2, "z": cz, "w": 0.9, "h": 2.1, "d": 0.15, "rotY": 1.5708},
    ]
    if uso in ("bano",):
        objs += [{"typeId": "sanitario", "x": cx + w / 2 - 0.4, "z": cz - d / 2 + 0.4, "w": 0.4, "h": 0.4, "d": 0.6, "rotY": 0},
                 {"typeId": "lavamanos", "x": cx + w / 2 - 0.35, "z": cz + d / 2 - 0.35, "w": 0.5, "h": 0.85, "d": 0.4, "rotY": 0}]
    elif uso in ("cocina",):
        objs += [{"typeId": "lavaplatos", "x": cx, "z": cz + d / 2 - 0.35, "w": 0.8, "h": 0.9, "d": 0.6, "rotY": 0}]
    else:
        objs += [{"typeId": "muro-drywall", "x": cx + w / 2 - 0.3, "z": cz, "w": 0.15, "h": 2.4, "d": min(2.0, d * 0.6), "rotY": 0}]
    return {"opcion": "Distribucion base", "descripcion": "Fallback sin LLM (ventana + acceso).", "objetos": objs}

if __name__ == "__main__":
    demo = {"npn": "760010100040100210026000000000", "area": 93, "icb": 2.2, "ica": 4.0}
    print(json.dumps(suggest(demo), indent=2, ensure_ascii=False))

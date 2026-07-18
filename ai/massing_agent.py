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

if __name__ == "__main__":
    demo = {"npn": "760010100040100210026000000000", "area": 93, "icb": 2.2, "ica": 4.0}
    print(json.dumps(suggest(demo), indent=2, ensure_ascii=False))

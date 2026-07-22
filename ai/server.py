"""
LifeCity · Servidor del agente de masas (FastAPI)
Expone POST /suggest que consume el editor (masas.html → "Sugerir masa con IA").

Uso:
  pip install -r requirements.txt
  set NVIDIA_API_KEY=nvapi-...        (o OPENAI_API_KEY + OPENAI_BASE_URL)
  set NEMOTRON_MODEL=<id-exacto>      (el que tengas en build.nvidia.com / NIM)
  uvicorn server:app --host 0.0.0.0 --port 8000

Luego en el editor pega el endpoint:  http://localhost:8000/suggest
(Para producción publícalo con HTTPS y CORS de tu dominio.)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Optional
import traceback, os, json, datetime

import massing_agent
import agent_maps

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
LOG_PATH = os.path.join(DATA_DIR, "interactions.jsonl")

app = FastAPI(title="LifeCity Massing Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # en producción: ["https://app.lifecity.com.co"]
    allow_methods=["*"], allow_headers=["*"],
)

class Predio(BaseModel):
    npn: Optional[str] = None
    area: Optional[float] = 0
    icb: Optional[float] = 0
    ica: Optional[float] = 0
    ring: Optional[Any] = None
    levels: Optional[Any] = None
    objetivo: Optional[str] = None

@app.get("/health")
def health():
    return {"ok": True, "model": massing_agent.NEMOTRON_MODEL}

# ===================== PROTOCOLO DE APRENDIZAJE =====================
# Cada input/decisión del usuario (masa, sólido, habitación, brief de interiores,
# diseño aceptado/rechazado) se registra como ejemplo para mejorar la IA.
class LearnEvent(BaseModel):
    t: Optional[int] = None
    session: Optional[str] = None
    event: str
    data: Optional[Any] = None

@app.post("/learn")
def learn(ev: LearnEvent):
    rec = ev.model_dump()
    rec["server_ts"] = datetime.datetime.utcnow().isoformat() + "Z"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return {"ok": True}

@app.get("/learn/stats")
def learn_stats():
    n = 0
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, encoding="utf-8") as f:
            n = sum(1 for _ in f)
    return {"events": n, "path": LOG_PATH}

# ===================== NUBES DE PUNTOS · SERVICIO UNIFICADO =====================
# Sube una vez, streamea a todo el programa (visor, bim, cotizador). Si un loader
# local falla, el frontend reintenta contra este servicio. Deployable en la nube
# (misma app FastAPI en cualquier host; o cambia CLOUDS_DIR a un bucket montado).
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
CLOUDS_DIR = os.path.join(DATA_DIR, "clouds")
os.makedirs(CLOUDS_DIR, exist_ok=True)

def _safe_name(n: str) -> str:
    return "".join(c for c in (n or "nube") if c.isalnum() or c in "._-")[:80] or "nube"

@app.post("/cloud/upload")
async def cloud_upload(f: UploadFile = File(...)):
    try:
        name = _safe_name(f.filename)
        path = os.path.join(CLOUDS_DIR, name)
        size = 0
        with open(path, "wb") as out:
            while chunk := await f.read(1024 * 1024):
                out.write(chunk); size += len(chunk)
        return {"ok": True, "name": name, "bytes": size, "stream": f"/cloud/stream/{name}"}
    except Exception as e:
        traceback.print_exc(); return {"ok": False, "error": str(e)}

@app.get("/cloud/list")
def cloud_list():
    try:
        return {"clouds": [{"name": n, "bytes": os.path.getsize(os.path.join(CLOUDS_DIR, n))}
                            for n in sorted(os.listdir(CLOUDS_DIR))]}
    except Exception as e:
        return {"clouds": [], "error": str(e)}

@app.get("/cloud/stream/{name}")
def cloud_stream(name: str):
    path = os.path.join(CLOUDS_DIR, _safe_name(name))
    if not os.path.exists(path):
        return {"ok": False, "error": "no existe"}
    def gen():
        with open(path, "rb") as fh:
            while chunk := fh.read(1024 * 512):
                yield chunk
    return StreamingResponse(gen(), media_type="application/octet-stream",
                             headers={"Content-Length": str(os.path.getsize(path)),
                                      "Access-Control-Allow-Origin": "*"})

# ===================== AGENTE · MINADO DE NUEVAS CIUDADES =====================
CIUDADES_ACTUALES = ["Cali", "Bogotá", "Medellín", "Cartagena", "Quito", "Buenos Aires",
                     "Madrid", "Miami Lakes", "Boca Ratón", "Delray Beach"]

@app.post("/agent/cities")
def agent_cities(payload: dict):
    """Recomienda nuevas ciudades para crear visores (Nemotron; fallback curado)."""
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        llm = massing_agent._get_llm()
        system = ("Eres el agente de expansión de LifeCity (visores de catastro+normativa por ciudad). "
                  "Recomienda ciudades NUEVAS con catastro/datos abiertos accesibles (WFS/ArcGIS) y mercado inmobiliario activo. "
                  'Responde SOLO JSON: {"cities":[{"name":str,"pais":str,"fuente_datos":str,"razon":str}]} (5 a 8).')
        human = f"Ciudades ya cubiertas: {CIUDADES_ACTUALES}. Criterio extra: {payload.get('criterio','LatAm y España primero')}"
        resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
        data = massing_agent._extract_json(getattr(resp, "content", str(resp)))
        data["agente"] = "Nemotron"
        return data
    except Exception as e:
        return {"agente": f"fallback sin LLM: {str(e)[:60]}", "cities": [
            {"name": "Barranquilla", "pais": "Colombia", "fuente_datos": "Catastro distrital / IGAC WFS", "razon": "4a ciudad de Colombia, datos IGAC abiertos"},
            {"name": "Bucaramanga", "pais": "Colombia", "fuente_datos": "IGAC / catastro multipropósito", "razon": "mercado activo, catastro multipropósito"},
            {"name": "Ciudad de México", "pais": "México", "fuente_datos": "SEDUVI / datos abiertos CDMX", "razon": "mayor mercado hispano, uso de suelo abierto"},
            {"name": "Lima", "pais": "Perú", "fuente_datos": "COFOPRI / IGN", "razon": "gran demanda de vivienda"},
            {"name": "Ciudad de Panamá", "pais": "Panamá", "fuente_datos": "ANATI", "razon": "hub inmobiliario regional"},
            {"name": "Barcelona", "pais": "España", "fuente_datos": "Catastro ES (INSPIRE WFS)", "razon": "catastro INSPIRE ya probado con Madrid"},
        ]}

@app.post("/agent/maps")
def agent_maps_ep(payload: dict):
    """Agente de mapas: construcciones REALES de Cali (catastro) + pisos + masas.
    payload: {lat, lon, radius?, limit?, gkey?, use_llm?}"""
    try:
        lat = float(payload.get("lat")); lon = float(payload.get("lon"))
        radius = float(payload.get("radius") or 120); limit = int(payload.get("limit") or 20)
        gkey = payload.get("gkey") or os.getenv("GOOGLE_MAPS_KEY")
        use_llm = bool(payload.get("use_llm", True))
        return agent_maps.run(lat, lon, radius, limit, gkey, use_llm)
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e), "buildings": [], "masas": [], "agente": "error"}

@app.post("/interiors")
def interiors(payload: dict):
    """Diseño de interiores con Nemotron (mismo formato que el editor BIM espera).
    Si no hay LLM, usa el fallback determinista (respeta la regla de ventana)."""
    try:
        return massing_agent.suggest_interiors(payload)
    except Exception as e:
        traceback.print_exc()
        out = massing_agent.interiors_fallback(payload)
        out["note"] = f"fallback sin LLM: {e}"
        return out

@app.post("/suggest")
def suggest(p: Predio):
    try:
        return massing_agent.suggest(p.model_dump())
    except Exception as e:
        traceback.print_exc()
        # Fallback determinista si el LLM no está disponible: llena el índice con una torre simple.
        area = float(p.area or 0); icb = float(p.icb or 0); ica = float(p.ica or 0)
        max_pot = area * (icb + ica)
        floors = max(1, round(max_pot / area)) if area else 5
        return {"masses": [{"floors": int(floors), "floorH": 3.0, "offset": 3.0, "baseZ": 0}],
                "solids": [], "note": f"fallback sin LLM: {e}"}

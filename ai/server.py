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

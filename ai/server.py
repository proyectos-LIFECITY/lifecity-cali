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
import traceback

import massing_agent

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

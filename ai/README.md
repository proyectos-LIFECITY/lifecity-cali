# IA de masas — LangChain + Nemotron

El editor de masas (`masas.html`) **graba cada cambio** (crear rectángulo, extruir, mover puntos/aristas/caras, masas) y arma un **dataset** con el predio + su normativa (ICB/ICA) como *ejemplos*. Con eso, un **agente LLM** (Nemotron vía LangChain) propone volumetrías nuevas.

```
Editor (masas.html)  ──graba──►  dataset.jsonl  ──few-shot──►  Agente (LangChain + Nemotron)
        ▲                                                              │
        └───────────── "Sugerir masa con IA" (POST /suggest) ─────────┘
```

## Qué es y qué no es (honesto)
- **Sí:** un agente que razona con la normativa + tus ejemplos y devuelve masas en JSON que el editor aplica; el dataset crece con tu uso.
- **No (todavía):** una red neuronal entrenada desde cero. Eso es un pipeline de ML aparte. El `dataset.jsonl` que exportas es exactamente lo que se necesita para **fine-tuning** posterior (p. ej. LoRA sobre un Nemotron/Llama). Aquí queda listo para ese siguiente paso.

## Puesta en marcha
```bash
cd ai
pip install -r requirements.txt

# Credencial del modelo (elige una vía):
#  A) NVIDIA (Nemotron):
set NVIDIA_API_KEY=nvapi-xxxxxxxx
set NEMOTRON_MODEL=<id-exacto-del-modelo>   # cópialo de build.nvidia.com / tu NIM
#  B) Endpoint OpenAI-compatible / NIM local:
set OPENAI_BASE_URL=http://localhost:8001/v1
set OPENAI_API_KEY=not-needed
set NEMOTRON_MODEL=<id-del-modelo>

uvicorn server:app --host 0.0.0.0 --port 8000
```
Verifica: `GET http://localhost:8000/health`.

> **Nombre del modelo:** los ids de Nemotron cambian con el tiempo. Pon en `NEMOTRON_MODEL` el id **exacto** que tengas habilitado (busca "Nemotron Ultra" en build.nvidia.com). Si no pones ninguno, `/suggest` responde con un *fallback* determinista (una torre que llena el índice) para que el botón nunca quede sin respuesta.

## Conectar el editor
1. Sube tu `dataset.jsonl` a esta carpeta `ai/` (botón **"Descargar dataset"** en el editor) para que el agente aprenda de tus ejemplos.
2. En el editor, sección **"IA de masas"**, pega el endpoint: `http://localhost:8000/suggest` (o tu URL pública HTTPS).
3. Pulsa **"Sugerir masa con IA"**: envía `{predio, ring, levels}` y aplica las masas/sólidos que devuelve.

## Formato de respuesta esperado
```json
{ "masses": [ {"floors": 12, "floorH": 3.0, "offset": 3.0, "baseZ": 0} ],
  "solids": [ {"p1": {"x": -10, "z": -8}, "p2": {"x": 10, "z": 8}, "h": 24} ] }
```
`masses` = prismas paramétricos (pisos×altura, retiro, apilado); `solids` = cajas sketch (rectángulo p1–p2 extruido `h` m).

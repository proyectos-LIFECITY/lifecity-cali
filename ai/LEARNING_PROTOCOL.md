# Protocolo de aprendizaje · LifeCity (masas + interiores)

Objetivo: que la IA cree **mejores masas e interiores** aprendiendo de lo que hace el usuario.

## 1. Captura (cliente → `learn.js`)
Cada input/decisión se registra como evento `{ t, session, page, event, data }`:

| Evento | Cuándo |
|---|---|
| `rect`, `pushpull`, `move`, `mass_create` | edición de masas / modelado sketch |
| `ai_suggest` | el usuario pide/acepta una sugerencia de masa |
| `bim_open`, `open_plan`, `plan_level` | entra al editor BIM y a la planta por nivel |
| `room_draw_start`, `room_save` | crea/edita habitaciones (espacios a diseñar) |
| `interior_open`, `interior_brief`, `interior_apply_mcp` | usa la IA de interiores (Claude) |

Se guardan en `localStorage` (offline) y, si hay backend, se envían a `POST /learn`.

## 2. Almacenamiento (backend → `server.py`)
- `POST /learn` → añade el evento a **`ai/data/interactions.jsonl`** (una línea por evento).
- `GET  /learn/stats` → cuántos ejemplos se llevan.
- El editor también exporta el dataset local con **"Descargar dataset"** (`.jsonl`).

## 3. Aprendizaje (bucle de mejora)
1. **Few-shot inmediato:** el agente (`massing_agent.py`, Nemotron 3 Ultra vía LangChain) toma los ejemplos recientes del predio/uso similares y los inyecta como contexto → mejores sugerencias sin reentrenar.
2. **Curación:** periódicamente se filtran los `interactions.jsonl` (se conservan los diseños que el usuario **aceptó/guardó**, se descartan los deshechos) → `dataset_curado.jsonl`.
3. **Fine-tuning (opcional):** con suficientes ejemplos curados se afina un modelo (LoRA sobre un modelo abierto, o el flujo de customización de NVIDIA) para las masas/interiores típicos de cada ciudad/uso.
4. **Evaluación:** métricas simples — % de índice POT aprovechado sin exceder, regla de ventanas cumplida en interiores, nº de correcciones del usuario tras la sugerencia.

## 4. Señal de recompensa (qué es "mejor")
- **Masas:** maximizar área construida **sin exceder** `área × (ICB+ICA)`; respetar retiros/niveles; pocas correcciones posteriores.
- **Interiores:** regla dura (toda habitación y la sala con ventana); circulaciones válidas; que el usuario **guarde** el diseño (no lo deshaga).

## Privacidad
Los eventos guardan geometría y parámetros de diseño, no datos personales de arrendatarios. Para producción, mueve el `POST /learn` a tu backend con auth y anonimiza identificadores.

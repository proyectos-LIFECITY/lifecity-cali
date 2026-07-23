"""
LifeCity · Puente Telegram (sin n8n)
====================================
Hace polling del bot (TELEGRAM_BOT_TOKEN, ponlo en keys.bat). Flujo del usuario:
  1) Envía su UBICACIÓN (clip → Ubicación) al bot.
  2) Envía la FOTO.
El puente une foto+coordenada, DETECTA EL PREDIAL en el catastro IDESC
(agent_maps.predio_at) y lo expone en GET /photos con el formato que ya
consume la capa de fotos del visor. Responde al usuario con el predio detectado.
"""
from __future__ import annotations
import os, json, time, threading, urllib.request, urllib.parse, pathlib

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DATA = pathlib.Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)
PHOTOS_FILE = DATA / "photos.json"

photos: list = []
pending: dict = {}
_started = False


def _load():
    global photos
    try:
        photos = json.loads(PHOTOS_FILE.read_text(encoding="utf-8"))
    except Exception:
        photos = []


def _save():
    try:
        PHOTOS_FILE.write_text(json.dumps(photos[-500:], ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _api(method: str, **params):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=40) as r:
        return json.loads(r.read().decode())


def _reply(chat_id, text):
    try:
        _api("sendMessage", chat_id=chat_id, text=text)
    except Exception:
        pass


def _loop():
    import agent_maps
    offset = 0
    while True:
        try:
            res = _api("getUpdates", offset=offset, timeout=25)
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                chat = (msg.get("chat") or {}).get("id")
                if not chat:
                    continue
                if msg.get("location"):
                    pending[chat] = {"lat": msg["location"]["latitude"], "lon": msg["location"]["longitude"]}
                    _reply(chat, "📍 Ubicación recibida. Ahora envíame la FOTO del predio.")
                elif msg.get("photo"):
                    loc = pending.get(chat)
                    if not loc:
                        _reply(chat, "⚠️ Envía primero tu ubicación (📎 → Ubicación) y luego la foto.")
                        continue
                    fid = msg["photo"][-1]["file_id"]
                    finfo = _api("getFile", file_id=fid)
                    url = f"https://api.telegram.org/file/bot{TOKEN}/{finfo['result']['file_path']}"
                    predio = None
                    try:
                        predio = agent_maps.predio_at(loc["lat"], loc["lon"])
                    except Exception:
                        pass
                    cap = msg.get("caption") or ""
                    if predio:
                        cap = (cap + " · " if cap else "") + f"{predio.get('direccion') or ''} · NPN {predio.get('npn') or ''}"
                    photos.append({"id": str(msg.get("message_id")), "lat": loc["lat"], "lon": loc["lon"],
                                   "url": url, "caption": cap,
                                   "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                   "predio": predio})
                    _save()
                    pending.pop(chat, None)
                    if predio:
                        _reply(chat, f"✅ Foto ubicada y predio detectado:\n🏠 {predio.get('direccion') or 's/d'}"
                                     f"\nNPN {predio.get('npn') or 's/d'} · {predio.get('pisos') or '?'} piso(s)"
                                     f" · {predio.get('barrio') or ''}\nYa aparece en el visor LifeCity.")
                    else:
                        _reply(chat, "✅ Foto ubicada (no encontré predio del catastro en ese punto). Ya aparece en el visor.")
        except Exception:
            time.sleep(5)


def start() -> bool:
    """Arranca el polling si hay token. Devuelve True si quedó activo."""
    global _started
    if _started:
        return True
    if not TOKEN:
        return False
    _load()
    threading.Thread(target=_loop, daemon=True).start()
    _started = True
    return True

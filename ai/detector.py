"""
LifeCity · Puente al Detector de elementos (repo 68 · PointNet++)
================================================================
El detector real (red neuronal entrenada en la RTX 3060) corre en su propio
servidor (repo 68, http://127.0.0.1:8068). Este modulo es un PROXY:
  - acepta la nube (PLY o ASCII XYZ),
  - la convierte a PLY si hace falta,
  - la envia a /api/detect del detector,
  - devuelve JSON limpio { classes, counts, quantities } para el editor.
Asi el editor de masas usa EL MISMO motor (mismo modelo, mismo entrenamiento).
Config: DETECTOR_URL (env) o http://127.0.0.1:8068.
"""
from __future__ import annotations
import os, io, json, struct, urllib.request

DETECTOR_URL = os.getenv("DETECTOR_URL", "http://127.0.0.1:8068").rstrip("/")


def _to_ply(raw: bytes, filename: str) -> bytes:
    """Si ya es PLY lo deja; si es ASCII XYZ/CSV/PTS, lo convierte a PLY ascii."""
    name = (filename or "").lower()
    if name.endswith(".ply") or raw[:3] == b"ply":
        return raw
    pts = []
    for line in raw.decode("utf-8", "ignore").splitlines():
        parts = line.replace(",", " ").split()
        if len(parts) >= 3:
            try:
                pts.append((float(parts[0]), float(parts[1]), float(parts[2])))
            except ValueError:
                pass
    if len(pts) < 1000:
        raise ValueError("nube con muy pocos puntos legibles (se esperan X Y Z por linea)")
    head = ("ply\nformat ascii 1.0\nelement vertex %d\n"
            "property float x\nproperty float y\nproperty float z\nend_header\n" % len(pts))
    body = "\n".join(f"{x} {y} {z}" for x, y, z in pts)
    return (head + body + "\n").encode()


def _multipart(field: str, filename: str, data: bytes):
    boundary = "----lifecity" + os.urandom(8).hex()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; "
            f"filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n").encode()
    body += data + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def status() -> dict:
    try:
        with urllib.request.urlopen(DETECTOR_URL + "/api/status", timeout=8) as r:
            d = json.loads(r.read().decode())
        return {"ok": True, "detector": DETECTOR_URL, **d}
    except Exception as e:
        return {"ok": False, "detector": DETECTOR_URL,
                "error": f"detector no disponible ({e}). Arranca EJECUTAR_LOCAL.bat del repo 68."}


def detect(raw: bytes, filename: str) -> dict:
    ply = _to_ply(raw, filename)
    body, ctype = _multipart("file", "cloud.ply", ply)
    req = urllib.request.Request(DETECTOR_URL + "/api/detect", data=body,
                                 headers={"Content-Type": ctype})
    with urllib.request.urlopen(req, timeout=180) as r:
        payload = r.read()
    # parsear cabecera: [4B len][header json][xyz][rgb][labels]
    hlen = struct.unpack("<I", payload[:4])[0]
    header = json.loads(payload[4:4 + hlen].decode())
    sid = header.get("session_id")
    quantities = None
    try:
        with urllib.request.urlopen(DETECTOR_URL + f"/api/quantities/{sid}", timeout=15) as r:
            quantities = json.loads(r.read().decode())
    except Exception:
        pass
    classes = header.get("classes", [])
    counts = header.get("counts", [])
    return {"ok": True, "session_id": sid, "num_points": header.get("num_points"),
            "classes": classes, "counts": counts,
            "counts_by_class": {classes[i]: counts[i] for i in range(min(len(classes), len(counts)))},
            "quantities": quantities}

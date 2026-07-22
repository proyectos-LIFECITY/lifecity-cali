#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cotizador TRC y Decenal — servidor local (repo 52)
Estático (patrón repo 50 serve.py) + API mínima:
  POST /api/send-email    -> envía correo vía SMTP (config.email.json, patrón repo 29)
  POST /api/save-project  -> guarda el proyecto JSON en webapp/proyectos/ (lo leen los
                             comandos del plugin cotizador-seguros)
  GET  /api/email-status  -> indica si hay credenciales SMTP configuradas
Sin dependencias externas: solo librería estándar.
"""
import http.server, socketserver, json, os, re, socket, ssl, smtplib, mimetypes
from email.message import EmailMessage

PORT = 8124
ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_EMAIL = os.path.join(ROOT, "config.email.json")
PROYECTOS_DIR = os.path.join(ROOT, "proyectos")
MAX_ADJUNTOS_MB = 22  # margen bajo el límite de 25MB de Gmail

MIMES = {".js": "text/javascript", ".mjs": "text/javascript",
         ".json": "application/json", ".wasm": "application/wasm",
         ".ifc": "text/plain", ".csv": "text/csv"}


def leer_config_email():
    if not os.path.exists(CONFIG_EMAIL):
        return None
    try:
        with open(CONFIG_EMAIL, encoding="utf-8") as f:
            cfg = json.load(f)
        if cfg.get("usuario") and cfg.get("password"):
            return cfg
    except Exception:
        pass
    return None


def enviar_correo(cfg, para, asunto, cuerpo, adjuntos_dir=None):
    msg = EmailMessage()
    remitente = cfg["usuario"]
    msg["From"] = f'{cfg.get("nombre_remitente", "Cotizador LifeCity")} <{remitente}>'
    msg["To"] = para
    msg["Subject"] = asunto
    msg.set_content(cuerpo)

    adjuntados, omitidos = [], []
    if adjuntos_dir and os.path.isdir(adjuntos_dir):
        total = 0
        for nombre in sorted(os.listdir(adjuntos_dir)):
            ruta = os.path.join(adjuntos_dir, nombre)
            if not os.path.isfile(ruta):
                continue
            tam = os.path.getsize(ruta)
            if total + tam > MAX_ADJUNTOS_MB * 1024 * 1024:
                omitidos.append(nombre)
                continue
            ctype, _ = mimetypes.guess_type(nombre)
            maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
            with open(ruta, "rb") as f:
                msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=nombre)
            total += tam
            adjuntados.append(nombre)

    contexto = ssl.create_default_context()
    with smtplib.SMTP(cfg.get("smtp_host", "smtp.gmail.com"), int(cfg.get("smtp_port", 587)), timeout=60) as srv:
        srv.starttls(context=contexto)
        srv.login(remitente, cfg["password"])
        srv.send_message(msg)
    return adjuntados, omitidos


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        return MIMES.get(ext, super().guess_type(path))

    def _json(self, code, data):
        cuerpo = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        if self.path == "/api/email-status":
            return self._json(200, {"configurado": leer_config_email() is not None})
        return super().do_GET()

    def do_POST(self):
        try:
            largo = int(self.headers.get("Content-Length", 0))
            datos = json.loads(self.rfile.read(largo).decode("utf-8")) if largo else {}
        except Exception:
            return self._json(400, {"ok": False, "error": "JSON inválido"})

        if self.path == "/api/save-project":
            nombre = re.sub(r"[^A-Za-z0-9_\-]", "_", str(datos.get("filename", "proyecto")))[:80]
            os.makedirs(PROYECTOS_DIR, exist_ok=True)
            ruta = os.path.join(PROYECTOS_DIR, nombre + ".json")
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(datos.get("data", {}), f, ensure_ascii=False, indent=1)
            return self._json(200, {"ok": True, "ruta": ruta})

        if self.path == "/api/delete-project":
            nombre = re.sub(r"[^A-Za-z0-9_\-]", "_", str(datos.get("filename", "")))[:80]
            if not nombre:
                return self._json(400, {"ok": False, "error": "filename requerido"})
            ruta = os.path.join(PROYECTOS_DIR, nombre + ".json")
            existia = os.path.isfile(ruta)
            if existia:
                os.remove(ruta)
            return self._json(200, {"ok": True, "borrado": existia})

        if self.path == "/api/send-email":
            cfg = leer_config_email()
            if not cfg:
                return self._json(400, {"ok": False, "error": "Sin config.email.json — usa el botón mailto: o crea el archivo (ver config.email.example.json)"})
            para = (datos.get("para") or "").strip()
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+(\s*[;,]\s*[^@\s]+@[^@\s]+\.[^@\s]+)*$", para):
                return self._json(400, {"ok": False, "error": "Destinatario inválido"})
            try:
                adj, omit = enviar_correo(cfg, para, datos.get("asunto", "(sin asunto)"),
                                          datos.get("cuerpo", ""), datos.get("adjuntosDir"))
                return self._json(200, {"ok": True, "adjuntos": adj, "omitidos": omit})
            except smtplib.SMTPAuthenticationError:
                return self._json(400, {"ok": False, "error": "Autenticación SMTP falló — revisa usuario/App Password en config.email.json"})
            except Exception as e:
                return self._json(500, {"ok": False, "error": str(e)})

        return self._json(404, {"ok": False, "error": "Ruta no encontrada"})

    def log_message(self, fmt, *args):
        print("[cotizador]", fmt % args)


class ServidorHilos(socketserver.ThreadingTCPServer):
    daemon_threads = True
    # En Windows SO_REUSEADDR permite que dos procesos se monten en el mismo
    # puerto (doble-bind) y las conexiones fallan de forma aleatoria.
    allow_reuse_address = (os.name != "nt")
    # Dual-stack: Chrome resuelve localhost como ::1 (IPv6); hay que atender
    # IPv6 e IPv4 a la vez o el navegador ve ERR_CONNECTION_REFUSED.
    address_family = socket.AF_INET6

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except OSError:
            pass
        super().server_bind()


if __name__ == "__main__":
    os.chdir(ROOT)
    with ServidorHilos(("::", PORT), Handler) as httpd:
        print(f"Cotizador TRC y Decenal -> http://localhost:{PORT}/index.html")
        print(f"SMTP configurado: {'si' if leer_config_email() else 'no (solo mailto:)'}")
        httpd.serve_forever()

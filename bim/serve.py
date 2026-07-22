#!/usr/bin/env python3
"""Servidor estatico local para LifeCity.
Fuerza el MIME de .js/.mjs a text/javascript para que los modulos ES carguen
bien en Windows (donde el registro a veces los marca como text/plain)."""
import http.server
import socketserver

PORT = 8123
Handler = http.server.SimpleHTTPRequestHandler
Handler.extensions_map = dict(Handler.extensions_map)
Handler.extensions_map.update({
    '.js': 'text/javascript',
    '.mjs': 'text/javascript',
    '.json': 'application/json',
    '.wasm': 'application/wasm',
})

if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"LifeCity en http://localhost:{PORT}  (Ctrl+C para detener)")
        httpd.serve_forever()

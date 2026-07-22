# LifeCity BIM · Servidor MCP

Conecta **Claude** (Desktop o Claude Code) con el editor BIM 5D para que genere
**opciones de diseño por habitación** directamente sobre el modelo.

## Instalación

```bash
cd mcp
npm install
```

## Conectar a Claude Desktop

En `%APPDATA%\Claude\claude_desktop_config.json` agrega:

```json
{
  "mcpServers": {
    "lifecity-bim": {
      "command": "node",
      "args": ["G:\\Mi unidad\\6. REPOS\\50. LifeCity BIM 5D\\mcp\\server.mjs"]
    }
  }
}
```

## Conectar a Claude Code

```bash
claude mcp add lifecity-bim -- node "G:\Mi unidad\6. REPOS\50. LifeCity BIM 5D\mcp\server.mjs"
```

## Flujo de uso

1. En **masas.html** (Obra nueva): dibuja las habitaciones (con su **uso**: habitación, sala, cocina…) y pulsa **"Exportar para Claude (MCP)"**. Guarda el JSON en `mcp/proyectos/`.
2. En Claude: *"Lee el proyecto X con lifecity-bim y genera 3 opciones de diseño para la habitación 'Alcoba 1'"*.
   - Tools: `listar_proyectos`, `leer_proyecto`, `listar_habitaciones`, `agregar_opcion_diseno`, `validar_proyecto`.
   - **Regla dura** (validada por el servidor): toda **habitación** y la **sala** deben incluir al menos una **ventana** en el perímetro del espacio.
3. En **masas.html**: **"Importar diseño de Claude (MCP)"** → los objetos aparecen en 3D y en la planta del nivel, marcados como opción.

## Estructura del proyecto JSON

`rooms[]` (roomId, uso, centro x/z, w×d, nivel) · `bim[]` (objetos; los de Claude llevan `fromClaude`, `optionName`, `roomId`) · `levels[]` · `designNotes[]`.

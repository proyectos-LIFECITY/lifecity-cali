/* ==========================================================================
 * LifeCity · Configuración de endpoints (nube + agente local)
 * --------------------------------------------------------------------------
 * Todo el "development" corre en la NUBE (backend en Render). Las funciones
 * que necesitan GPU/CUDA (detector de elementos PointNet++ y procesamiento
 * pesado de nube de puntos) corren LOCALMENTE en el PC del usuario mediante
 * el instalador "LifeCity Local" (localhost). Este archivo decide, por cada
 * llamada, si va a la nube o al agente local, y si el agente local no está
 * corriendo ofrece descargar el instalador.
 *
 * Ruteo:
 *   - CPU / catastro / agentes / IA de texto  → LC.cloud(path)   (Render)
 *   - GPU / detector / nube de puntos         → LC.local(path)   (localhost)
 *
 * Sobrescribible sin tocar código:
 *   - ?api=https://mi-backend            (o localStorage 'lifecity_cloud_api')
 *   - localStorage 'lifecity_local_agent' (por defecto http://localhost:8000)
 * ======================================================================== */
(function () {
  // Cambia esto por la URL real que te dé Render (o déjalo y usa ?api=...).
  var DEFAULT_CLOUD = 'https://lifecity-api.onrender.com';
  var DEFAULT_LOCAL = 'http://localhost:8000';
  // Página de descarga del instalador (servida por GitHub Pages).
  var INSTALLER_PAGE = '/descargar.html';

  function qp(k) { try { return new URLSearchParams(location.search).get(k); } catch (e) { return null; } }
  function clean(u) { return (u || '').replace(/\/+$/, ''); }

  var LC = {
    cloudApi: clean(qp('api') || localStorage.getItem('lifecity_cloud_api') || DEFAULT_CLOUD),
    localAgent: clean(localStorage.getItem('lifecity_local_agent') || DEFAULT_LOCAL),
    installerPage: INSTALLER_PAGE,
    _localUp: null,

    /** URL de un endpoint en la NUBE (Render). */
    cloud: function (path) { return this.cloudApi + (path.charAt(0) === '/' ? path : '/' + path); },
    /** URL de un endpoint en el AGENTE LOCAL (localhost, GPU). */
    local: function (path) { return this.localAgent + (path.charAt(0) === '/' ? path : '/' + path); },

    /** ¿Está corriendo el agente local? (cachea el resultado por sesión). */
    localReady: function (timeout) {
      var self = this;
      return new Promise(function (resolve) {
        var ctrl = ('AbortController' in window) ? new AbortController() : null;
        var t = setTimeout(function () { if (ctrl) ctrl.abort(); }, timeout || 1500);
        fetch(self.localAgent + '/health', ctrl ? { signal: ctrl.signal } : {})
          .then(function (r) { clearTimeout(t); self._localUp = !!(r && r.ok); resolve(self._localUp); })
          .catch(function () { clearTimeout(t); self._localUp = false; resolve(false); });
      });
    },

    /**
     * Garantiza que el agente local esté listo para una función GPU.
     * Si no lo está, muestra el modal de descarga del instalador y resuelve false.
     * @returns Promise<boolean>
     */
    ensureLocal: function (featureName) {
      var self = this;
      return this.localReady().then(function (up) {
        if (up) return true;
        self.showInstaller(featureName);
        return false;
      });
    },

    /** Modal con la descarga del instalador LifeCity Local. */
    showInstaller: function (featureName) {
      if (document.getElementById('lc-installer-modal')) {
        document.getElementById('lc-installer-modal').style.display = 'flex';
        return;
      }
      var ov = document.createElement('div');
      ov.id = 'lc-installer-modal';
      ov.style.cssText = 'position:fixed;inset:0;background:rgba(6,9,13,.85);z-index:99999;display:flex;align-items:center;justify-content:center;font-family:system-ui,Segoe UI,sans-serif';
      ov.innerHTML =
        '<div style="background:#11161e;border:1px solid #2a3548;border-radius:14px;max-width:440px;width:92%;padding:22px;color:#e6ecf5">' +
        '<div style="font-size:26px">🖥️⚡</div>' +
        '<h2 style="font-size:17px;margin:8px 0 4px">Esta función corre en tu PC</h2>' +
        '<p style="font-size:12.5px;color:#8b97aa;line-height:1.5;margin:0 0 12px">' +
        '<b style="color:#e6ecf5">' + (featureName || 'El detector de elementos') + '</b> usa tu tarjeta gráfica (GPU) y no puede correr en la nube. ' +
        'Instala <b style="color:#f4b942">LifeCity Local</b> una sola vez: se ejecuta en segundo plano con tus permisos y el visor lo detecta automáticamente.</p>' +
        '<ol style="font-size:12px;color:#8b97aa;line-height:1.7;margin:0 0 14px;padding-left:18px">' +
        '<li>Descarga e instala <b>LifeCity Local</b>.</li>' +
        '<li>Acepta el permiso de Firewall (solo localhost).</li>' +
        '<li>Vuelve aquí y repite la acción.</li></ol>' +
        '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
        '<a href="' + this.installerPage + '" target="_blank" style="flex:1;text-align:center;background:#f4b942;color:#1a1305;font-weight:700;padding:11px;border-radius:8px;text-decoration:none;font-size:13px">⇩ Descargar LifeCity Local</a>' +
        '<button id="lc-inst-retry" style="background:#1a2230;border:1px solid #2a3548;color:#e6ecf5;padding:11px 14px;border-radius:8px;cursor:pointer;font-size:13px">Ya lo instalé ↻</button>' +
        '</div>' +
        '<button id="lc-inst-x" style="background:none;border:0;color:#8b97aa;margin-top:10px;cursor:pointer;font-size:11px;width:100%">Cerrar</button>' +
        '</div>';
      document.body.appendChild(ov);
      document.getElementById('lc-inst-x').onclick = function () { ov.style.display = 'none'; };
      document.getElementById('lc-inst-retry').onclick = function () {
        var b = this; b.textContent = 'Comprobando…';
        LC.localReady(2500).then(function (up) {
          if (up) { ov.style.display = 'none'; b.textContent = 'Ya lo instalé ↻'; }
          else { b.textContent = 'Aún no responde ✗'; setTimeout(function(){ b.textContent = 'Ya lo instalé ↻'; }, 1800); }
        });
      };
    }
  };

  window.LC = LC;
})();

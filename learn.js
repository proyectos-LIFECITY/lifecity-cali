/* ============================================================
   LifeCity · Protocolo de aprendizaje (cliente)
   Registra cada INPUT/decisión del usuario como ejemplo de entrenamiento.
   - Guarda en localStorage (offline) y, si hay backend, hace POST /learn.
   - window.LifeLearn.log(evento, datos)
   - window.LifeLearn.exportJsonl()  → dataset descargable
   Eventos típicos: 'mass_create','solid_rect','push_pull','vertex_move',
   'room_create','interior_brief','interior_apply','ai_suggest','level_add'.
   ============================================================ */
(function () {
  var LKEY = 'lifecity_learn_log';
  var EKEY = 'cali_learn_endpoint';
  var endpoint = localStorage.getItem(EKEY) || 'http://localhost:8000/learn';

  function sid() {
    var s = sessionStorage.getItem('lc_sid');
    if (!s) { s = 's' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); sessionStorage.setItem('lc_sid', s); }
    return s;
  }
  function load() { try { return JSON.parse(localStorage.getItem(LKEY) || '[]'); } catch (e) { return []; } }
  function save(a) { try { localStorage.setItem(LKEY, JSON.stringify(a.slice(-3000))); } catch (e) {} }

  function log(event, data) {
    var rec = { t: Date.now(), session: sid(), page: location.pathname.split('/').pop(), event: event, data: data || {} };
    var a = load(); a.push(rec); save(a);
    if (endpoint) {
      try { fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(rec), keepalive: true }).catch(function () {}); } catch (e) {}
    }
    return rec;
  }
  window.LifeLearn = {
    log: log,
    all: load,
    count: function () { return load().length; },
    exportJsonl: function () { return load().map(function (r) { return JSON.stringify(r); }).join('\n'); },
    setEndpoint: function (u) { endpoint = u; localStorage.setItem(EKEY, u); },
    endpoint: function () { return endpoint; }
  };
})();

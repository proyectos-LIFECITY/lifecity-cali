// ===================================================================
// OSMPublish — publica edificaciones en OpenStreetMap (API 0.6)
// Autenticación OAuth 2.0 con PKCE (flujo out-of-band: copiar/pegar código).
// Servidores: sandbox de desarrollo (pruebas, recomendado para estudios de
// masas) y producción (solo edificios que existen en la realidad — regla OSM).
//
// Uso: OSMPublish.setClientId(...); await OSMPublish.beginAuth();
//      await OSMPublish.exchangeCode(codigo);
//      await OSMPublish.publishBuildings([{ ring:[[lon,lat],...], tags:{...} }], 'comentario');
// ===================================================================
(function () {
  const SERVERS = {
    sandbox: {
      label: 'Sandbox dev (pruebas)',
      auth: 'https://master.apis.dev.openstreetmap.org',
      api: 'https://master.apis.dev.openstreetmap.org',
      web: 'https://master.apis.dev.openstreetmap.org',
    },
    live: {
      label: 'OSM producción',
      auth: 'https://www.openstreetmap.org',
      api: 'https://api.openstreetmap.org',
      web: 'https://www.openstreetmap.org',
    },
  };
  const OOB = 'urn:ietf:wg:oauth:2.0:oob';
  const LS = (k) => 'lc_osm_' + k;

  let server = localStorage.getItem(LS('server')) || 'sandbox';
  if (!SERVERS[server]) server = 'sandbox';

  const cfg = () => SERVERS[server];
  function setServer(s) { if (SERVERS[s]) { server = s; localStorage.setItem(LS('server'), s); } }
  function getClientId() { return localStorage.getItem(LS('client_' + server)) || ''; }
  function setClientId(v) { localStorage.setItem(LS('client_' + server), (v || '').trim()); }
  const token = () => localStorage.getItem(LS('token_' + server)) || '';
  const isConnected = () => !!token();
  function logout() { localStorage.removeItem(LS('token_' + server)); }

  function b64url(bytes) {
    let s = '';
    for (const b of bytes) s += String.fromCharCode(b);
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  // Abre la pantalla de autorización de OSM; el usuario copia el código mostrado
  async function beginAuth() {
    const clientId = getClientId();
    if (!clientId) throw new Error('Configura el Client ID: registra una app OAuth2 en ' + cfg().auth + '/oauth2/applications con redirect "' + OOB + '" y permiso write_api.');
    const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)));
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
    localStorage.setItem(LS('verifier_' + server), verifier);
    const q = new URLSearchParams({
      client_id: clientId, redirect_uri: OOB, response_type: 'code',
      scope: 'write_api', code_challenge: b64url(new Uint8Array(digest)), code_challenge_method: 'S256',
    });
    const url = cfg().auth + '/oauth2/authorize?' + q.toString();
    window.open(url, '_blank');
    return url;
  }

  // Canjea el código pegado por el usuario por un access token
  async function exchangeCode(code) {
    const verifier = localStorage.getItem(LS('verifier_' + server));
    if (!verifier) throw new Error('Primero pulsa "Conectar cuenta OSM".');
    const res = await fetch(cfg().auth + '/oauth2/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code', code: (code || '').trim(),
        client_id: getClientId(), redirect_uri: OOB, code_verifier: verifier,
      }).toString(),
    });
    if (!res.ok) throw new Error('OSM rechazó el código (' + res.status + '): ' + (await res.text()).slice(0, 160));
    const data = await res.json();
    if (!data.access_token) throw new Error('OSM no devolvió token de acceso');
    localStorage.setItem(LS('token_' + server), data.access_token);
    localStorage.removeItem(LS('verifier_' + server));
    return true;
  }

  async function apiFetch(path, method, body) {
    const headers = { 'Authorization': 'Bearer ' + token() };
    if (body) headers['Content-Type'] = 'text/xml; charset=utf-8';
    const res = await fetch(cfg().api + path, { method, headers, body: body || undefined });
    const text = await res.text();
    if (res.status === 401) { logout(); throw new Error('Sesión OSM expirada: vuelve a conectar tu cuenta.'); }
    if (!res.ok) throw new Error('OSM API ' + res.status + ': ' + text.slice(0, 200));
    return text;
  }

  const escXml = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  // buildings: [{ ring: [[lon,lat],...] , tags: { building:'yes', height:'30', ... } }]
  // Crea changeset → sube nodos y ways (osmChange) → cierra changeset.
  async function publishBuildings(buildings, comment) {
    if (!isConnected()) throw new Error('Conecta tu cuenta OSM primero.');
    if (!buildings || !buildings.length) throw new Error('No hay geometrías para publicar.');
    const csXml = '<osm><changeset>' +
      '<tag k="created_by" v="LifeCity Massing 0.2"/>' +
      '<tag k="comment" v="' + escXml(comment || 'Edificaciones LifeCity') + '"/>' +
      '</changeset></osm>';
    const csId = (await apiFetch('/api/0.6/changeset/create', 'PUT', csXml)).trim();
    let nid = -1, wid = -1;
    const nodes = [], ways = [];
    for (const b of buildings) {
      let ring = (b.ring || []).slice();
      const f0 = ring[0], l0 = ring[ring.length - 1];
      if (ring.length > 3 && f0 && l0 && Math.abs(f0[0] - l0[0]) < 1e-9 && Math.abs(f0[1] - l0[1]) < 1e-9) ring = ring.slice(0, -1);
      if (ring.length < 3) continue;
      const refs = [];
      for (const [lon, lat] of ring) {
        const id = nid--;
        nodes.push('<node id="' + id + '" lon="' + lon.toFixed(7) + '" lat="' + lat.toFixed(7) + '" changeset="' + csId + '"/>');
        refs.push(id);
      }
      refs.push(refs[0]); // anillo cerrado
      const tags = Object.entries(b.tags || {}).map(([k, v]) => '<tag k="' + escXml(k) + '" v="' + escXml(v) + '"/>').join('');
      ways.push('<way id="' + (wid--) + '" changeset="' + csId + '">' + refs.map(r => '<nd ref="' + r + '"/>').join('') + tags + '</way>');
    }
    if (!ways.length) throw new Error('Ninguna huella válida para publicar.');
    const osc = '<osmChange version="0.6" generator="LifeCity Massing"><create>' + nodes.join('') + ways.join('') + '</create></osmChange>';
    await apiFetch('/api/0.6/changeset/' + csId + '/upload', 'POST', osc);
    await apiFetch('/api/0.6/changeset/' + csId + '/close', 'PUT');
    return { changeset: csId, url: cfg().web + '/changeset/' + csId, count: ways.length };
  }

  window.OSMPublish = {
    SERVERS, oob: OOB,
    server: () => server, setServer,
    getClientId, setClientId,
    isConnected, logout,
    beginAuth, exchangeCode,
    publishBuildings,
    registerUrl: () => cfg().auth + '/oauth2/applications',
  };
})();

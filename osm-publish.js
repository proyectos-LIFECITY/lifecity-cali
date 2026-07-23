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

  // App OAuth2 de LifeCity registrada en OSM producción. La app quedó registrada como
  // CONFIDENCIAL, por lo que el canje del token exige también el client_secret.
  // (Nota: al ir en el frontend el secreto es visible; con una app "pública" en OSM
  // bastaría PKCE sin secreto.) Redirect registrado: cali_aec_viewer.html.
  const DEFAULT_CLIENT = { live: 'NklL5gBi2MuVOwXixR4-LR-E0dYuQKvru8cgslPOnGo', sandbox: '' };
  const DEFAULT_SECRET = { live: 'cSE0l0x-uvpDArO6Vr8Oqj9IcB8kBkD5xM5q30_Te08', sandbox: '' };
  const WEB_REDIRECT = 'https://app.lifecity.com.co/cali_aec_viewer.html';
  // Usa el flujo de REDIRECCIÓN cuando estamos en el dominio registrado; si no, OOB (copiar/pegar).
  const useRedirect = () => (location.origin === 'https://app.lifecity.com.co');
  const redirectUri = () => (useRedirect() ? WEB_REDIRECT : OOB);

  let server = localStorage.getItem(LS('server')) || 'live';
  if (!SERVERS[server]) server = 'live';

  const cfg = () => SERVERS[server];
  function setServer(s) { if (SERVERS[s]) { server = s; localStorage.setItem(LS('server'), s); } }
  function getClientId() { return localStorage.getItem(LS('client_' + server)) || DEFAULT_CLIENT[server] || ''; }
  function setClientId(v) { localStorage.setItem(LS('client_' + server), (v || '').trim()); }
  const token = () => localStorage.getItem(LS('token_' + server)) || '';
  const isConnected = () => !!token();
  function logout() { localStorage.removeItem(LS('token_' + server)); }

  function b64url(bytes) {
    let s = '';
    for (const b of bytes) s += String.fromCharCode(b);
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  // Inicia OAuth2 PKCE por REDIRECCIÓN (vuelve a cali_aec_viewer.html con ?code).
  // Solo funciona en el dominio registrado en la app OAuth de OSM: OSM ya NO acepta
  // el redirect out-of-band (urn:...:oob), así que desde localhost no hay conexión.
  async function beginAuth() {
    const clientId = getClientId();
    if (!clientId) throw new Error('Configura el Client ID (registra una app OAuth2 en ' + cfg().auth + '/oauth2/applications con permiso write_api).');
    if (!useRedirect()) {
      throw new Error('Conecta OSM desde https://app.lifecity.com.co — tu app OAuth de OSM solo tiene registrado ese redirect (OSM ya no acepta el flujo de copiar/pegar código). Una vez conectado allí, la sesión OSM queda guardada en ese navegador.');
    }
    const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)));
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
    localStorage.setItem(LS('verifier_' + server), verifier);
    const q = new URLSearchParams({
      client_id: clientId, redirect_uri: WEB_REDIRECT, response_type: 'code',
      scope: 'write_api', code_challenge: b64url(new Uint8Array(digest)), code_challenge_method: 'S256',
    });
    const url = cfg().auth + '/oauth2/authorize?' + q.toString();
    localStorage.setItem(LS('flow'), 'redirect');
    location.href = url;
    return url;
  }

  // Canjea el código por un access token (OOB: pegado; redirect: recibido en la URL)
  async function exchangeCode(code, ru) {
    const verifier = localStorage.getItem(LS('verifier_' + server));
    if (!verifier) throw new Error('Primero pulsa "Conectar cuenta OSM".');
    const body = {
      grant_type: 'authorization_code', code: (code || '').trim(),
      client_id: getClientId(), redirect_uri: ru || redirectUri(), code_verifier: verifier,
    };
    const secret = localStorage.getItem(LS('secret_' + server)) || DEFAULT_SECRET[server] || '';
    if (secret) body.client_secret = secret; // app confidencial: OSM exige el secreto en el canje
    const res = await fetch(cfg().auth + '/oauth2/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams(body).toString(),
    });
    if (!res.ok) throw new Error('OSM rechazó el código (' + res.status + '): ' + (await res.text()).slice(0, 160));
    const data = await res.json();
    if (!data.access_token) throw new Error('OSM no devolvió token de acceso');
    localStorage.setItem(LS('token_' + server), data.access_token);
    localStorage.removeItem(LS('verifier_' + server));
    return true;
  }

  // Callback del flujo de redirección: si volvemos con ?code=..., lo canjeamos y limpiamos la URL.
  async function handleRedirectCallback() {
    if (localStorage.getItem(LS('flow')) !== 'redirect') return false;
    const qs = new URLSearchParams(location.search);
    const code = qs.get('code');
    if (!code) return false;
    try {
      await exchangeCode(code, WEB_REDIRECT);
      localStorage.removeItem(LS('flow'));
      // limpiar ?code de la URL
      const clean = location.pathname + location.hash;
      history.replaceState(null, '', clean);
      window.dispatchEvent(new CustomEvent('osm-connected'));
      return true;
    } catch (e) { console.warn('[OSM] callback:', e.message); return false; }
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
    usesRedirect: useRedirect,
    handleRedirectCallback,
    registerUrl: () => cfg().auth + '/oauth2/applications',
  };
  // Auto-procesa el retorno del OAuth por redirección (?code=...) al cargar cualquier página que incluya este script.
  handleRedirectCallback();
})();

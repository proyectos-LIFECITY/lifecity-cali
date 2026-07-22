/* LifeCity · guard de sesión para el Cotizador (bajo /cotizador/webapp/).
   Redirige al login raíz del dominio si no hay sesión válida. */
(function () {
  var KEY = 'lifecity_session';
  var LOGIN = '../../login.html';
  var s = null;
  try { s = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { s = null; }
  if (!s || (s.exp && Date.now() > s.exp)) {
    try { localStorage.removeItem(KEY); } catch (e) {}
    location.replace(LOGIN);
    return;
  }
  window.LifeCityAuth = {
    user: function () { return s; },
    name: function () { return (s && (s.name || s.email)) || 'Usuario'; },
    logout: function () { try { localStorage.removeItem(KEY); } catch (e) {} location.replace(LOGIN); }
  };
})();

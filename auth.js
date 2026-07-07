/* LifeCity · guard de sesión.
   Incluir en <head> ANTES del resto: <script src="auth.js"></script>
   Redirige a login.html si no hay sesión válida. */
/* LifeCity · guard de sesión.
   Incluir en <head> ANTES del resto: <script src="auth.js"></script>
   Redirige a login.html si no hay sesión válida. */
(function () {
  var KEY = 'lifecity_session';
  var LOGIN = 'login.html';
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
    loggedIn: function () { return true; },
    logout: function () { try { localStorage.removeItem(KEY); } catch (e) {} location.replace(LOGIN); }
  };
})();

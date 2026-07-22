/* ============================================================
   LifeCity · Plataforma (Supabase por usuario + licencias)
   - Cada usuario logueado tiene su propio set de proyectos (tabla user_state, RLS).
   - Plan free/pro (tabla profiles). Redención de licencia (RPC redeem_license).
   - Fallback: sin sesión Supabase => localStorage anónimo, plan 'free'.
   API:  await LifePlatform.ready;
         LifePlatform.userId()/email()/isLogged()
         LifePlatform.projectsKey()                      // clave localStorage por-usuario
         await LifePlatform.pull()                        // baja proyectos del usuario a localStorage
         await LifePlatform.push()                        // sube proyectos del usuario a Supabase
         LifePlatform.plan() / isPro()
         await LifePlatform.refreshPlan()
         await LifePlatform.redeem(code)
   ============================================================ */
(function () {
  var CFG = window.SUPABASE_CONFIG || {};
  var PROPS_BASE = 'cali_aec_props_v1';
  var state = { sb: null, user: null, plan: 'free', planExp: null };
  var resolveReady;
  var readyP = new Promise(function (r) { resolveReady = r; });

  function shortId() { return state.user ? ('u' + String(state.user.id).replace(/-/g, '').slice(0, 12)) : 'anon'; }
  function projectsKey() { return PROPS_BASE + '_' + shortId(); }
  function localProps() { try { return JSON.parse(localStorage.getItem(projectsKey()) || '[]'); } catch (e) { return []; } }

  async function init() {
    try {
      if (CFG.url && CFG.anonKey) {
        var mod = await import('https://esm.sh/@supabase/supabase-js@2');
        state.sb = mod.createClient(CFG.url, CFG.anonKey);
        var s = (await state.sb.auth.getSession()).data.session;
        state.user = s ? s.user : null;
        if (state.user) { await refreshPlan(); await pull(); }
      }
    } catch (e) { console.warn('[LifePlatform] Supabase no disponible:', e.message); }
    // plan cacheado (offline)
    try { var c = JSON.parse(localStorage.getItem('cali_plan') || 'null'); if (c && !state.user) { state.plan = c.plan || 'free'; state.planExp = c.exp || null; } } catch (e) {}
    resolveReady(true);
  }

  async function refreshPlan() {
    if (!state.sb || !state.user) return state.plan;
    try {
      var r = await state.sb.from('profiles').select('plan,plan_expires').eq('id', state.user.id).maybeSingle();
      if (r.data) { state.plan = r.data.plan || 'free'; state.planExp = r.data.plan_expires || null; }
      else { await state.sb.from('profiles').insert({ id: state.user.id, email: state.user.email, plan: 'free' }); state.plan = 'free'; }
      localStorage.setItem('cali_plan', JSON.stringify({ plan: state.plan, exp: state.planExp }));
    } catch (e) { console.warn('[LifePlatform] plan:', e.message); }
    return state.plan;
  }

  async function pull() {
    if (!state.sb || !state.user) return;
    try {
      var r = await state.sb.from('user_state').select('data').eq('key', 'properties').maybeSingle();
      if (r.data && Array.isArray(r.data.data)) localStorage.setItem(projectsKey(), JSON.stringify(r.data.data));
    } catch (e) { console.warn('[LifePlatform] pull:', e.message); }
  }
  var pushT = null;
  async function push() {
    if (!state.sb || !state.user) return;
    try { await state.sb.from('user_state').upsert({ user_id: state.user.id, key: 'properties', data: localProps(), updated_at: new Date().toISOString() }, { onConflict: 'user_id,key' }); }
    catch (e) { console.warn('[LifePlatform] push:', e.message); }
  }
  function pushDebounced() { clearTimeout(pushT); pushT = setTimeout(push, 1200); }

  function isPro() {
    if (state.plan !== 'pro') return false;
    if (state.planExp && Date.now() > new Date(state.planExp).getTime()) return false;
    return true;
  }
  async function redeem(code) {
    if (!state.sb || !state.user) throw new Error('Inicia sesión (Supabase) para activar una licencia.');
    var r = await state.sb.rpc('redeem_license', { p_code: (code || '').trim() });
    if (r.error) throw new Error(r.error.message);
    if (r.data !== 'ok') throw new Error('Licencia inválida o ya usada.');
    await refreshPlan();
    return true;
  }

  window.LifePlatform = {
    ready: readyP,
    isLogged: function () { return !!state.user; },
    userId: function () { return state.user ? state.user.id : null; },
    email: function () { return state.user ? state.user.email : null; },
    projectsKey: projectsKey,
    pull: pull, push: push, pushDebounced: pushDebounced,
    plan: function () { return isPro() ? 'pro' : 'free'; },
    isPro: isPro, refreshPlan: refreshPlan, redeem: redeem,
    supabase: function () { return state.sb; }
  };
  init();
})();

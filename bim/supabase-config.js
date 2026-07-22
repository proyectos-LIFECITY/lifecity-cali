/* ============================================================
   LifeCity · Configuración de Supabase Auth
   ------------------------------------------------------------
   1. Crea un proyecto gratis en https://supabase.com
   2. Ve a: Project Settings → API
   3. Copia "Project URL" y "anon public" key y pégalas abajo.
   4. (Auth) En Authentication → Providers → Email: deja "Email"
      habilitado. Si quieres entrar sin confirmar correo, apaga
      "Confirm email" en Authentication → Sign In / Providers.

   Si dejas los dos campos vacíos, el login funciona en MODO LOCAL
   (cuentas guardadas solo en este navegador, útil para demo).
   ============================================================ */
window.SUPABASE_CONFIG = {
  // URL BASE del proyecto (sin /rest/v1). createClient la necesita así.
  url: 'https://dwqqgfieeuxnqhjkeags.supabase.co',
  anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImR3cXFnZmllZXV4bnFoamtlYWdzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODI5NDY0ODcsImV4cCI6MjA5ODUyMjQ4N30.SobIM_8AyvZsU9tY3XtDC89fxNXvl3v6fJghLEIo3xU'
};

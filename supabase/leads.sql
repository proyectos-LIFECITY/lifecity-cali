-- ============================================================
-- LifeCity · Tabla de LEADS (registros del login)
-- Ejecuta esto UNA vez en: Supabase → SQL Editor → New query → Run
-- ============================================================

create table if not exists public.leads (
  id          uuid primary key default gen_random_uuid(),
  created_at  timestamptz not null default now(),
  name        text,
  email       text,
  source      text default 'signup',
  user_agent  text
);

-- Seguridad a nivel de fila
alter table public.leads enable row level security;

-- Permite que el formulario (anon) y usuarios autenticados INSERTEN leads.
-- No se da SELECT a anon: los leads los ves desde el Dashboard (Table Editor),
-- que usa la service_role y no está sujeta a estas políticas.
drop policy if exists "leads_insert_anon" on public.leads;
create policy "leads_insert_anon"
  on public.leads
  for insert
  to anon, authenticated
  with check (true);

-- (Opcional) índice para buscar por correo
create index if not exists leads_email_idx on public.leads (email);

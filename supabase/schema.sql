-- ============================================================
-- LifeCity · Esquema (usuarios + proyectos por usuario + licencias)
-- Ejecutar UNA vez en: Supabase -> SQL Editor -> Run
-- ============================================================

-- 1) Perfil / plan por usuario -------------------------------
create table if not exists public.profiles (
  id           uuid primary key references auth.users(id) on delete cascade,
  email        text,
  plan         text not null default 'free',   -- 'free' | 'pro'
  plan_expires timestamptz,
  created_at   timestamptz default now()
);
alter table public.profiles enable row level security;
drop policy if exists profiles_self on public.profiles;
create policy profiles_self on public.profiles
  for all to authenticated using (id = auth.uid()) with check (id = auth.uid());

-- Crea el perfil automaticamente al registrarse
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles(id, email, plan) values (new.id, new.email, 'free')
  on conflict (id) do nothing;
  return new;
end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- 2) Estado por usuario (proyectos, estudios, etc.) ----------
create table if not exists public.user_state (
  user_id    uuid not null default auth.uid() references auth.users(id) on delete cascade,
  key        text not null,                    -- 'properties' | 'studies' | ...
  data       jsonb not null,
  updated_at timestamptz default now(),
  primary key (user_id, key)
);
alter table public.user_state enable row level security;
drop policy if exists user_state_own on public.user_state;
create policy user_state_own on public.user_state
  for all to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

-- 3) Licencias PRO (redimibles) ------------------------------
create table if not exists public.license_keys (
  code    text primary key,
  plan    text not null default 'pro',
  months  int  not null default 12,
  used_by uuid,
  used_at timestamptz
);
alter table public.license_keys enable row level security;  -- sin policies: nadie las lee directo; solo la RPC (security definer)

create or replace function public.redeem_license(p_code text)
returns text language plpgsql security definer as $$
declare k record;
begin
  select * into k from public.license_keys where code = p_code and used_by is null for update;
  if not found then return 'invalid'; end if;
  update public.license_keys set used_by = auth.uid(), used_at = now() where code = p_code;
  insert into public.profiles(id, plan, plan_expires)
    values (auth.uid(), k.plan, now() + make_interval(months => k.months))
    on conflict (id) do update set plan = excluded.plan, plan_expires = excluded.plan_expires;
  return 'ok';
end $$;
grant execute on function public.redeem_license(text) to authenticated;

-- 4) (Ejemplo) crea unas licencias PRO para vender/entregar ---
-- insert into public.license_keys(code, plan, months) values
--   ('LIFECITY-PRO-2026-AB12', 'pro', 12),
--   ('LIFECITY-PRO-2026-CD34', 'pro', 12)
-- on conflict do nothing;

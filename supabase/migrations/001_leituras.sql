-- Estrutura do banco: leituras enviadas pelo ESP32 (via EMQX -> API)
create table if not exists public.leituras (
  id          bigint generated always as identity primary key,
  device_id   text        not null,
  grandeza    text        not null,            -- ex.: 'peso'
  valor       double precision not null,
  unidade     text        not null,            -- ex.: 'g'
  alerta      boolean     not null default false,
  recebido_em timestamptz not null default now()
);

create index if not exists leituras_dev_gr_tempo
  on public.leituras (device_id, grandeza, recebido_em desc);

-- Somente a Edge Function (service role) acessa a tabela.
alter table public.leituras enable row level security;

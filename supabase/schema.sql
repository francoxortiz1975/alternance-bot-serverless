-- Páginas de carreras de empresas a monitorear
create table sources (
  id serial primary key,
  name text not null,
  url text not null unique,
  active boolean not null default true,
  last_scraped_at timestamptz
);

-- Ofertas scrapeadas (filtro por palabras clave). El análisis Gemini (analysis/score_global)
-- se rellena de forma diferida, solo cuando el usuario elige la oferta desde el bot.
create table offers (
  id serial primary key,
  source_id integer references sources(id),
  offer_url text not null unique,
  title text,
  location text,
  raw_text text,
  analysis jsonb,
  score_global numeric,
  status text not null default 'new',  -- new | presented | applied | discarded | incompatible
  scraped_at timestamptz not null default now()
);

create index offers_status_scraped_idx on offers (status, scraped_at desc);

-- Estado de conversación por chat de Telegram
create table conversation_state (
  chat_id bigint primary key,
  state text not null default 'idle',  -- idle | awaiting_confirmation | awaiting_selection
  context jsonb,
  updated_at timestamptz not null default now()
);

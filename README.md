# alternance-bot-serverless

Bot de Telegram 100% serverless para automatizar candidaturas de alternance:

- **Vercel** (función Python) → recibe el webhook de Telegram, analiza ofertas, genera carta DOCX→PDF y envía documentos.
- **Supabase** (Postgres) → guarda ofertas scrapeadas/analizadas + estado de la conversación.
- **GitHub Actions** (cron cada 6h) → scrapea páginas de carreras de empresas y analiza nuevas ofertas.
- **Jina Reader** → obtiene el texto de páginas web (sustituye a Playwright).
- **Gemini API** → análisis y scoring de cada oferta.
- **CloudConvert** → convierte la carta DOCX generada a PDF.
- **Telegram Bot API** → vía HTTP directo, sin librerías.

Costo: **$0** (todos los servicios usados están en su free tier, sin tarjeta de crédito).

## Flujos del bot

1. **Pegar una URL de oferta** → el bot la analiza con Gemini, muestra un resumen con score de compatibilidad y pregunta "¿Generar candidatura? o/n". Si respondes "o", genera la carta (PDF) + adjunta el CV correspondiente.
2. **Escribir "hola"** → el bot muestra hasta 15 ofertas ya scrapeadas (título, ubicación y enlace — sin análisis todavía). Respondes con un número para que el bot analice *esa* oferta con Gemini (al instante, no antes) y te muestre el detalle completo + "¿Generar candidatura? o/n". Después de cada candidatura generada o descartada, el bot pregunta "¿quieres ver otra oferta?" — puedes seguir eligiendo números de la lista o responder "no"/"listo" para terminar.
3. **`/add <url>`** → agrega una página de carreras de empresa a la tabla `sources`, para que el cron la incluya en el próximo scraping (el nombre de la fuente se deriva automáticamente del dominio).

El cron de GitHub Actions alimenta el flujo 2: scrapea periódicamente las páginas configuradas en la tabla `sources` **usando solo filtros de texto** (palabras clave del puesto + localización), sin llamar a Gemini. Guarda título, ubicación y enlace de cada oferta que matchea. El análisis Gemini (compatibilidad, score, carta) se hace de forma diferida, solo cuando eliges una oferta desde el bot o pegas una URL directamente.

### Sobre los límites de la API de Gemini

Con este diseño, Gemini **no** se llama durante el scraping (que puede encontrar docenas de ofertas cada 6h) — solo se llama on-demand, 1 vez por oferta que realmente revises desde el bot (pegando su URL, o eligiéndola de la lista de "hola"; el resultado se guarda en `offers.analysis` así que no se reanaliza si la vuelves a abrir). En la práctica eso son como máximo unas pocas requests por sesión de uso, muy por debajo de los límites free tier de `gemini-2.5-flash`/`gemini-2.0-flash` (decenas de requests por minuto y cientos-1500 por día).

## Setup paso a paso

### 1. Supabase

1. Crea un proyecto gratis en [supabase.com](https://supabase.com).
2. Ve al **SQL Editor** y ejecuta el contenido de [`supabase/schema.sql`](supabase/schema.sql).
3. (Opcional) edita y ejecuta [`supabase/seed_sources.sql`](supabase/seed_sources.sql) para añadir las páginas de carreras de empresas que quieres monitorear.
4. En **Project Settings → API**, copia:
   - `Project URL` → `SUPABASE_URL`
   - `service_role` key → `SUPABASE_SERVICE_KEY` (¡no la `anon` key! necesitas el service role para que el bot pueda escribir sin RLS)

### 2. Jina Reader (opcional pero recomendado)

Crea una cuenta gratis en [jina.ai](https://jina.ai) y copia tu API key → `JINA_API_KEY`. Sin key, Jina Reader funciona igual pero con límites de tasa más bajos.

### 3. CloudConvert

Crea una cuenta gratis en [cloudconvert.com](https://cloudconvert.com/dashboard/api/v2/keys) y genera una API key → `CLOUDCONVERT_API_KEY`. Free tier: 25 conversiones/día.

### 4. Gemini API

Reutiliza tu key existente de [aistudio.google.com](https://aistudio.google.com) → `GEMINI_API_KEY`.

### 5. Telegram

- Reutiliza el token de tu bot (`@BotFather`) → `TELEGRAM_BOT_TOKEN`.
- Define un secreto random para `TELEGRAM_WEBHOOK_SECRET` (cualquier string largo, ej: `openssl rand -hex 24`).
- Obtén tu `chat_id` para `ALLOWED_CHAT_ID`: manda cualquier mensaje a tu bot y luego visita
  `https://api.telegram.org/bot<TOKEN>/getUpdates` — busca `"chat":{"id": ...}`.

### 6. Deploy en Vercel

```bash
npm i -g vercel
cd alternance-bot-serverless
vercel
```

En el dashboard de Vercel (Project Settings → Environment Variables), añade todas las variables de [`.env.example`](.env.example):

```
TELEGRAM_BOT_TOKEN
TELEGRAM_WEBHOOK_SECRET
ALLOWED_CHAT_ID
GEMINI_API_KEY
JINA_API_KEY
CLOUDCONVERT_API_KEY
SUPABASE_URL
SUPABASE_SERVICE_KEY
```

Luego `vercel --prod` para desplegar a producción.

### 7. Registrar el webhook de Telegram

```bash
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=https://<tu-deploy>.vercel.app/api/webhook&secret_token=<TELEGRAM_WEBHOOK_SECRET>"
```

Verifica con `https://api.telegram.org/bot<TOKEN>/getWebhookInfo`.

### 8. GitHub Actions (scraping periódico)

1. Sube este repo a GitHub.
2. En **Settings → Secrets and variables → Actions**, añade:
   - `GEMINI_API_KEY`
   - `JINA_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
3. El workflow [`scrape.yml`](.github/workflows/scrape.yml) corre cada 6h automáticamente. Puedes lanzarlo manualmente desde la pestaña **Actions → Scrape job offers → Run workflow**.

### 9. Añadir fuentes a monitorear

Inserta filas en la tabla `sources` (vía Supabase dashboard o SQL):

```sql
insert into sources (name, url) values
  ('Mi Empresa - Alternance', 'https://empresa.com/carreras?contrato=alternance');
```

## Desarrollo local

```bash
pip install -r requirements.txt
cp .env.example .env  # y completa las keys
```

- `python -c "from lib.jina_client import fetch_texto_pagina; print(fetch_texto_pagina('https://...')[:500])"` — probar scraping.
- `python scripts/scrape_offers.py` — correr el scraper manualmente.
- `vercel dev` — correr el webhook localmente (simula con `curl` mandando un update de Telegram al endpoint `/api/webhook`).

-- Páginas de carreras de empresas a monitorear (scraping cada 6h).
-- Descomenta y ejecuta esto en el SQL editor de Supabase, o inserta filas
-- desde el dashboard de Supabase (tabla "sources").

-- ── GRUPO A: Validadas con Jina Reader ✅ ──────────────────────────────────────
-- Estas URLs exponen los títulos de las ofertas como texto de links estáticos.
-- Listas para activar.

-- insert into sources (name, url) values
--   ('AXA - Data & Tech',         'https://recrutement.axa.fr/data-science'),
--   ('Thales - Alternance Data',   'https://careers.thalesgroup.com/fr/fr/search-results?keywords=alternance%20data'),
--   ('Capgemini - Offres',         'https://www.capgemini.com/fr-fr/carrieres/rejoignez-nous/nos-offres-demploi/?keywords=alternance%20data'),
--   ('Doctolib - Engineering',     'https://job-boards.greenhouse.io/doctolib'),
--   ('BNP Paribas - Offres',       'https://group.bnpparibas/en/careers/all-job-offers?keyword=alternance+data'),
--   ('Orange - Apprentissage',     'https://orange.jobs/site/fr-apprentissage/index.htm'),
--   ('Sopra Steria - Offres',      'https://jobs.smartrecruiters.com/SopraSteria1')
-- on conflict (url) do nothing;


-- ── GRUPO B: SPA JavaScript — requieren Firecrawl ⚙️ ─────────────────────────
-- Estas URLs fallaban con Jina (página vacía). Con FIRECRAWL_API_KEY configurada
-- deberían funcionar. Probar una a una antes de activar en masa.

-- insert into sources (name, url) values
--   ('Société Générale - Alternance',  'https://careers.societegenerale.com/fr/offres?contract=apprentissage'),
--   ('Crédit Agricole CIB',            'https://careers.ca-cib.com/fr/offres'),
--   ('BPCE - Offres',                  'https://carrieres.bpce.fr/offres'),
--   ('Natixis - Offres',               'https://carrieres.bpce.fr/offres?type=apprentissage'),
--   ('Amundi - Carrières',             'https://jobs.amundi.com/go/Toutes-les-offres/'),
--   ('La Banque Postale',              'https://carrieres.labanquepostale.fr/offres'),
--   ('Decathlon Tech',                 'https://www.decathlon.fr/landing/_/R-a-recrutement'),
--   ('ManoMano - Jobs',                'https://jobs.lever.co/manomano'),
--   ('L''Oréal - Tech',               'https://careers.loreal.com/fr_FR/jobs/SearchJobs/?6617=[3201862]'),
--   ('EDF - Alternance',               'https://edf.csod.com/ux/ats/careersite/1/home?c=edf'),
--   ('Air France - Carrières',         'https://careers.airfranceklm.com/fr_FR/jobs?type=apprentissage')
-- on conflict (url) do nothing;


-- ── GRUPO D: Portales propios — probar con Jina ❓ ────────────────────────────
-- Luxury / otras empresas con portales propios. Pueden ser estáticos (Jina OK)
-- o SPA (necesitarían Firecrawl). Probar antes de activar.

-- insert into sources (name, url) values
--   ('Hermès - Alternance',    'https://talents.hermes.com/fr/sites/CX/jobs?type=Alternance'),
--   ('Allianz France',         'https://careers.allianz.com/fr_FR/search?keywords=alternance&location=France')
-- on conflict (url) do nothing;


-- ── GRUPO C: No probadas aún ❓ ────────────────────────────────────────────────
-- FAANG/Big Tech — sus portales suelen ser SPA o requieren login corporativo.
-- Probar con Firecrawl.

-- insert into sources (name, url) values
--   ('IBM France - Alternance',        'https://www.ibm.com/fr-fr/employment/'),
--   ('Salesforce - Careers',           'https://careers.salesforce.com/en/jobs/?country=France&type=Intern'),
--   ('SAP - Alternance France',        'https://jobs.sap.com/go/Alternance-France/'),
--   ('ServiceNow - Jobs',              'https://careers.servicenow.com/careers/jobs?location=France'),
--   ('Oracle - Alternance',            'https://careers.oracle.com/jobs/#en/sites/jobsearch/jobs?location=France')
-- on conflict (url) do nothing;

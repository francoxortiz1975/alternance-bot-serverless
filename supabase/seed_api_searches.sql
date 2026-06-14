-- Ejemplo basado en la búsqueda de La Bonne Alternance:
-- Maintenance, installation et assistance informatique — Paris (30km), niveau Licence/BUT.
-- Descomenta y ajusta a tu gusto, o inserta filas desde el dashboard de Supabase.

-- insert into api_searches (name, romes, latitude, longitude, radius, target_diploma_level) values
--   ('Maintenance & assistance info - Paris',
--    'H1101,H1106,H1107,H1108,I1102,I1305,I1401,I1403,I1404,F1134,I1322,I1327,I1329,I1330,I1406,I1407,I1409,M1866,M1869,M1871,M1874',
--    48.859, 2.347, 30, '6');

-- Búsquedas adicionales por tipo de puesto (códigos ROME M18 — informatique/data),
-- alineadas con las categorías de type_cv. Paris (30km), niveau Licence/Master 1.
--
-- Nota : la API solo filtra por código ROME (no por título de puesto), y M1805
-- ("Études et développement informatique") es un código amplio que cubre Dev,
-- Data Engineer e Ingénieur IA a la vez — por eso varias búsquedas comparten
-- el mismo código ROME y pueden devolver ofertas solapadas (se deduplican por
-- offer_url al guardar, así que no es un problema).

-- insert into api_searches (name, romes, latitude, longitude, radius, target_diploma_level) values
--   ('Ingénieur Data - Paris', 'M1805,M1403', 48.859, 2.347, 30, '6'),
--   ('Ingénieur DevOps - Paris', 'M1801,M1802', 48.859, 2.347, 30, '6'),
--   ('Ingénieur IA - Paris', 'M1805,M1403', 48.859, 2.347, 30, '6'),
--   ('Développeur - Paris', 'M1805', 48.859, 2.347, 30, '6'),
--   ('Data Analyst - Paris', 'M1805,M1403', 48.859, 2.347, 30, '6');

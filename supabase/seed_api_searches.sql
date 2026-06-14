-- Ejemplo basado en la búsqueda de La Bonne Alternance:
-- Maintenance, installation et assistance informatique — Paris (30km), niveau Licence/BUT.
-- Descomenta y ajusta a tu gusto, o inserta filas desde el dashboard de Supabase.

-- insert into api_searches (name, romes, latitude, longitude, radius, target_diploma_level) values
--   ('Maintenance & assistance info - Paris',
--    'H1101,H1106,H1107,H1108,I1102,I1305,I1401,I1403,I1404,F1134,I1322,I1327,I1329,I1330,I1406,I1407,I1409,M1866,M1869,M1871,M1874',
--    48.859, 2.347, 30, '6');

-- Búsquedas adicionales por familia de métiers (códigos ROME M18 — informatique/data),
-- alineadas con las categorías de type_cv. Paris (30km), niveau Licence/Master 1.

-- Data_Engineer, Data_IA, Data_Scientist, Data_Analyst, Software_Engineer
-- insert into api_searches (name, romes, latitude, longitude, radius, target_diploma_level) values
--   ('Dev & Data - Paris', 'M1805,M1403', 48.859, 2.347, 30, '6');

-- DevOps (administration systèmes/réseaux, expertise & support)
-- insert into api_searches (name, romes, latitude, longitude, radius, target_diploma_level) values
--   ('DevOps & administration systèmes - Paris', 'M1801,M1802', 48.859, 2.347, 30, '6');

-- Chef_de_Projet, Business_Analyst, IT_Generalist (conseil, MOA, direction des SI)
-- insert into api_searches (name, romes, latitude, longitude, radius, target_diploma_level) values
--   ('Conseil, gestion de projet & BA - Paris', 'M1806,M1803', 48.859, 2.347, 30, '6');

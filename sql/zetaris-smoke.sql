-- PROPOSED ONLY: run in the authenticated Zetaris SQL Editor after installation.
-- This is not a SQLite/DuckDB substitute for Zetaris.
SELECT 1 AS one;
SHOW SERVER VERSION;
SHOW LIGHTNING DATABASES;
-- Run only after discovery confirms access to NY_TAXI:
SHOW LIGHTNING TABLES NY_TAXI;
SELECT * FROM NY_TAXI.taxi_zones LIMIT 5;

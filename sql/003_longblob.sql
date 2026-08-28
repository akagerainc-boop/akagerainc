-- ============================================================
--  Fix: images.data must be LONGBLOB (SQLAlchemy LargeBinary maps to
--  plain BLOB = 64 KB on MySQL, which rejects real images/PDFs with
--  (1406, "Data too long for column 'data'")).
--
--  Usage:  mysql -u USER -p YOUR_DB < 003_longblob.sql
-- ============================================================
ALTER TABLE images MODIFY COLUMN data LONGBLOB;

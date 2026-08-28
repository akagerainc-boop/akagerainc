-- ============================================================
--  Akagera Inc — in-place upgrade for an EXISTING database
--  (adds Phase-1 columns + new tables without touching data)
--
--  Usage:  mysql -u USER -p YOUR_DB_NAME < 001_migrate_existing.sql
--
--  Safe to run more than once. New tables are created by the app on
--  startup (SQLAlchemy create_all) too — this script is for teams that
--  apply schema changes manually / in CI.
-- ============================================================

DELIMITER $$

DROP PROCEDURE IF EXISTS akg_add_col $$
CREATE PROCEDURE akg_add_col(IN tbl VARCHAR(64), IN col VARCHAR(64), IN ddl TEXT)
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = tbl AND COLUMN_NAME = col
  ) THEN
    SET @s = CONCAT('ALTER TABLE `', tbl, '` ADD COLUMN `', col, '` ', ddl);
    PREPARE st FROM @s; EXECUTE st; DEALLOCATE PREPARE st;
  END IF;
END $$

DELIMITER ;

-- ---------- users ----------
CALL akg_add_col('users', 'password_hash',  'VARCHAR(255) NULL');
CALL akg_add_col('users', 'role',           "VARCHAR(40) NOT NULL DEFAULT 'customer'");
CALL akg_add_col('users', 'phone',          'VARCHAR(50) NULL');
CALL akg_add_col('users', 'company',        'VARCHAR(255) NULL');
CALL akg_add_col('users', 'country',        'VARCHAR(100) NULL');
CALL akg_add_col('users', 'email_verified', 'TINYINT(1) DEFAULT 0');
CALL akg_add_col('users', 'is_active',      'TINYINT(1) DEFAULT 1');
CALL akg_add_col('users', 'provider',       "VARCHAR(40) DEFAULT 'password'");
CALL akg_add_col('users', 'last_login_at',  'DATETIME NULL');

-- ---------- apps (products) ----------
CALL akg_add_col('apps', 'slug',                 'VARCHAR(255) NULL');
CALL akg_add_col('apps', 'category',             'VARCHAR(100) NULL');
CALL akg_add_col('apps', 'status',               "VARCHAR(30) DEFAULT 'published'");
CALL akg_add_col('apps', 'version',              'VARCHAR(50) NULL');
CALL akg_add_col('apps', 'release_date',         'DATE NULL');
CALL akg_add_col('apps', 'platforms',            'JSON NULL');
CALL akg_add_col('apps', 'pricing_model',        "VARCHAR(30) DEFAULT 'free'");
CALL akg_add_col('apps', 'price',                'DECIMAL(10,2) DEFAULT 0');
CALL akg_add_col('apps', 'subscription_options', 'JSON NULL');
CALL akg_add_col('apps', 'play_store_url',       'VARCHAR(500) NULL');
CALL akg_add_col('apps', 'app_store_url',        'VARCHAR(500) NULL');
CALL akg_add_col('apps', 'website_url',          'VARCHAR(500) NULL');
CALL akg_add_col('apps', 'documentation_url',    'VARCHAR(500) NULL');
CALL akg_add_col('apps', 'screenshots',          'JSON NULL');
CALL akg_add_col('apps', 'is_featured',          'TINYINT(1) DEFAULT 0');
CALL akg_add_col('apps', 'sort_order',           'INT DEFAULT 0');

-- ---------- services ----------
CALL akg_add_col('services', 'slug',                          'VARCHAR(255) NULL');
CALL akg_add_col('services', 'short_description',             'VARCHAR(500) NULL');
CALL akg_add_col('services', 'currency',                      "VARCHAR(8) DEFAULT 'USD'");
CALL akg_add_col('services', 'category',                      'VARCHAR(100) NULL');
CALL akg_add_col('services', 'duration_value',                'INT NULL');
CALL akg_add_col('services', 'duration_unit',                 'VARCHAR(20) NULL');
CALL akg_add_col('services', 'duration_label',                'VARCHAR(120) NULL');
CALL akg_add_col('services', 'features',                      'JSON NULL');
CALL akg_add_col('services', 'requirements',                  'JSON NULL');
CALL akg_add_col('services', 'process_steps',                 'JSON NULL');
CALL akg_add_col('services', 'faqs',                          'JSON NULL');
CALL akg_add_col('services', 'terms',                         'TEXT NULL');
CALL akg_add_col('services', 'delivery_method',               'VARCHAR(120) NULL');
CALL akg_add_col('services', 'status',                        "VARCHAR(30) DEFAULT 'published'");
CALL akg_add_col('services', 'availability',                  "VARCHAR(30) DEFAULT 'available'");
CALL akg_add_col('services', 'is_featured',                   'TINYINT(1) DEFAULT 0');
CALL akg_add_col('services', 'popular',                       'TINYINT(1) DEFAULT 0');
CALL akg_add_col('services', 'sort_order',                    'INT DEFAULT 0');
CALL akg_add_col('services', 'grants_business_portal_access', 'TINYINT(1) NOT NULL DEFAULT 0');
CALL akg_add_col('services', 'portal_business_name',          'VARCHAR(255) NULL');
CALL akg_add_col('services', 'portal_category',               'VARCHAR(100) NULL');
CALL akg_add_col('services', 'portal_access_duration_days',   'INT DEFAULT 365');

-- ---------- payments ----------
CALL akg_add_col('payments', 'order_id',      'INT NULL');
CALL akg_add_col('payments', 'provider',      'VARCHAR(40) NULL');
CALL akg_add_col('payments', 'provider_ref',  'VARCHAR(255) NULL');
CALL akg_add_col('payments', 'refunded_at',   'DATETIME NULL');

-- ---------- licenses ----------
CALL akg_add_col('licenses', 'product_id',   'INT NULL');
CALL akg_add_col('licenses', 'license_type', "VARCHAR(30) DEFAULT 'annual'");
CALL akg_add_col('licenses', 'status',       "VARCHAR(30) DEFAULT 'active'");
CALL akg_add_col('licenses', 'max_devices',  'INT DEFAULT 1');
CALL akg_add_col('licenses', 'starts_at',    'DATETIME NULL');

-- ---------- contact_messages ----------
CALL akg_add_col('contact_messages', 'company',      'VARCHAR(255) NULL');
CALL akg_add_col('contact_messages', 'subject',      'VARCHAR(255) NULL');
CALL akg_add_col('contact_messages', 'inquiry_type', 'VARCHAR(60) NULL');

-- ---------- backfill ----------
UPDATE apps      SET slug = LOWER(REPLACE(REPLACE(REPLACE(name,' ','-'),'.',''),'/','-')) WHERE slug IS NULL OR slug = '';
UPDATE services  SET slug = LOWER(REPLACE(REPLACE(REPLACE(name,' ','-'),'.',''),'/','-')) WHERE slug IS NULL OR slug = '';
UPDATE apps      SET status = 'published' WHERE status IS NULL;
UPDATE services  SET status = 'published' WHERE status IS NULL;
UPDATE users     SET role = 'customer'   WHERE role IS NULL OR role = '';
UPDATE licenses  SET status = 'active', is_active = 1 WHERE status IS NULL;

DROP PROCEDURE IF EXISTS akg_add_col;

-- ---------- new tables ----------
--  The application creates every new table automatically on boot
--  (SQLAlchemy Base.metadata.create_all). To create them by hand,
--  run the CREATE TABLE statements for the following from
--  akagerainc_schema.sql:
--    downloads, orders, order_items, invoices, subscriptions,
--    license_activations, support_tickets, ticket_messages,
--    blog_posts, categories, doc_pages, faqs, testimonials,
--    case_studies, industries, internships, internship_applications,
--    job_positions, job_applications, notifications,
--    navigation_items, audit_logs, service_fields

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
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  actor_email VARCHAR(255), 
  action VARCHAR(80), 
  entity VARCHAR(80), 
  entity_id VARCHAR(80), 
  meta JSON, 
  ip VARCHAR(80), 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id),
  KEY `ix_audit_logs_actor_email` (`actor_email`),
  KEY `ix_audit_logs_entity` (`entity`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS blog_posts (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  slug VARCHAR(220) NOT NULL, 
  title VARCHAR(255) NOT NULL, 
  excerpt VARCHAR(500), 
  body TEXT, 
  cover_image VARCHAR(500), 
  author VARCHAR(120), 
  category VARCHAR(100), 
  tags JSON, 
  status VARCHAR(30), 
  reading_time INTEGER, 
  is_featured BOOL, 
  published_at DATETIME, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id),
  UNIQUE KEY `ix_blog_posts_slug` (`slug`),
  KEY `ix_blog_posts_category` (`category`),
  KEY `ix_blog_posts_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS case_studies (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  slug VARCHAR(220) NOT NULL, 
  title VARCHAR(255) NOT NULL, 
  client VARCHAR(200), 
  category VARCHAR(100), 
  summary VARCHAR(500), 
  challenge TEXT, 
  solution TEXT, 
  results TEXT, 
  technologies JSON, 
  platforms JSON, 
  screenshots JSON, 
  cover_image VARCHAR(500), 
  link VARCHAR(500), 
  is_featured BOOL, 
  status VARCHAR(30), 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id),
  UNIQUE KEY `ix_case_studies_slug` (`slug`),
  KEY `ix_case_studies_category` (`category`),
  KEY `ix_case_studies_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS categories (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  kind VARCHAR(30), 
  name VARCHAR(120) NOT NULL, 
  slug VARCHAR(140), 
  sort_order INTEGER, 
  is_active BOOL, 
  PRIMARY KEY (id),
  KEY `ix_categories_kind` (`kind`),
  KEY `ix_categories_slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS doc_pages (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  slug VARCHAR(220) NOT NULL, 
  section VARCHAR(120), 
  title VARCHAR(255) NOT NULL, 
  body TEXT, 
  sort_order INTEGER, 
  is_published BOOL, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id),
  UNIQUE KEY `ix_doc_pages_slug` (`slug`),
  KEY `ix_doc_pages_section` (`section`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS faqs (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  category VARCHAR(100), 
  question VARCHAR(400) NOT NULL, 
  answer TEXT NOT NULL, 
  sort_order INTEGER, 
  is_active BOOL, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id),
  KEY `ix_faqs_category` (`category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS industries (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  slug VARCHAR(160) NOT NULL, 
  name VARCHAR(160) NOT NULL, 
  icon VARCHAR(80), 
  summary VARCHAR(500), 
  body TEXT, 
  is_active BOOL, 
  sort_order INTEGER, 
  PRIMARY KEY (id),
  UNIQUE KEY `ix_industries_slug` (`slug`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS internships (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  slug VARCHAR(200) NOT NULL, 
  title VARCHAR(255) NOT NULL, 
  department VARCHAR(120), 
  description TEXT, 
  requirements JSON, 
  duration_label VARCHAR(120), 
  start_date DATE, 
  end_date DATE, 
  price NUMERIC(10, 2), 
  is_free BOOL, 
  positions INTEGER, 
  deadline DATE, 
  status VARCHAR(30), 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id),
  UNIQUE KEY `ix_internships_slug` (`slug`),
  KEY `ix_internships_department` (`department`),
  KEY `ix_internships_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS job_positions (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  slug VARCHAR(200) NOT NULL, 
  title VARCHAR(255) NOT NULL, 
  department VARCHAR(120), 
  location VARCHAR(160), 
  employment_type VARCHAR(60), 
  description TEXT, 
  responsibilities JSON, 
  requirements JSON, 
  benefits JSON, 
  status VARCHAR(30), 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id),
  UNIQUE KEY `ix_job_positions_slug` (`slug`),
  KEY `ix_job_positions_department` (`department`),
  KEY `ix_job_positions_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS navigation_items (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  parent_id INTEGER, 
  location VARCHAR(30), 
  label VARCHAR(120) NOT NULL, 
  url VARCHAR(300), 
  column_group VARCHAR(80), 
  sort_order INTEGER, 
  is_enabled BOOL, 
  PRIMARY KEY (id), 
  FOREIGN KEY(parent_id) REFERENCES navigation_items (id) ON DELETE CASCADE,
  KEY `ix_navigation_items_parent_id` (`parent_id`),
  KEY `ix_navigation_items_location` (`location`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS otp_codes (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  email VARCHAR(255) NOT NULL, 
  code_hash VARCHAR(255) NOT NULL, 
  purpose VARCHAR(30), 
  attempts INTEGER, 
  consumed BOOL, 
  expires_at DATETIME NOT NULL, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id),
  KEY `ix_otp_codes_email` (`email`),
  KEY `ix_otp_codes_purpose` (`purpose`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS testimonials (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  name VARCHAR(160) NOT NULL, 
  `role` VARCHAR(160), 
  company VARCHAR(160), 
  quote TEXT NOT NULL, 
  avatar VARCHAR(500), 
  rating INTEGER, 
  is_active BOOL, 
  sort_order INTEGER, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS downloads (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  product_id INTEGER, 
  platform VARCHAR(30), 
  label VARCHAR(120), 
  file_path VARCHAR(500), 
  external_url VARCHAR(500), 
  version VARCHAR(50), 
  architecture VARCHAR(50), 
  file_size VARCHAR(50), 
  min_os VARCHAR(80), 
  release_notes TEXT, 
  is_active BOOL, 
  released_at DATE, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(product_id) REFERENCES apps (id) ON DELETE CASCADE,
  KEY `ix_downloads_product_id` (`product_id`),
  KEY `ix_downloads_platform` (`platform`),
  KEY `ix_downloads_product_platform` (`product_id`, `platform`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS internship_applications (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  internship_id INTEGER, 
  full_name VARCHAR(200) NOT NULL, 
  email VARCHAR(255) NOT NULL, 
  phone VARCHAR(50), 
  education VARCHAR(300), 
  interest_area VARCHAR(160), 
  cv_path VARCHAR(500), 
  preferred_duration VARCHAR(120), 
  start_date DATE, 
  message TEXT, 
  status VARCHAR(30), 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(internship_id) REFERENCES internships (id) ON DELETE CASCADE,
  KEY `ix_internship_applications_internship_id` (`internship_id`),
  KEY `ix_internship_applications_email` (`email`),
  KEY `ix_internship_applications_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS job_applications (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  job_id INTEGER, 
  full_name VARCHAR(200) NOT NULL, 
  email VARCHAR(255) NOT NULL, 
  phone VARCHAR(50), 
  resume_path VARCHAR(500), 
  cover_letter TEXT, 
  status VARCHAR(30), 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(job_id) REFERENCES job_positions (id) ON DELETE CASCADE,
  KEY `ix_job_applications_job_id` (`job_id`),
  KEY `ix_job_applications_email` (`email`),
  KEY `ix_job_applications_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  user_id INTEGER, 
  type VARCHAR(60), 
  title VARCHAR(255), 
  body TEXT, 
  link VARCHAR(500), 
  is_read BOOL, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
  KEY `ix_notifications_user_id` (`user_id`),
  KEY `ix_notifications_is_read` (`is_read`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  order_ref VARCHAR(40) NOT NULL, 
  user_id INTEGER, 
  status VARCHAR(30), 
  subtotal NUMERIC(10, 2), 
  total NUMERIC(10, 2), 
  currency VARCHAR(8), 
  notes TEXT, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
  UNIQUE KEY `ix_orders_order_ref` (`order_ref`),
  KEY `ix_orders_user_id` (`user_id`),
  KEY `ix_orders_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS service_fields (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  service_id INTEGER, 
  label VARCHAR(200) NOT NULL, 
  field_key VARCHAR(100) NOT NULL, 
  field_type VARCHAR(30), 
  options JSON, 
  required BOOL, 
  help_text VARCHAR(300), 
  sort_order INTEGER, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(service_id) REFERENCES services (id) ON DELETE CASCADE,
  KEY `ix_service_fields_service_id` (`service_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS subscriptions (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  user_id INTEGER, 
  item_type VARCHAR(20), 
  ref_id INTEGER, 
  plan_name VARCHAR(120), 
  price NUMERIC(10, 2), 
  currency VARCHAR(8), 
  billing_period VARCHAR(20), 
  status VARCHAR(30), 
  start_date DATETIME DEFAULT CURRENT_TIMESTAMP, 
  renewal_date DATETIME, 
  expires_at DATETIME, 
  cancelled_at DATETIME, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
  KEY `ix_subscriptions_user_id` (`user_id`),
  KEY `ix_subscriptions_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS support_tickets (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  ticket_ref VARCHAR(40) NOT NULL, 
  user_id INTEGER, 
  email VARCHAR(255), 
  name VARCHAR(255), 
  subject VARCHAR(255) NOT NULL, 
  category VARCHAR(80), 
  priority VARCHAR(20), 
  status VARCHAR(30), 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL,
  UNIQUE KEY `ix_support_tickets_ticket_ref` (`ticket_ref`),
  KEY `ix_support_tickets_user_id` (`user_id`),
  KEY `ix_support_tickets_email` (`email`),
  KEY `ix_support_tickets_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS invoices (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  invoice_ref VARCHAR(40) NOT NULL, 
  order_id INTEGER, 
  user_id INTEGER, 
  amount NUMERIC(10, 2), 
  currency VARCHAR(8), 
  pdf_path VARCHAR(500), 
  issued_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, 
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
  UNIQUE KEY `ix_invoices_invoice_ref` (`invoice_ref`),
  KEY `ix_invoices_order_id` (`order_id`),
  KEY `ix_invoices_user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS license_activations (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  license_id INTEGER, 
  device_id VARCHAR(255), 
  device_name VARCHAR(255), 
  is_active BOOL, 
  activated_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(license_id) REFERENCES licenses (id) ON DELETE CASCADE,
  KEY `ix_license_activations_license_id` (`license_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS order_items (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  order_id INTEGER, 
  item_type VARCHAR(20), 
  ref_id INTEGER, 
  name VARCHAR(255), 
  unit_amount NUMERIC(10, 2), 
  quantity INTEGER, 
  duration_label VARCHAR(120), 
  form_data JSON, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE,
  KEY `ix_order_items_order_id` (`order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ticket_messages (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  ticket_id INTEGER, 
  sender VARCHAR(20), 
  body TEXT NOT NULL, 
  attachment_path VARCHAR(500), 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(ticket_id) REFERENCES support_tickets (id) ON DELETE CASCADE,
  KEY `ix_ticket_messages_ticket_id` (`ticket_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

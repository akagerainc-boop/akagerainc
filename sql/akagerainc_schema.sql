-- ============================================================
--  Akagera Inc - full MySQL 8 schema  (Phase 1)
--  Fresh install:  mysql -u USER -p < akagerainc_schema.sql
--  Then seed:      python seed.py     (creates admin + demo content)
-- ============================================================
CREATE DATABASE IF NOT EXISTS akagerainc CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE akagerainc;
SET FOREIGN_KEY_CHECKS = 0;


CREATE TABLE IF NOT EXISTS apps (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  name VARCHAR(255) NOT NULL, 
  slug VARCHAR(255), 
  description TEXT, 
  short_description VARCHAR(500), 
  features JSON, 
  how_it_works TEXT, 
  installation_steps JSON, 
  requires_license BOOL, 
  download_url VARCHAR(500), 
  app_icon VARCHAR(500), 
  app_logo VARCHAR(500), 
  app_image VARCHAR(500), 
  category VARCHAR(100), 
  status VARCHAR(30), 
  version VARCHAR(50), 
  release_date DATE, 
  platforms JSON, 
  pricing_model VARCHAR(30), 
  price NUMERIC(10, 2), 
  subscription_options JSON, 
  play_store_url VARCHAR(500), 
  app_store_url VARCHAR(500), 
  website_url VARCHAR(500), 
  documentation_url VARCHAR(500), 
  screenshots JSON, 
  is_featured BOOL, 
  sort_order INTEGER, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_apps_category ON apps (category);


CREATE UNIQUE INDEX ix_apps_slug ON apps (slug);

CREATE INDEX ix_apps_status ON apps (status);


CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  actor_email VARCHAR(255), 
  action VARCHAR(80), 
  entity VARCHAR(80), 
  entity_id VARCHAR(80), 
  meta JSON, 
  ip VARCHAR(80), 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_audit_logs_actor_email ON audit_logs (actor_email);

CREATE INDEX ix_audit_logs_entity ON audit_logs (entity);



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
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_blog_posts_category ON blog_posts (category);


CREATE UNIQUE INDEX ix_blog_posts_slug ON blog_posts (slug);

CREATE INDEX ix_blog_posts_status ON blog_posts (status);


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
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_case_studies_category ON case_studies (category);


CREATE UNIQUE INDEX ix_case_studies_slug ON case_studies (slug);

CREATE INDEX ix_case_studies_status ON case_studies (status);


CREATE TABLE IF NOT EXISTS categories (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  kind VARCHAR(30), 
  name VARCHAR(120) NOT NULL, 
  slug VARCHAR(140), 
  sort_order INTEGER, 
  is_active BOOL, 
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_categories_kind ON categories (kind);

CREATE INDEX ix_categories_slug ON categories (slug);


CREATE TABLE IF NOT EXISTS contact_messages (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  name VARCHAR(255) NOT NULL, 
  email VARCHAR(255) NOT NULL, 
  phone VARCHAR(50), 
  company VARCHAR(255), 
  subject VARCHAR(255), 
  inquiry_type VARCHAR(60), 
  service_required VARCHAR(255), 
  message TEXT NOT NULL, 
  status VARCHAR(50), 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_contact_messages_email ON contact_messages (email);


CREATE INDEX ix_contact_messages_status ON contact_messages (status);


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
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_doc_pages_section ON doc_pages (section);

CREATE UNIQUE INDEX ix_doc_pages_slug ON doc_pages (slug);


CREATE TABLE IF NOT EXISTS faqs (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  category VARCHAR(100), 
  question VARCHAR(400) NOT NULL, 
  answer TEXT NOT NULL, 
  sort_order INTEGER, 
  is_active BOOL, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_faqs_category ON faqs (category);



CREATE TABLE IF NOT EXISTS industries (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  slug VARCHAR(160) NOT NULL, 
  name VARCHAR(160) NOT NULL, 
  icon VARCHAR(80), 
  summary VARCHAR(500), 
  body TEXT, 
  is_active BOOL, 
  sort_order INTEGER, 
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE UNIQUE INDEX ix_industries_slug ON industries (slug);


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
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_internships_department ON internships (department);


CREATE UNIQUE INDEX ix_internships_slug ON internships (slug);

CREATE INDEX ix_internships_status ON internships (status);


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
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_job_positions_department ON job_positions (department);


CREATE UNIQUE INDEX ix_job_positions_slug ON job_positions (slug);

CREATE INDEX ix_job_positions_status ON job_positions (status);


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
  FOREIGN KEY(parent_id) REFERENCES navigation_items (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_navigation_items_location ON navigation_items (location);

CREATE INDEX ix_navigation_items_parent_id ON navigation_items (parent_id);


CREATE TABLE IF NOT EXISTS services (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  name VARCHAR(255) NOT NULL, 
  slug VARCHAR(255), 
  description TEXT, 
  short_description VARCHAR(500), 
  price NUMERIC(10, 2) NOT NULL, 
  currency VARCHAR(8), 
  icon VARCHAR(100), 
  image_url VARCHAR(500), 
  service_type VARCHAR(50), 
  category VARCHAR(100), 
  duration_value INTEGER, 
  duration_unit VARCHAR(20), 
  duration_label VARCHAR(120), 
  features JSON, 
  requirements JSON, 
  process_steps JSON, 
  faqs JSON, 
  terms TEXT, 
  delivery_method VARCHAR(120), 
  status VARCHAR(30), 
  availability VARCHAR(30), 
  is_featured BOOL, 
  popular BOOL, 
  sort_order INTEGER, 
  grants_business_portal_access BOOL NOT NULL, 
  portal_business_name VARCHAR(255), 
  portal_category VARCHAR(100), 
  portal_access_duration_days INTEGER, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_services_category ON services (category);


CREATE UNIQUE INDEX ix_services_slug ON services (slug);

CREATE INDEX ix_services_status ON services (status);


CREATE TABLE IF NOT EXISTS site_content (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  content_key VARCHAR(100) NOT NULL, 
  content_value JSON NOT NULL, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE UNIQUE INDEX ix_site_content_content_key ON site_content (content_key);



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



CREATE TABLE IF NOT EXISTS users (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  name VARCHAR(255) NOT NULL, 
  email VARCHAR(255) NOT NULL, 
  google_id VARCHAR(255), 
  profile_picture VARCHAR(500), 
  password_hash VARCHAR(255), 
  `role` VARCHAR(40), 
  phone VARCHAR(50), 
  company VARCHAR(255), 
  country VARCHAR(100), 
  email_verified BOOL, 
  is_active BOOL, 
  provider VARCHAR(40), 
  last_login_at DATETIME, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE UNIQUE INDEX ix_users_google_id ON users (google_id);


CREATE INDEX ix_users_role ON users (`role`);


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
  FOREIGN KEY(product_id) REFERENCES apps (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_downloads_platform ON downloads (platform);

CREATE INDEX ix_downloads_product_id ON downloads (product_id);

CREATE INDEX ix_downloads_product_platform ON downloads (product_id, platform);


CREATE TABLE IF NOT EXISTS images (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  url VARCHAR(500), 
  data BLOB, 
  filename VARCHAR(255), 
  mime_type VARCHAR(50), 
  alt_text VARCHAR(255), 
  page_type VARCHAR(50), 
  app_id INTEGER, 
  service_id INTEGER, 
  `order` INTEGER, 
  is_active BOOL, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(app_id) REFERENCES apps (id) ON DELETE CASCADE, 
  FOREIGN KEY(service_id) REFERENCES services (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_images_page_active ON images (page_type, is_active);

CREATE INDEX ix_images_page_type ON images (page_type);


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
  FOREIGN KEY(internship_id) REFERENCES internships (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_internship_applications_email ON internship_applications (email);


CREATE INDEX ix_internship_applications_internship_id ON internship_applications (internship_id);

CREATE INDEX ix_internship_applications_status ON internship_applications (status);


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
  FOREIGN KEY(job_id) REFERENCES job_positions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_job_applications_email ON job_applications (email);


CREATE INDEX ix_job_applications_job_id ON job_applications (job_id);

CREATE INDEX ix_job_applications_status ON job_applications (status);


CREATE TABLE IF NOT EXISTS licenses (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  user_id INTEGER NOT NULL, 
  license_key VARCHAR(40) NOT NULL, 
  service_id INTEGER, 
  app_id INTEGER, 
  product_id INTEGER, 
  license_type VARCHAR(30), 
  status VARCHAR(30), 
  max_devices INTEGER, 
  is_active BOOL, 
  starts_at DATETIME, 
  expires_at DATETIME, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
  FOREIGN KEY(service_id) REFERENCES services (id), 
  FOREIGN KEY(app_id) REFERENCES apps (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_licenses_is_active ON licenses (is_active);

CREATE UNIQUE INDEX ix_licenses_license_key ON licenses (license_key);

CREATE INDEX ix_licenses_status ON licenses (status);

CREATE INDEX ix_licenses_user_id ON licenses (user_id);


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
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_notifications_is_read ON notifications (is_read);

CREATE INDEX ix_notifications_user_id ON notifications (user_id);


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
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE UNIQUE INDEX ix_orders_order_ref ON orders (order_ref);

CREATE INDEX ix_orders_status ON orders (status);

CREATE INDEX ix_orders_user_id ON orders (user_id);


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
  FOREIGN KEY(service_id) REFERENCES services (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_service_fields_service_id ON service_fields (service_id);


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
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_subscriptions_status ON subscriptions (status);

CREATE INDEX ix_subscriptions_user_id ON subscriptions (user_id);


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
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_support_tickets_email ON support_tickets (email);


CREATE INDEX ix_support_tickets_status ON support_tickets (status);

CREATE UNIQUE INDEX ix_support_tickets_ticket_ref ON support_tickets (ticket_ref);

CREATE INDEX ix_support_tickets_user_id ON support_tickets (user_id);


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
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE UNIQUE INDEX ix_invoices_invoice_ref ON invoices (invoice_ref);

CREATE INDEX ix_invoices_order_id ON invoices (order_id);

CREATE INDEX ix_invoices_user_id ON invoices (user_id);


CREATE TABLE IF NOT EXISTS license_activations (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  license_id INTEGER, 
  device_id VARCHAR(255), 
  device_name VARCHAR(255), 
  is_active BOOL, 
  activated_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(license_id) REFERENCES licenses (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_license_activations_license_id ON license_activations (license_id);


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
  FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_order_items_order_id ON order_items (order_id);


CREATE TABLE IF NOT EXISTS payments (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  user_id INTEGER NOT NULL, 
  order_id INTEGER, 
  amount NUMERIC(10, 2) NOT NULL, 
  currency VARCHAR(3), 
  status VARCHAR(50), 
  payment_method VARCHAR(50), 
  provider VARCHAR(40), 
  provider_ref VARCHAR(255), 
  stripe_transaction_id VARCHAR(255), 
  paypal_order_id VARCHAR(255), 
  transaction_id VARCHAR(255), 
  service_id INTEGER, 
  refunded_at DATETIME, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
  FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE SET NULL, 
  UNIQUE (stripe_transaction_id), 
  UNIQUE (paypal_order_id), 
  FOREIGN KEY(service_id) REFERENCES services (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_payments_order_id ON payments (order_id);

CREATE INDEX ix_payments_status ON payments (status);


CREATE TABLE IF NOT EXISTS ticket_messages (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  ticket_id INTEGER, 
  sender VARCHAR(20), 
  body TEXT NOT NULL, 
  attachment_path VARCHAR(500), 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(ticket_id) REFERENCES support_tickets (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE INDEX ix_ticket_messages_ticket_id ON ticket_messages (ticket_id);


CREATE TABLE IF NOT EXISTS business_tokens (
  id INTEGER NOT NULL AUTO_INCREMENT, 
  user_id INTEGER, 
  service_id INTEGER, 
  payment_id INTEGER, 
  business_name VARCHAR(255) NOT NULL, 
  category VARCHAR(100) NOT NULL, 
  token VARCHAR(20) NOT NULL, 
  status VARCHAR(50), 
  expires_at DATETIME, 
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP, 
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
  PRIMARY KEY (id), 
  FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
  FOREIGN KEY(service_id) REFERENCES services (id), 
  FOREIGN KEY(payment_id) REFERENCES payments (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX ix_business_tokens_business_name ON business_tokens (business_name);

CREATE INDEX ix_business_tokens_category ON business_tokens (category);


CREATE INDEX ix_business_tokens_payment_id ON business_tokens (payment_id);

CREATE INDEX ix_business_tokens_service_id ON business_tokens (service_id);

CREATE INDEX ix_business_tokens_status ON business_tokens (status);

CREATE UNIQUE INDEX ix_business_tokens_token ON business_tokens (token);

CREATE INDEX ix_business_tokens_user_id ON business_tokens (user_id);

SET FOREIGN_KEY_CHECKS = 1;

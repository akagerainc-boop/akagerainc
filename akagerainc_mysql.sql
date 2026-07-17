CREATE DATABASE IF NOT EXISTS akagerainc
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE akagerainc;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  google_id VARCHAR(255) UNIQUE,
  profile_picture VARCHAR(500),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS apps (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  short_description VARCHAR(500),
  features JSON,
  how_it_works TEXT,
  installation_steps JSON,
  requires_license BOOLEAN DEFAULT FALSE,
  download_url VARCHAR(500),
  app_icon VARCHAR(500),
  app_logo VARCHAR(500),
  app_image VARCHAR(500),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS services (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  icon VARCHAR(100),
  image_url VARCHAR(500),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  status VARCHAR(50) DEFAULT 'pending',
  payment_method VARCHAR(50) DEFAULT 'paypal',
  stripe_transaction_id VARCHAR(255) UNIQUE,
  paypal_order_id VARCHAR(255) UNIQUE,
  service_id INT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_payments_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_payments_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS licenses (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  license_key VARCHAR(20) NOT NULL UNIQUE,
  service_id INT,
  app_id INT,
  is_active BOOLEAN DEFAULT TRUE,
  expires_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_licenses_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_licenses_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL,
  CONSTRAINT fk_licenses_app FOREIGN KEY (app_id) REFERENCES apps(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS images (
  id INT AUTO_INCREMENT PRIMARY KEY,
  url VARCHAR(500),
  data LONGBLOB,
  filename VARCHAR(255),
  mime_type VARCHAR(50) DEFAULT 'image/jpeg',
  alt_text VARCHAR(255),
  page_type VARCHAR(50),
  app_id INT,
  service_id INT,
  `order` INT DEFAULT 0,
  is_active BOOLEAN DEFAULT TRUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_images_app FOREIGN KEY (app_id) REFERENCES apps(id) ON DELETE CASCADE,
  CONSTRAINT fk_images_service FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contact_messages (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  phone VARCHAR(50),
  service_required VARCHAR(255),
  message TEXT NOT NULL,
  status VARCHAR(50) DEFAULT 'new',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS business_tokens (
  id INT AUTO_INCREMENT PRIMARY KEY,
  business_name VARCHAR(255) NOT NULL,
  category VARCHAR(100) NOT NULL,
  token VARCHAR(20) NOT NULL UNIQUE,
  status VARCHAR(50) DEFAULT 'active',
  expires_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS site_content (
  id INT AUTO_INCREMENT PRIMARY KEY,
  content_key VARCHAR(100) NOT NULL UNIQUE,
  content_value JSON NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT IGNORE INTO services (name, description, price, icon, image_url)
VALUES ('Website Development', 'Responsive business websites and portals', 250.00, 'globe', NULL);

INSERT IGNORE INTO apps (name, description, short_description, requires_license, download_url)
VALUES ('Akagera Business App', 'A secure mobile-first business companion for daily operations.', 'Business operations app', FALSE, 'https://example.com/akagera-app.apk');

INSERT INTO site_content (content_key, content_value)
VALUES (
  'pricing',
  JSON_ARRAY(
    JSON_OBJECT(
      'name', 'Starter',
      'price', '$250',
      'description', 'For small businesses that need a clear online presence and a reliable launch plan.',
      'features', JSON_ARRAY('Corporate website', 'Basic support', 'Contact form', 'Mobile friendly')
    ),
    JSON_OBJECT(
      'name', 'Professional',
      'price', '$850',
      'description', 'For growing companies that need a stronger digital platform and custom workflows.',
      'features', JSON_ARRAY('Custom web app', 'Marketplace setup', 'Admin tools', 'Priority support')
    ),
    JSON_OBJECT(
      'name', 'Enterprise',
      'price', 'Custom',
      'description', 'For large organizations that need private portals, advanced automation and dedicated support.',
      'features', JSON_ARRAY('Business portal', 'Advanced security', 'Dedicated delivery', 'API integration')
    )
  )
)
ON DUPLICATE KEY UPDATE content_value = VALUES(content_value), updated_at = CURRENT_TIMESTAMP;
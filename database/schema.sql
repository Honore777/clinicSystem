
CREATE DATABASE IF NOT EXISTS clinic_system CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
USE clinic_system;

SET SESSION sql_mode='STRICT_TRANS_TABLES';



CREATE TABLE IF NOT EXISTS city (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  slug VARCHAR(160) NOT NULL,
  lat DECIMAL(10,7) NULL,
  lng DECIMAL(10,7) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY ux_city_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS clinic (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  city_id BIGINT UNSIGNED NOT NULL,
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(255) NOT NULL,            -- unique friendly URL
  description TEXT NULL,
  contact_phone VARCHAR(32) NULL,
  contact_email VARCHAR(255) NULL,
  address VARCHAR(512) NULL,
  registration_number VARCHAR(128) NULL, 
  services JSON NULL,                    
  pricing JSON NULL,                     
  photos JSON NULL,                      
  is_verified TINYINT(1) DEFAULT 0,      
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (city_id) REFERENCES city(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  UNIQUE KEY ux_clinic_slug (slug),
  INDEX idx_clinic_city (city_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Photos metadata stored separately for flexibility
CREATE TABLE IF NOT EXISTS clinic_photo (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  clinic_id BIGINT UNSIGNED NOT NULL,
  file_path VARCHAR(1024) NOT NULL,
  caption VARCHAR(255) DEFAULT NULL,
  is_primary TINYINT(1) DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (clinic_id) REFERENCES clinic(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



CREATE TABLE IF NOT EXISTS doctor (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  clinic_id BIGINT UNSIGNED NOT NULL,
  name VARCHAR(255) NOT NULL,
  specialty VARCHAR(255) DEFAULT NULL,
  phone VARCHAR(32) DEFAULT NULL,
  email VARCHAR(255) DEFAULT NULL,
  working_hours JSON DEFAULT NULL,    -- e.g. [{"day":"Mon","from":"08:00","to":"12:00"},...]
  bio TEXT DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (clinic_id) REFERENCES clinic(id) ON DELETE CASCADE ON UPDATE CASCADE,
  INDEX idx_doctor_clinic (clinic_id),
  INDEX idx_doctor_specialty (specialty)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



CREATE TABLE IF NOT EXISTS patient (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  phone VARCHAR(32) NOT NULL,
  email VARCHAR(255) DEFAULT NULL,
  preferred_language ENUM('rw','en') DEFAULT 'rw', -- 'rw' = Kinyarwanda
  city_id BIGINT UNSIGNED DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (city_id) REFERENCES city(id) ON DELETE SET NULL ON UPDATE CASCADE,
  UNIQUE KEY ux_patient_phone (phone),
  INDEX idx_patient_city (city_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

DELETE FROM patient WHERE phone = '0781290496';

CREATE TABLE IF NOT EXISTS appointment_request (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  patient_id BIGINT UNSIGNED NOT NULL,
  clinic_id BIGINT UNSIGNED NOT NULL,
  doctor_id BIGINT UNSIGNED NULL,
  requested_start DATETIME NOT NULL,
  requested_end DATETIME NOT NULL,
  reason TEXT NULL,
  is_urgent TINYINT(1) DEFAULT 0,
  status ENUM('pending','approved','rescheduled','declined') DEFAULT 'pending',
  proposed_start DATETIME NULL,   -- when clinic proposes a reschedule
  proposed_end DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (patient_id) REFERENCES patient(id) ON DELETE CASCADE,
  FOREIGN KEY (clinic_id) REFERENCES clinic(id) ON DELETE CASCADE,
  FOREIGN KEY (doctor_id) REFERENCES doctor(id) ON DELETE SET NULL,
  INDEX idx_req_clinic (clinic_id),
  INDEX idx_req_doctor (doctor_id),
  INDEX idx_req_start (requested_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



CREATE TABLE IF NOT EXISTS appointment (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  appointment_request_id BIGINT UNSIGNED NOT NULL UNIQUE,
  clinic_id BIGINT UNSIGNED NOT NULL,
  doctor_id BIGINT UNSIGNED NULL,
  confirmed_start DATETIME NOT NULL,
  confirmed_end DATETIME NOT NULL,
  payment_status ENUM('unpaid','paid','pending_refund') DEFAULT 'unpaid',
  receipt_link VARCHAR(1024) DEFAULT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (appointment_request_id) REFERENCES appointment_request(id) ON DELETE CASCADE,
  FOREIGN KEY (clinic_id) REFERENCES clinic(id) ON DELETE CASCADE,
  FOREIGN KEY (doctor_id) REFERENCES doctor(id) ON DELETE SET NULL,
  INDEX idx_appt_clinic (clinic_id),
  INDEX idx_appt_doctor (doctor_id),
  INDEX idx_appt_time (confirmed_start, confirmed_end)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;



-- Staff table: clinic staff and superadmin
CREATE TABLE IF NOT EXISTS staff (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  clinic_id BIGINT UNSIGNED NULL,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) DEFAULT NULL,
  phone VARCHAR(32) DEFAULT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('staff','manager','superadmin') DEFAULT 'staff',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (clinic_id) REFERENCES clinic(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Notifications table for in-app / email / sms tracking
CREATE TABLE IF NOT EXISTS notification (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  appointment_id BIGINT UNSIGNED NULL,
  appointment_request_id BIGINT UNSIGNED NULL,
  recipient_type ENUM('patient','clinic','staff','admin') NOT NULL,
  recipient_id BIGINT UNSIGNED NULL,
  channel ENUM('in_app','email','sms','whatsapp') DEFAULT 'in_app',
  message TEXT,
  status ENUM('queued','sent','failed') DEFAULT 'queued',
  read_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (appointment_id) REFERENCES appointment(id) ON DELETE SET NULL,
  FOREIGN KEY (appointment_request_id) REFERENCES appointment_request(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Simple reviews table for clinics so patients can leave feedback
CREATE TABLE IF NOT EXISTS clinic_review (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  clinic_id BIGINT UNSIGNED NOT NULL,
  patient_id BIGINT UNSIGNED NULL,
  rating TINYINT UNSIGNED NOT NULL,        -- 1-5 stars
  comment TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (clinic_id) REFERENCES clinic(id) ON DELETE CASCADE,
  FOREIGN KEY (patient_id) REFERENCES patient(id) ON DELETE SET NULL,
  INDEX idx_review_clinic (clinic_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Set the first photo as primary for each clinic (run this after initial data load)


DESC clinic_review;

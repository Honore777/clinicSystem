-- Run this in SQLTools as a root/admin user to create a dedicated DB user
-- Replace 'strong_password' with a secure password before running.

CREATE USER IF NOT EXISTS 'clinic_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON clinic_system.* TO 'clinic_user'@'localhost';

CREATE USER IF NOT EXISTS 'clinic_user'@'127.0.0.1' IDENTIFIED BY 'strong_password';
GRANT ALL PRIVILEGES ON clinic_system.* TO 'clinic_user'@'127.0.0.1';

-- If MySQL 8 and client has auth plugin issues, you can force mysql_native_password:
-- ALTER USER 'clinic_user'@'localhost' IDENTIFIED WITH mysql_native_password BY 'strong_password';
-- ALTER USER 'clinic_user'@'127.0.0.1' IDENTIFIED WITH mysql_native_password BY 'strong_password';

FLUSH PRIVILEGES;

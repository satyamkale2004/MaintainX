CREATE DATABASE maintenx;
USE maintenx;

CREATE TABLE societies(
id INT AUTO_INCREMENT PRIMARY KEY,
name VARCHAR(100),
address TEXT
);

CREATE TABLE secretary(
id INT AUTO_INCREMENT PRIMARY KEY,
name VARCHAR(100),
email VARCHAR(100),
mobile VARCHAR(15),
password VARCHAR(100),
society_id INT
);

CREATE TABLE members(
id INT AUTO_INCREMENT PRIMARY KEY,
name VARCHAR(100),
email VARCHAR(100),
mobile VARCHAR(15),
flat_no VARCHAR(10),
living_type VARCHAR(20),
maintenance INT,
password VARCHAR(100),
society_id INT
);

CREATE TABLE bills(
id INT AUTO_INCREMENT PRIMARY KEY,
member_id INT,
month VARCHAR(20),
maintenance INT,
penalty INT,
total INT,
status VARCHAR(20)
);

CREATE TABLE payments(
id INT AUTO_INCREMENT PRIMARY KEY,
member_id INT,
bill_id INT,
amount INT,
payment_date DATE
);

ALTER TABLE bills ADD COLUMN society_id INT;
UPDATE bills SET society_id = 1;

ALTER TABLE bills ADD COLUMN date DATE;
UPDATE bills SET date = CURDATE();

-- Charges
CREATE TABLE charges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    society_id INT,
    title VARCHAR(100),
    amount DECIMAL(10,2),
    created_at DATE
);

-- Announcements
CREATE TABLE announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    society_id INT,
    title VARCHAR(200),
    message TEXT,
    date DATE
);

-- Complaints
CREATE TABLE complaints (
    id INT AUTO_INCREMENT PRIMARY KEY,
    member_id INT,
    society_id INT,
    subject VARCHAR(200),
    message TEXT,
    status VARCHAR(20) DEFAULT 'Pending',
    date DATE
);
ALTER TABLE bills ADD due_date DATE;

ALTER TABLE bills 
ADD UNIQUE KEY unique_bill (member_id, month, society_id);

ALTER TABLE bills 
ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
-- สร้างฐานข้อมูล
CREATE DATABASE IF NOT EXISTS fallsense;

-- เลือกฐานข้อมูล
USE fallsense;

-- สร้างตาราง users
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- สร้างตาราง fall_history (ประวัติการหกล้ม)
CREATE TABLE IF NOT EXISTS fall_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    camera_id INT NOT NULL,
    camera_name VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL,
    fall_time DATETIME NOT NULL,
    severity VARCHAR(50) NOT NULL,
    details TEXT,
    image_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- เพิ่มข้อมูลตัวอย่างในตาราง fall_history
INSERT INTO fall_history (camera_id, camera_name, location, fall_time, severity, details, image_url) VALUES
    (1, 'กล้อง 1', 'ห้องนั่งเล่น', '2023-06-15 08:30:00', 'รุนแรงปานกลาง', 'ผู้สูงอายุหกล้มขณะเดินไปห้องน้ำ', '/static/images/fall1.jpg'),
    (2, 'กล้อง 2', 'ห้องครัว', '2023-07-21 15:45:00', 'รุนแรงมาก', 'หกล้มและมีการกระแทกศีรษะ', '/static/images/fall2.jpg'),
    (1, 'กล้อง 1', 'ห้องนั่งเล่น', '2023-08-05 22:10:00', 'รุนแรงน้อย', 'สะดุดพรมแต่ไม่ได้รับบาดเจ็บรุนแรง', '/static/images/fall3.jpg'),
    (3, 'กล้อง 3', 'ห้องนอน', '2023-09-13 06:20:00', 'รุนแรงปานกลาง', 'หกล้มจากเตียง', '/static/images/fall4.jpg'),
    (2, 'กล้อง 2', 'ห้องครัว', '2023-10-30 12:15:00', 'รุนแรงน้อย', 'ลื่นแต่สามารถพยุงตัวได้', '/static/images/fall5.jpg');

-- เพิ่มผู้ใช้ตัวอย่าง (รหัสผ่าน: admin123)
INSERT INTO users (username, password) VALUES ('admin', 'admin123'); 
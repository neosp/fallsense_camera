<?php
// กำหนดค่าการเชื่อมต่อฐานข้อมูล
$host = "localhost";
$port = 3306;  // ระบุพอร์ต 3306
$user = "root";
$password = "1234";
$db_name = "fallsense";
$charset = "utf8";  // ใช้ utf8 แทน utf8mb4

// สร้างการเชื่อมต่อกับฐานข้อมูล
function get_db_connection() {
    global $host, $port, $user, $password, $db_name, $charset;
    
    try {
        // สร้างการเชื่อมต่อ PDO พร้อมระบุพอร์ต
        $dsn = "mysql:host=$host;port=$port;dbname=$db_name;charset=$charset";
        $options = array(
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false,
        );
        
        return new PDO($dsn, $user, $password, $options);
    } catch (PDOException $e) {
        // บันทึกข้อผิดพลาดแทนการแสดงผลโดยตรง (ป้องกันการเปิดเผยข้อมูลสำคัญ)
        error_log("Database connection error: " . $e->getMessage());
        return null;
    }
}

// ฟังก์ชันสำหรับการสร้างตารางและฐานข้อมูล
function create_database_and_tables() {
    global $host, $port, $user, $password, $db_name;
    
    try {
        // เชื่อมต่อโดยไม่ระบุฐานข้อมูล
        $dsn = "mysql:host=$host;port=$port";
        $conn = new PDO($dsn, $user, $password);
        $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        
        // สร้างฐานข้อมูล
        $conn->exec("CREATE DATABASE IF NOT EXISTS $db_name");
        $conn->exec("USE $db_name");
        
        // สร้างตาราง users
        $conn->exec("CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )");
        
        // สร้างตาราง fall_history
        $conn->exec("CREATE TABLE IF NOT EXISTS fall_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            camera_id INT NOT NULL,
            camera_name VARCHAR(100) NOT NULL,
            location VARCHAR(100) NOT NULL,
            fall_time DATETIME NOT NULL,
            severity VARCHAR(50) NOT NULL,
            details TEXT,
            image_url VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )");
        
        // ตรวจสอบว่ามีข้อมูลในตาราง fall_history หรือไม่
        $stmt = $conn->query("SELECT COUNT(*) as count FROM fall_history");
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        $count = $row["count"];
        
        if ($count == 0) {
            // เพิ่มข้อมูลตัวอย่าง
            $conn->exec("INSERT INTO fall_history (camera_id, camera_name, location, fall_time, severity, details, image_url) VALUES
                (1, 'กล้อง 1', 'ห้องนั่งเล่น', '2023-06-15 08:30:00', 'รุนแรงปานกลาง', 'ผู้สูงอายุหกล้มขณะเดินไปห้องน้ำ', '/static/images/fall1.jpg'),
                (2, 'กล้อง 2', 'ห้องครัว', '2023-07-21 15:45:00', 'รุนแรงมาก', 'หกล้มและมีการกระแทกศีรษะ', '/static/images/fall2.jpg'),
                (1, 'กล้อง 1', 'ห้องนั่งเล่น', '2023-08-05 22:10:00', 'รุนแรงน้อย', 'สะดุดพรมแต่ไม่ได้รับบาดเจ็บรุนแรง', '/static/images/fall3.jpg'),
                (3, 'กล้อง 3', 'ห้องนอน', '2023-09-13 06:20:00', 'รุนแรงปานกลาง', 'หกล้มจากเตียง', '/static/images/fall4.jpg'),
                (2, 'กล้อง 2', 'ห้องครัว', '2023-10-30 12:15:00', 'รุนแรงน้อย', 'ลื่นแต่สามารถพยุงตัวได้', '/static/images/fall5.jpg')
            ");
        }
        
        // ตรวจสอบว่ามีผู้ใช้ในระบบหรือไม่
        $stmt = $conn->query("SELECT COUNT(*) as count FROM users");
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        $count = $row["count"];
        
        if ($count == 0) {
            // เพิ่มผู้ใช้ตัวอย่าง (รหัสผ่าน: admin123)
            $hashed_password = password_hash("admin123", PASSWORD_DEFAULT);
            $conn->exec("INSERT INTO users (username, password) VALUES ('admin', '$hashed_password')");
        }
        
        return true;
    } catch (PDOException $e) {
        error_log("Database setup error: " . $e->getMessage());
        return false;
    }
}

// สร้างตารางและฐานข้อมูลอัตโนมัติเมื่อรวมไฟล์นี้
create_database_and_tables();
?> 
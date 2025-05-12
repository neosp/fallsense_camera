<?php
// เริ่ม session
session_start();

// ตั้งค่าการเชื่อมต่อฐานข้อมูล
$host = "localhost";
$username = "root";
$password = "1234";
$db_name = "fallsense";

// ตัวแปรสำหรับข้อความแสดงผล
$message = "";

// สร้างการเชื่อมต่อกับฐานข้อมูล
try {
    $conn = new PDO("mysql:host=$host", $username, $password);
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    // ตรวจสอบว่าฐานข้อมูลมีอยู่แล้วหรือไม่ ถ้าไม่มีให้สร้าง
    $sql = "CREATE DATABASE IF NOT EXISTS $db_name";
    $conn->exec($sql);
    
    // เลือกฐานข้อมูล
    $conn->exec("USE $db_name");
    
    // สร้างตาราง users ถ้ายังไม่มี
    $sql = "CREATE TABLE IF NOT EXISTS users (
        id INT(6) UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )";
    $conn->exec($sql);
    
} catch(PDOException $e) {
    $message = "การเชื่อมต่อฐานข้อมูลผิดพลาด: " . $e->getMessage();
}

// ตรวจสอบการส่งฟอร์ม login
if ($_SERVER["REQUEST_METHOD"] == "POST" && isset($_POST['login'])) {
    $username = $_POST['username'];
    $password = $_POST['password'];
    
    try {
        // ค้นหาผู้ใช้จากฐานข้อมูล
        $stmt = $conn->prepare("SELECT * FROM users WHERE username = :username");
        $stmt->bindParam(':username', $username);
        $stmt->execute();
        $user = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if ($user) {
            // ตรวจสอบรหัสผ่าน
            if (password_verify($password, $user['password'])) {
                // รหัสผ่านถูกต้อง, กำหนดค่า session
                $_SESSION['loggedin'] = true;
                $_SESSION['username'] = $username;
                
                // Redirect ไปที่หน้า dashboard
                header("Location: dashboard.php");
                exit;
            } else {
                $message = "รหัสผ่านไม่ถูกต้อง";
            }
        } else {
            $message = "ไม่พบชื่อผู้ใช้";
        }
    } catch(PDOException $e) {
        $message = "เกิดข้อผิดพลาด: " . $e->getMessage();
    }
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Fallsense Camera</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }
        .container {
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            padding: 30px;
            width: 100%;
            max-width: 400px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #555;
            font-weight: 500;
        }
        .form-control {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            box-sizing: border-box;
            transition: border-color 0.3s;
        }
        .form-control:focus {
            border-color: #3498db;
            outline: none;
        }
        .btn {
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 12px 20px;
            cursor: pointer;
            width: 100%;
            font-size: 16px;
            font-weight: 500;
            transition: background-color 0.3s;
        }
        .btn:hover {
            background-color: #2980b9;
        }
        .message {
            text-align: center;
            margin-top: 20px;
            padding: 10px;
            color: #e74c3c;
        }
        .footer {
            text-align: center;
            margin-top: 20px;
        }
        .footer a {
            color: #3498db;
            text-decoration: none;
        }
        .footer a:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Fallsense Camera</h1>
            <p>เข้าสู่ระบบเพื่อจัดการกล้อง</p>
        </div>
        
        <?php if(!empty($message)): ?>
        <div class="message">
            <?php echo $message; ?>
        </div>
        <?php endif; ?>
        
        <form action="<?php echo htmlspecialchars($_SERVER["PHP_SELF"]); ?>" method="post">
            <div class="form-group">
                <label for="username">ชื่อผู้ใช้</label>
                <input type="text" class="form-control" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">รหัสผ่าน</label>
                <input type="password" class="form-control" id="password" name="password" required>
            </div>
            <button type="submit" name="login" class="btn">เข้าสู่ระบบ</button>
        </form>
        
        <div class="footer">
            <p>ยังไม่มีบัญชีผู้ใช้? <a href="register.php">ลงทะเบียน</a></p>
        </div>
    </div>
</body>
</html> 
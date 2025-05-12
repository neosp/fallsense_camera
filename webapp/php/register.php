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
    $conn = new PDO("mysql:host=$host;dbname=$db_name", $username, $password);
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch(PDOException $e) {
    $message = "การเชื่อมต่อฐานข้อมูลผิดพลาด: " . $e->getMessage();
}

// ตรวจสอบการส่งฟอร์มลงทะเบียน
if ($_SERVER["REQUEST_METHOD"] == "POST" && isset($_POST['register'])) {
    $username = $_POST['username'];
    $password = $_POST['password'];
    $confirm_password = $_POST['confirm_password'];
    
    // ตรวจสอบว่ารหัสผ่านตรงกัน
    if ($password !== $confirm_password) {
        $message = "รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน";
    } else {
        try {
            // ตรวจสอบว่ามีชื่อผู้ใช้นี้อยู่แล้วหรือไม่
            $stmt = $conn->prepare("SELECT COUNT(*) FROM users WHERE username = :username");
            $stmt->bindParam(':username', $username);
            $stmt->execute();
            $count = $stmt->fetchColumn();
            
            if ($count > 0) {
                $message = "ชื่อผู้ใช้นี้มีอยู่ในระบบแล้ว กรุณาใช้ชื่อผู้ใช้อื่น";
            } else {
                // เข้ารหัสรหัสผ่าน
                $hashed_password = password_hash($password, PASSWORD_DEFAULT);
                
                // เพิ่มผู้ใช้ใหม่ลงในฐานข้อมูล
                $stmt = $conn->prepare("INSERT INTO users (username, password) VALUES (:username, :password)");
                $stmt->bindParam(':username', $username);
                $stmt->bindParam(':password', $hashed_password);
                $stmt->execute();
                
                // แสดงข้อความสำเร็จ และ redirect ไปที่หน้า login
                $message = "ลงทะเบียนสำเร็จ คุณสามารถเข้าสู่ระบบได้แล้ว";
                header("Refresh: 2; URL=index.php");
            }
        } catch(PDOException $e) {
            $message = "เกิดข้อผิดพลาด: " . $e->getMessage();
        }
    }
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - Fallsense Camera</title>
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
        .success-message {
            text-align: center;
            margin-top: 20px;
            padding: 10px;
            color: #27ae60;
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
            <p>ลงทะเบียนบัญชีผู้ใช้ใหม่</p>
        </div>
        
        <?php if(!empty($message)): ?>
        <div class="<?php echo strpos($message, 'สำเร็จ') !== false ? 'success-message' : 'message'; ?>">
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
            <div class="form-group">
                <label for="confirm_password">ยืนยันรหัสผ่าน</label>
                <input type="password" class="form-control" id="confirm_password" name="confirm_password" required>
            </div>
            <button type="submit" name="register" class="btn">ลงทะเบียน</button>
        </form>
        
        <div class="footer">
            <p>มีบัญชีผู้ใช้แล้ว? <a href="index.php">เข้าสู่ระบบ</a></p>
        </div>
    </div>
    
    <script>
        // ตรวจสอบว่ารหัสผ่านและการยืนยันรหัสผ่านตรงกันก่อนส่งฟอร์ม
        document.querySelector('form').addEventListener('submit', function(event) {
            var password = document.getElementById('password').value;
            var confirmPassword = document.getElementById('confirm_password').value;
            
            if (password !== confirmPassword) {
                event.preventDefault();
                alert('รหัสผ่านและการยืนยันรหัสผ่านไม่ตรงกัน');
            }
        });
    </script>
</body>
</html> 
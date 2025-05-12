<?php
// เริ่ม session
session_start();

// ตรวจสอบว่ามีการเข้าสู่ระบบหรือไม่
if (!isset($_SESSION['loggedin']) || $_SESSION['loggedin'] !== true) {
    header("Location: index.php");
    exit;
}

// รับค่าชื่อผู้ใช้จาก session
$username = $_SESSION['username'];

// ฟังก์ชันสำหรับออกจากระบบ
if (isset($_GET['logout'])) {
    // ล้างค่า session และ redirect ไปที่หน้า login
    session_destroy();
    header("Location: index.php");
    exit;
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Fallsense Camera</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 0;
        }
        .navbar {
            background-color: #2c3e50;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .navbar h1 {
            margin: 0;
            font-size: 22px;
        }
        .user-info {
            display: flex;
            align-items: center;
        }
        .user-info span {
            margin-right: 15px;
        }
        .logout-btn {
            background-color: #e74c3c;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
        }
        .logout-btn:hover {
            background-color: #c0392b;
        }
        .container {
            max-width: 1200px;
            margin: 20px auto;
            padding: 0 20px;
        }
        .dashboard-header {
            margin-bottom: 30px;
        }
        .dashboard-header h2 {
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }
        .card-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            padding: 20px;
            transition: transform 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card h3 {
            color: #2c3e50;
            margin-top: 0;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        .card-content {
            margin-top: 15px;
        }
        .camera-feed {
            width: 100%;
            height: 200px;
            background-color: #000;
            border-radius: 5px;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #666;
            font-style: italic;
        }
        .camera-controls {
            margin-top: 15px;
            display: flex;
            justify-content: space-between;
        }
        .camera-btn {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
            cursor: pointer;
            flex: 1;
            margin: 0 5px;
        }
        .camera-btn.record {
            background-color: #e74c3c;
        }
        .status {
            margin-top: 10px;
            padding: 8px;
            border-radius: 4px;
            background-color: #f8f9fa;
            font-size: 14px;
        }
        .status.online {
            color: #27ae60;
            border-left: 4px solid #27ae60;
        }
        .status.offline {
            color: #e74c3c;
            border-left: 4px solid #e74c3c;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>Fallsense Camera Dashboard</h1>
        <div class="user-info">
            <span>ยินดีต้อนรับ, <?php echo htmlspecialchars($username); ?></span>
            <a href="?logout=1" class="logout-btn">ออกจากระบบ</a>
        </div>
    </div>
    
    <div class="container">
        <div class="dashboard-header">
            <h2>จัดการกล้อง Fallsense</h2>
        </div>
        
        <div class="card-container">
            <!-- Camera 1 -->
            <div class="card">
                <h3>กล้อง 1 - ห้องนั่งเล่น</h3>
                <div class="card-content">
                    <div class="camera-feed">
                        [ภาพกล้องจะแสดงที่นี่]
                    </div>
                    <div class="camera-controls">
                        <button class="camera-btn">ตั้งค่า</button>
                        <button class="camera-btn record">บันทึก</button>
                        <button class="camera-btn">ภาพนิ่ง</button>
                    </div>
                    <div class="status online">
                        สถานะ: ออนไลน์
                    </div>
                </div>
            </div>
            
            <!-- Camera 2 -->
            <div class="card">
                <h3>กล้อง 2 - ประตูหน้า</h3>
                <div class="card-content">
                    <div class="camera-feed">
                        [ภาพกล้องจะแสดงที่นี่]
                    </div>
                    <div class="camera-controls">
                        <button class="camera-btn">ตั้งค่า</button>
                        <button class="camera-btn record">บันทึก</button>
                        <button class="camera-btn">ภาพนิ่ง</button>
                    </div>
                    <div class="status online">
                        สถานะ: ออนไลน์
                    </div>
                </div>
            </div>
            
            <!-- Camera 3 -->
            <div class="card">
                <h3>กล้อง 3 - สวนหลังบ้าน</h3>
                <div class="card-content">
                    <div class="camera-feed">
                        [ภาพกล้องจะแสดงที่นี่]
                    </div>
                    <div class="camera-controls">
                        <button class="camera-btn">ตั้งค่า</button>
                        <button class="camera-btn record">บันทึก</button>
                        <button class="camera-btn">ภาพนิ่ง</button>
                    </div>
                    <div class="status offline">
                        สถานะ: ออฟไลน์
                    </div>
                </div>
            </div>
            
            <!-- Add Camera -->
            <div class="card">
                <h3>เพิ่มกล้องใหม่</h3>
                <div class="card-content" style="text-align:center; padding: 40px 0;">
                    <div style="font-size: 50px; color: #ddd; margin-bottom: 20px;">+</div>
                    <button class="camera-btn" style="width: 80%;">เพิ่มกล้อง</button>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // JavaScript สำหรับจำลองการทำงานของปุ่มต่างๆ
        document.querySelectorAll('.camera-btn').forEach(function(button) {
            button.addEventListener('click', function() {
                if (this.textContent === 'บันทึก') {
                    this.textContent = 'หยุด';
                    this.style.backgroundColor = '#e74c3c';
                } else if (this.textContent === 'หยุด') {
                    this.textContent = 'บันทึก';
                    this.style.backgroundColor = '#3498db';
                } else if (this.textContent === 'ภาพนิ่ง') {
                    alert('บันทึกภาพนิ่งสำเร็จ');
                } else if (this.textContent === 'ตั้งค่า') {
                    alert('กำลังเปิดการตั้งค่ากล้อง');
                } else if (this.textContent === 'เพิ่มกล้อง') {
                    alert('กำลังเพิ่มกล้องใหม่');
                }
            });
        });
    </script>
</body>
</html> 
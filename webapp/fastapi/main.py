from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from typing import Dict, List, Optional
import pymysql
import pymysql.cursors
import traceback
import datetime

app = FastAPI()

# ตั้งค่า templates และ static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ตั้งค่าการเชื่อมต่อ MySQL
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,   # เพิ่ม port 3306
    "user": "root",
    "password": "1234",
    "charset": "utf8",  # เปลี่ยนจาก utf8mb4 เป็น utf8
    "cursorclass": pymysql.cursors.DictCursor
}

# ฟังก์ชันสำหรับเชื่อมต่อกับฐานข้อมูล
def get_connection():
    try:
        # เชื่อมต่อโดยไม่ระบุฐานข้อมูลก่อน
        temp_config = DB_CONFIG.copy()
        connection = pymysql.connect(**temp_config)
        
        # สร้างฐานข้อมูล fallsense ถ้ายังไม่มี
        with connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS fallsense")
            cursor.execute("USE fallsense")
        
        return connection
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"ไม่สามารถเชื่อมต่อฐานข้อมูลได้: {e}")
        print(f"Error details: {error_detail}")
        return None

# ฟังก์ชันสำหรับสร้างตารางหากยังไม่มี
def create_tables():
    connection = get_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                # สร้างตาราง users
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # สร้างตาราง fall_history (ประวัติการหกล้ม)
                cursor.execute("""
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
                )
                """)
            connection.commit()
            print("สร้างตารางสำเร็จ")
            
            # เพิ่มข้อมูลตัวอย่างในตาราง fall_history ถ้ายังไม่มีข้อมูล
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM fall_history")
                count = cursor.fetchone()["count"]
                
                if count == 0:
                    # เพิ่มข้อมูลตัวอย่าง
                    sample_data = [
                        (1, "กล้อง 1", "ห้องนั่งเล่น", "2023-06-15 08:30:00", "รุนแรงปานกลาง", "ผู้สูงอายุหกล้มขณะเดินไปห้องน้ำ", "/static/images/fall1.jpg"),
                        (2, "กล้อง 2", "ห้องครัว", "2023-07-21 15:45:00", "รุนแรงมาก", "หกล้มและมีการกระแทกศีรษะ", "/static/images/fall2.jpg"),
                        (1, "กล้อง 1", "ห้องนั่งเล่น", "2023-08-05 22:10:00", "รุนแรงน้อย", "สะดุดพรมแต่ไม่ได้รับบาดเจ็บรุนแรง", "/static/images/fall3.jpg"),
                        (3, "กล้อง 3", "ห้องนอน", "2023-09-13 06:20:00", "รุนแรงปานกลาง", "หกล้มจากเตียง", "/static/images/fall4.jpg"),
                        (2, "กล้อง 2", "ห้องครัว", "2023-10-30 12:15:00", "รุนแรงน้อย", "ลื่นแต่สามารถพยุงตัวได้", "/static/images/fall5.jpg"),
                    ]
                    
                    for data in sample_data:
                        camera_id, camera_name, location, fall_time, severity, details, image_url = data
                        cursor.execute("""
                        INSERT INTO fall_history (camera_id, camera_name, location, fall_time, severity, details, image_url)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (camera_id, camera_name, location, fall_time, severity, details, image_url))
                    
                    connection.commit()
                    print("เพิ่มข้อมูลตัวอย่างสำเร็จ")
                
        except Exception as e:
            error_detail = traceback.format_exc()
            print(f"ไม่สามารถสร้างตารางได้: {e}")
            print(f"Error details: {error_detail}")
        finally:
            connection.close()

# เรียกฟังก์ชันสร้างตารางเมื่อเริ่มแอป
try:
    print("กำลังพยายามเชื่อมต่อกับฐานข้อมูล...")
    create_tables()
    print("เชื่อมต่อฐานข้อมูลสำเร็จ")
except Exception as e:
    error_detail = traceback.format_exc()
    print(f"เกิดข้อผิดพลาดในการเริ่มต้นฐานข้อมูล: {e}")
    print(f"Error details: {error_detail}")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "message": ""})

@app.get("/login", response_class=HTMLResponse)
async def fall_history(request: Request):
    """แสดงรายการประวัติการหกล้ม"""
    connection = get_connection()
    if not connection:
        return templates.TemplateResponse(
            "error.html", 
            {"request": request, "message": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้ กรุณาตรวจสอบว่า MySQL ทำงานอยู่และรหัสผ่านถูกต้อง"}
        )
    
    try:
        with connection.cursor() as cursor:
            # ดึงข้อมูลประวัติการหกล้มทั้งหมด เรียงตามเวลาล่าสุด
            cursor.execute("SELECT fall_time FROM fall_history ORDER BY fall_time DESC")
            fall_records = cursor.fetchall()
            
            # ปรับรูปแบบวันที่ให้เหมาะสม
            for record in fall_records:
                if isinstance(record["fall_time"], datetime.datetime):
                    record["formatted_time"] = record["fall_time"].strftime("%d/%m/%Y %H:%M")
                else:
                    record["formatted_time"] = record["fall_time"]
            
            # ดึงจำนวนการหกล้มทั้งหมด
            cursor.execute("SELECT COUNT(*) as total FROM fall_history")
            total_falls = cursor.fetchone()["total"]
            
            stats = {
                "total_falls": total_falls
            }
            
            return templates.TemplateResponse(
                "fall_history.html", 
                {
                    "request": request, 
                    "fall_records": fall_records,
                    "stats": stats
                }
            )
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูลประวัติการหกล้ม: {e}")
        print(f"Error details: {error_detail}")
        return templates.TemplateResponse(
            "error.html", 
            {"request": request, "message": f"เกิดข้อผิดพลาด: {str(e)}"}
        )
    finally:
        connection.close()

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...)
):
    connection = get_connection()
    if not connection:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "message": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้ กรุณาตรวจสอบว่า MySQL ทำงานอยู่และรหัสผ่านถูกต้อง"}
        )
    
    try:
        with connection.cursor() as cursor:
            # ค้นหาผู้ใช้จากฐานข้อมูล
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if user and user["password"] == password:  # ในระบบจริงควรเข้ารหัส password
                # ดึงข้อมูลประวัติการหกล้มทั้งหมด เรียงตามเวลาล่าสุด
                cursor.execute("SELECT fall_time FROM fall_history ORDER BY fall_time DESC")
                fall_records = cursor.fetchall()
                
                # ปรับรูปแบบวันที่ให้เหมาะสม
                for record in fall_records:
                    if isinstance(record["fall_time"], datetime.datetime):
                        record["formatted_time"] = record["fall_time"].strftime("%d/%m/%Y %H:%M")
                    else:
                        record["formatted_time"] = record["fall_time"]
                
                # ดึงจำนวนการหกล้มทั้งหมด
                cursor.execute("SELECT COUNT(*) as total FROM fall_history")
                total_falls = cursor.fetchone()["total"]
                
                stats = {
                    "total_falls": total_falls
                }
                
                return templates.TemplateResponse(
                    "fall_history.html", 
                    {
                        "request": request, 
                        "fall_records": fall_records,
                        "stats": stats,
                        "username": username
                    }
                )
            else:
                return templates.TemplateResponse(
                    "login.html", 
                    {"request": request, "message": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"}
                )
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"เกิดข้อผิดพลาดในการล็อกอิน: {e}")
        print(f"Error details: {error_detail}")
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "message": f"เกิดข้อผิดพลาด: {str(e)}"}
        )
    finally:
        connection.close()

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "message": ""})

@app.post("/register", response_class=HTMLResponse)
async def register(
    request: Request, 
    username: str = Form(...), 
    password: str = Form(...)
):
    connection = get_connection()
    if not connection:
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "message": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้ กรุณาตรวจสอบว่า MySQL ทำงานอยู่และรหัสผ่านถูกต้อง"}
        )
    
    try:
        with connection.cursor() as cursor:
            # ตรวจสอบว่ามีชื่อผู้ใช้นี้อยู่แล้วหรือไม่
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                return templates.TemplateResponse(
                    "register.html", 
                    {"request": request, "message": "ชื่อผู้ใช้นี้มีอยู่ในระบบแล้ว"}
                )
            
            # เพิ่มผู้ใช้ใหม่
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, password)  # ในระบบจริงควรเข้ารหัส password
            )
            connection.commit()
            
            return templates.TemplateResponse(
                "login.html", 
                {"request": request, "message": "ลงทะเบียนสำเร็จ กรุณาเข้าสู่ระบบ"}
            )
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"เกิดข้อผิดพลาดในการลงทะเบียน: {e}")
        print(f"Error details: {error_detail}")
        return templates.TemplateResponse(
            "register.html", 
            {"request": request, "message": f"เกิดข้อผิดพลาด: {str(e)}"}
        )
    finally:
        connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 
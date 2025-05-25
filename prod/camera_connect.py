#!/usr/bin/env python3
import cv2
import numpy as np
import time
import os
import subprocess
import platform
import sys

def open_in_vlc(url):
    """
    Open the camera stream directly in VLC media player.
    This is useful when OpenCV cannot properly handle the stream but VLC can.
    
    Returns True if VLC was launched successfully, False otherwise.
    """
    print(f"Attempting to open stream in VLC: {url}")
    
    # Determine the correct VLC command based on operating system
    vlc_cmd = None
    if platform.system() == "Windows":
        # Try common installation paths on Windows
        vlc_paths = [
            "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
            "C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe"
        ]
        for path in vlc_paths:
            if os.path.exists(path):
                vlc_cmd = [path, url]
                break
        if vlc_cmd is None:
            print("VLC not found in common locations. Please install VLC or specify the correct path.")
            return False
            
    elif platform.system() == "Darwin":  # macOS
        vlc_paths = [
            "/Applications/VLC.app/Contents/MacOS/VLC",
            os.path.expanduser("~/Applications/VLC.app/Contents/MacOS/VLC")
        ]
        for path in vlc_paths:
            if os.path.exists(path):
                vlc_cmd = [path, url]
                break
        if vlc_cmd is None:
            print("VLC not found. Please install VLC.app in your Applications folder.")
            return False
            
    else:  # Linux and other Unix-like systems
        # Check if VLC is available in PATH
        try:
            subprocess.run(["which", "vlc"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            vlc_cmd = ["vlc", url]
        except subprocess.CalledProcessError:
            print("VLC not found. Please install VLC using your package manager.")
            return False
    
    # Launch VLC
    try:
        print(f"Launching VLC with command: {' '.join(vlc_cmd)}")
        subprocess.Popen(vlc_cmd)
        print("VLC launched successfully. Close the VLC window when finished.")
        return True
    except Exception as e:
        print(f"Error launching VLC: {e}")
        return False

def connect_to_ip_camera(ip="192.168.1.40", port="10554", user="admin", password="12345678", path="/tcp/av0_0", timeout=30):
    """
    Connect to an IP camera with the given credentials using the working URL format.
    Returns the VideoCapture object if successful, None otherwise.
    
    VStar C24S camera may require specific stream handling.
    """
    # Create URL for the IP camera with the specified format
    url = f"rtsp://{user}:{password}@{ip}:{port}{path}"
    
    print(f"Connecting to VStar C24S camera at {ip}:{port}")
    print(f"Using URL: {url}")
    
    # VLC-compatible options for OpenCV - these mimic what VLC might use
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|analyzeduration;10000000|reorder_queue_size;10000|buffer_size;10485760|stimeout;1000000"
    
    # Create VideoCapture options to improve streaming reliability
    # These options help with VStar camera models
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    
    # Configure specific parameters for RTSP streaming to improve reliability
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 10)  # Use a larger buffer like VLC would
    
    # Set timeout parameters for better connection handling
    # This can help with VStar C24S models that have streaming issues
    try:
        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC = 300000  # 30 seconds timeout
        cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)  # Convert to milliseconds
    except:
        print("Warning: CAP_PROP_OPEN_TIMEOUT_MSEC not supported in this OpenCV version")
    
    # Give it a moment to connect
    print(f"Waiting for connection (up to {timeout} seconds)...")
    time.sleep(3)
    
    # Check if camera opened successfully
    if not cap.isOpened():
        print(f"Error: Could not connect to IP camera at {ip}:{port}")
        # Try alternative URL formats that might work with VStar C24S
        alt_paths = [
            "/live/ch00_0",
            "/cam/realmonitor?channel=1&subtype=0",
            "/h264Preview_01_main",
            "/livestream/0",
            "/videoMain",
            "/live/ch01_0",
            "/video1"
        ]
        
        for alt_path in alt_paths:
            alt_url = f"rtsp://{user}:{password}@{ip}:{port}{alt_path}"
            print(f"Trying alternative URL: {alt_url}")
            alt_cap = cv2.VideoCapture(alt_url, cv2.CAP_FFMPEG)
            alt_cap.set(cv2.CAP_PROP_BUFFERSIZE, 10)
            time.sleep(2)
            
            if alt_cap.isOpened():
                print(f"Successfully connected using alternative URL: {alt_url}")
                return alt_cap
            else:
                alt_cap.release()
                
        print("All alternative paths failed. Trying one last method...")
        # Try TCP transport explicitly - sometimes helps with VStar cameras
        tcp_url = f"rtsp://{user}:{password}@{ip}:{port}{path}?tcp"
        tcp_cap = cv2.VideoCapture(tcp_url, cv2.CAP_FFMPEG)
        time.sleep(2)
        
        if tcp_cap.isOpened():
            print(f"Successfully connected using TCP transport: {tcp_url}")
            return tcp_cap
            
        return None
    
    print(f"Successfully connected to VStar C24S camera at {ip}:{port}")
    return cap

def display_camera_feed(cap, window_name="Camera Feed", auto_reconnect=True, ip="192.168.1.40", port="10554", user="admin", password="12345678", path="/tcp/av0_0"):
    """
    Display the camera feed in a window.
    Press 'q' to quit.
    If auto_reconnect is True, it will try to reconnect if connection is lost.
    
    Additional parameters are included to allow automatic reconnection to VStar C24S camera.
    """
    if cap is None:
        print("Error: Camera not connected")
        return
    
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    consecutive_failures = 0
    max_failures = 3  # VStar C24S may need quicker reconnection
    frame_count = 0
    last_frame_time = time.time()
    frame_timeout = 5  # Seconds to wait before considering the stream frozen
    
    try:
        while True:
            # Capture frame-by-frame
            ret, frame = cap.read()
            current_time = time.time()
            
            if not ret or (current_time - last_frame_time > frame_timeout and frame_count > 0):
                consecutive_failures += 1
                print(f"Error capturing frame. Failure count: {consecutive_failures}/{max_failures}")
                
                if consecutive_failures >= max_failures and auto_reconnect:
                    print("Connection lost or stream frozen. Attempting to reconnect...")
                    cap.release()
                    print("Waiting before reconnection attempt...")
                    time.sleep(2)  # Add delay before reconnection
                    
                    # Try to reconnect with explicit settings for VStar C24S
                    new_cap = connect_to_ip_camera(ip, port, user, password, path, timeout=10)
                    if new_cap is not None:
                        cap = new_cap
                        consecutive_failures = 0
                        frame_count = 0
                        last_frame_time = time.time()
                        print("Successfully reconnected to camera.")
                        continue
                    else:
                        print("Reconnection failed. Exiting display loop.")
                        break
                
                time.sleep(0.5)
                continue
            
            # Reset failure counter on successful frame capture
            consecutive_failures = 0
            last_frame_time = current_time
            frame_count += 1
            
            # VStar C24S specific - first frames might be invalid
            if frame_count < 3:
                print(f"Initializing stream, frame {frame_count}...")
            
            # Display the resulting frame
            try:
                # Check if frame is valid
                if frame is not None and frame.size > 0:
                    cv2.imshow(window_name, frame)
                else:
                    print("Received empty frame")
                    consecutive_failures += 1
                    continue
            except Exception as e:
                print(f"Error displaying frame: {e}")
                consecutive_failures += 1
                continue
            
            # Press 'q' to exit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
            # VStar C24S may need a small delay between frames
            time.sleep(0.01)
            
    except Exception as e:
        print(f"Error in camera feed: {e}")
    finally:
        # When everything done, release the capture and destroy windows
        cap.release()
        cv2.destroyAllWindows()

def save_image(cap, filename=None):
    """
    Capture and save a single image from the camera.
    """
    if cap is None:
        print("Error: Camera not connected")
        return False
    
    # Create output directory if it doesn't exist
    output_dir = "captures"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate filename with timestamp if not provided
    if filename is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"capture_{timestamp}.jpg")
    
    # Read a frame from the camera
    ret, frame = cap.read()
    
    if not ret:
        print("Error: Failed to capture image")
        return False
    
    # Save the image
    cv2.imwrite(filename, frame)
    print(f"Image saved as {filename}")
    return True

def record_video(cap, duration=10, filename=None):
    """
    Record video from the camera for the specified duration in seconds.
    """
    if cap is None:
        print("Error: Camera not connected")
        return False
    
    # Create output directory if it doesn't exist
    output_dir = "videos"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Generate filename with timestamp if not provided
    if filename is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"video_{timestamp}.mp4")
    
    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25  # Default to 25 fps if unable to get actual fps
    
    # Define codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use 'mp4v' for mp4 format
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"Error: Could not create video file {filename}")
        return False
    
    # Record for specified duration
    print(f"Recording video for {duration} seconds...")
    start_time = time.time()
    frames_recorded = 0
    
    try:
        while (time.time() - start_time) < duration:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame")
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                continue
            
            # Write the frame to the output file
            out.write(frame)
            frames_recorded += 1
            
            # Display the frame
            cv2.imshow('Recording...', frame)
            
            # Press 'q' to stop recording early
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    finally:
        # Release everything
        out.release()
        cv2.destroyAllWindows()
    
    print(f"Video recording complete. {frames_recorded} frames saved to {filename}")
    return True

def show_camera_properties(cap):
    """
    Display detailed camera properties.
    """
    if cap is None:
        print("Error: Camera not connected")
        return
    
    properties = [
        ("Width", cv2.CAP_PROP_FRAME_WIDTH),
        ("Height", cv2.CAP_PROP_FRAME_HEIGHT),
        ("FPS", cv2.CAP_PROP_FPS),
        ("Brightness", cv2.CAP_PROP_BRIGHTNESS),
        ("Contrast", cv2.CAP_PROP_CONTRAST),
        ("Saturation", cv2.CAP_PROP_SATURATION),
        ("Hue", cv2.CAP_PROP_HUE),
        ("Gain", cv2.CAP_PROP_GAIN),
        ("Exposure", cv2.CAP_PROP_EXPOSURE)
    ]
    
    print("\nCamera Properties:")
    print("-----------------")
    for name, prop_id in properties:
        try:
            value = cap.get(prop_id)
            print(f"{name}: {value}")
        except:
            print(f"{name}: Not supported")
    
    # Capture a test frame to verify connection
    ret, frame = cap.read()
    if ret:
        print("\nConnection Test: Successful")
        if frame is not None:
            print(f"Frame Shape: {frame.shape}")
            print(f"Frame Type: {frame.dtype}")
    else:
        print("\nConnection Test: Failed (could not capture frame)")

def test_alternative_paths():
    """
    Test multiple common RTSP path formats for VStar C24S camera
    """
    # Camera connection parameters
    ip = "192.168.1.40"
    port = "10554"
    user = "admin"
    password = "12345678"
    
    # Common RTSP paths to try
    paths = [
        "/tcp/av0_0",          # From your working URL
        "/h264Preview_01_main",
        "/live/ch00_0",
        "/cam/realmonitor?channel=1&subtype=0",
        "/livestream/0",
        "/videoMain",
        "/live/ch01_0",
        "/video1"
    ]
    
    print("Testing multiple RTSP URL formats for VStar C24S camera...")
    
    for path in paths:
        url = f"rtsp://{user}:{password}@{ip}:{port}{path}"
        print(f"\nTrying URL: {url}")
        
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 10)
        
        time.sleep(3)
        
        if cap.isOpened():
            print(f"SUCCESS: Connected with path: {path}")
            
            # Try to read a frame
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                print("SUCCESS: Captured a frame with this URL!")
                
                # Create output directory if it doesn't exist
                output_dir = "test_captures"
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = path.replace('/', '_')
                if filename.startswith('_'):
                    filename = filename[1:]
                test_image = os.path.join(output_dir, f"vstar_c24s_{filename}_{timestamp}.jpg")
                cv2.imwrite(test_image, frame)
                print(f"Saved test image as {test_image}")
                
                # Ask if user wants to view in VLC
                print("Would you like to open this stream in VLC? (y/n)")
                if input().lower() == 'y':
                    open_in_vlc(url)
            else:
                print("Connected but could not capture a frame")
        else:
            print(f"Failed to connect with path: {path}")
        
        cap.release()
    
    print("\nPath testing completed. If any paths worked, they should open in VLC if requested.")

def main():
    print("=== VStar C24S Camera Connection Utility ===")
    
    # Default IP camera credentials for the working URL
    ip = "192.168.1.40"
    port = "10554"
    user = "admin"
    password = "12345678"
    path = "/tcp/av0_0"
    
    # Construct the URL for both OpenCV and VLC
    url = f"rtsp://{user}:{password}@{ip}:{port}{path}"
    
    # Main operation loop
    while True:
        print("\nVStar C24S Camera Options:")
        print("1. Connect and display with OpenCV")
        print("2. Take a picture")
        print("3. Record video")
        print("4. Show camera properties")
        print("5. Open stream in VLC (recommended)")
        print("6. Change camera settings")
        print("7. Test alternative paths")
        print("8. Quit")
        
        choice = input("Enter your choice (1-8): ")
        
        if choice == '1':
            # Connect to the camera
            print(f"\nConnecting to VStar C24S camera at {ip}:{port}...")
            cap = connect_to_ip_camera(ip, port, user, password, path)
            
            if cap is None:
                print("Failed to connect to camera.")
                print("Would you like to try opening in VLC instead? (y/n)")
                if input().lower() == 'y':
                    open_in_vlc(url)
                continue
            
            # Pass all camera parameters for proper reconnection
            display_camera_feed(cap, auto_reconnect=True, 
                               ip=ip, port=port, user=user, 
                               password=password, path=path)
            # Release the camera
            if cap is not None:
                cap.release()
        
        elif choice == '2':
            # Connect to take a picture
            cap = connect_to_ip_camera(ip, port, user, password, path)
            if cap is None:
                print("Failed to connect to camera. Cannot take picture.")
                continue
                
            save_image(cap)
            cap.release()
        
        elif choice == '3':
            # Connect to record video
            cap = connect_to_ip_camera(ip, port, user, password, path)
            if cap is None:
                print("Failed to connect to camera. Cannot record video.")
                continue
                
            duration = input("Enter recording duration in seconds (default: 10): ")
            try:
                duration = int(duration)
            except ValueError:
                duration = 10
            
            record_video(cap, duration)
            cap.release()
        
        elif choice == '4':
            # Connect to show properties
            cap = connect_to_ip_camera(ip, port, user, password, path)
            if cap is None:
                print("Failed to connect to camera. Cannot show properties.")
                continue
                
            show_camera_properties(cap)
            cap.release()
        
        elif choice == '5':
            # Open directly in VLC (which is known to work)
            open_in_vlc(url)
        
        elif choice == '6':
            # Allow changing camera connection settings
            print("\nCurrent camera settings:")
            print(f"IP: {ip}")
            print(f"Port: {port}")
            print(f"Username: {user}")
            print(f"Password: {password}")
            print(f"Path: {path}")
            
            print("\nEnter new settings (press Enter to keep current value):")
            new_ip = input(f"IP address [{ip}]: ") or ip
            new_port = input(f"Port [{port}]: ") or port
            new_user = input(f"Username [{user}]: ") or user
            new_password = input(f"Password [{password}]: ") or password
            new_path = input(f"Path [{path}]: ") or path
            
            # Update settings
            ip = new_ip
            port = new_port
            user = new_user
            password = new_password
            path = new_path
            
            # Update the URL
            url = f"rtsp://{user}:{password}@{ip}:{port}{path}"
            print(f"Settings updated. New URL: {url}")
        
        elif choice == '7':
            test_alternative_paths()
        
        elif choice == '8':
            print("Exiting...")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

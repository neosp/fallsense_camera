#!/usr/bin/env python3
import cv2
import numpy as np
import time
import os

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
    
    # Create VideoCapture options to improve streaming reliability
    # These options help with VStar camera models
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    
    # Configure specific parameters for RTSP streaming to improve reliability
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # Use a smaller buffer for lower latency
    
    # Set timeout parameters for better connection handling
    # This can help with VStar C24S models that have streaming issues
    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC = 300000  # 30 seconds timeout
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout * 1000)  # Convert to milliseconds
    
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
            alt_cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
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

def main():
    print("=== VStar C24S Camera Connection Utility ===")
    
    # Default IP camera credentials for the working URL
    ip = "192.168.1.40"
    port = "10554"
    user = "admin"
    password = "12345678"
    path = "/tcp/av0_0"
    
    # Connect to the camera
    print(f"\nConnecting to VStar C24S camera at {ip}:{port}...")
    cap = connect_to_ip_camera(ip, port, user, password, path)
    
    if cap is None:
        print("Failed to connect to camera. Exiting.")
        return
    
    # Main operation loop
    while True:
        print("\nVStar C24S Camera Operations:")
        print("1. Display live camera feed")
        print("2. Take a picture")
        print("3. Record video")
        print("4. Show camera properties")
        print("5. Reconnect to camera")
        print("6. Change camera settings")
        print("7. Quit")
        
        choice = input("Enter your choice (1-7): ")
        
        if choice == '1':
            # Pass all camera parameters for proper reconnection
            display_camera_feed(cap, auto_reconnect=True, 
                               ip=ip, port=port, user=user, 
                               password=password, path=path)
            # Reconnect after feed closes
            cap = connect_to_ip_camera(ip, port, user, password, path)
        
        elif choice == '2':
            save_image(cap)
        
        elif choice == '3':
            duration = input("Enter recording duration in seconds (default: 10): ")
            try:
                duration = int(duration)
            except ValueError:
                duration = 10
            
            record_video(cap, duration)
            # Reconnect after recording
            cap = connect_to_ip_camera(ip, port, user, password, path)
        
        elif choice == '4':
            show_camera_properties(cap)
        
        elif choice == '5':
            print("Reconnecting to camera...")
            if cap is not None:
                cap.release()
            cap = connect_to_ip_camera(ip, port, user, password, path)
            if cap is None:
                print("Failed to reconnect. Exiting.")
                break
                
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
            
            # Reconnect with new settings
            print("Connecting with new settings...")
            if cap is not None:
                cap.release()
            cap = connect_to_ip_camera(ip, port, user, password, path)
            if cap is None:
                print("Failed to connect with new settings.")
                print("Would you like to revert to previous settings? (y/n)")
                if input().lower() == 'y':
                    # Revert to known working settings
                    ip = "192.168.1.40"
                    port = "10554"
                    user = "admin"
                    password = "12345678"
                    path = "/tcp/av0_0"
                    cap = connect_to_ip_camera(ip, port, user, password, path)
        
        elif choice == '7':
            if cap is not None:
                cap.release()
            print("Exiting...")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

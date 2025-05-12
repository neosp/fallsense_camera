#!/usr/bin/env python3
import cv2
import time
import sys
import os
import subprocess
import platform

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

def test_camera_connection():
    # Camera connection parameters for VStar C24S
    ip = "192.168.1.40"
    port = "10554"
    user = "admin"
    password = "12345678"
    path = "/tcp/av0_0"
    
    # Create the RTSP URL
    url = f"rtsp://{user}:{password}@{ip}:{port}{path}"
    
    print(f"Python version: {sys.version}")
    print(f"OpenCV version: {cv2.__version__}")
    print(f"Testing connection to VStar C24S camera at {ip}:{port}")
    print(f"Using URL: {url}")
    
    # Try to connect to the camera with improved parameters for VStar cameras
    # Set environment variables to mimic VLC's behavior
    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|analyzeduration;10000000|reorder_queue_size;10000|buffer_size;10485760|stimeout;1000000"
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    
    # Configure streaming parameters that may help with VStar C24S
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 10)
    
    # Give it a moment to connect
    print("Waiting for connection...")
    time.sleep(5)  # Extended wait time for VStar cameras
    
    # Try several frames to handle potential initial empty frames
    connected = False
    valid_frame = False
    frame = None
    
    for i in range(10):  # Try up to 10 frames
        if not cap.isOpened():
            break
            
        connected = True
        print(f"Connection established, trying to read frame {i+1}/10...")
        ret, test_frame = cap.read()
        
        if ret and test_frame is not None and test_frame.size > 0:
            print(f"Successfully captured frame {i+1}")
            frame = test_frame
            valid_frame = True
            break
        else:
            print(f"Frame {i+1} invalid or empty, trying again...")
            time.sleep(0.5)
    
    # Check if connected
    if connected:
        print("SUCCESS: Connected to VStar C24S camera!")
        
        if valid_frame:
            print("SUCCESS: Captured a valid frame!")
            
            # Create output directory if it doesn't exist
            output_dir = "test_captures"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Save the frame as a test image
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            test_image = os.path.join(output_dir, f"vstar_c24s_test_{timestamp}.jpg")
            cv2.imwrite(test_image, frame)
            print(f"Saved test image as {test_image}")
            
            # Try to determine if it's a color or grayscale image
            if len(frame.shape) == 3:
                channels = frame.shape[2]
                print(f"Image has {channels} channels (color)")
            else:
                print("Image is grayscale")
            
            # Get camera properties
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            print(f"Camera resolution: {width}x{height}")
            print(f"Camera FPS: {fps}")
            
            # Try to display the image briefly
            try:
                cv2.namedWindow("VStar C24S Test Frame", cv2.WINDOW_NORMAL)
                cv2.imshow("VStar C24S Test Frame", frame)
                print("Displaying test frame - press any key to continue...")
                cv2.waitKey(5000)  # Wait up to 5 seconds for a key press
                cv2.destroyAllWindows()
            except Exception as e:
                print(f"Could not display image: {e}")
        else:
            print("ERROR: Could not capture a valid frame. The camera may be connected but not streaming properly.")
            print("This is common with some VStar cameras.")
            print("\nWould you like to try opening the stream in VLC instead? (y/n)")
            choice = input()
            if choice.lower() == 'y':
                open_in_vlc(url)
    else:
        print("ERROR: Failed to connect to camera")
        print("Things to try:")
        print("1. Verify the camera is powered on and connected to the network")
        print("2. Check that the IP address and port are correct")
        print("3. Ensure username and password are correct")
        print("4. Try with a different RTSP URL format")
        print("5. Open in VLC instead (which is known to work with this camera)")
        
        print("\nWould you like to try opening the stream in VLC? (y/n)")
        choice = input()
        if choice.lower() == 'y':
            open_in_vlc(url)
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    print("Test completed.")

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
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)
        
        time.sleep(3)
        
        if cap.isOpened():
            print(f"SUCCESS: Connected with path: {path}")
            
            # Try to read a frame
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                print("SUCCESS: Captured a frame with this URL!")
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                test_image = f"vstar_c24s_test_{timestamp}_{path.replace('/', '_')}.jpg"
                cv2.imwrite(test_image, frame)
                print(f"Saved test image as {test_image}")
            else:
                print("Connected but could not capture a frame")
        else:
            print(f"Failed to connect with path: {path}")
        
        cap.release()
    
    print("\nPath testing completed. Check the saved images.")

if __name__ == "__main__":
    print("VStar C24S Camera Connection Test\n")
    
    print("Test options:")
    print("1. Test with OpenCV")
    print("2. Open directly in VLC (recommended)")
    print("3. Test multiple RTSP path formats")
    choice = input("Enter choice (1-3): ")
    
    # Create the default URL
    ip = "192.168.1.40"
    port = "10554"
    user = "admin"
    password = "12345678"
    path = "/tcp/av0_0"
    url = f"rtsp://{user}:{password}@{ip}:{port}{path}"
    
    if choice == "1":
        test_camera_connection()
    elif choice == "2":
        print("Opening stream directly in VLC (which is known to work with VStar C24S)...")
        open_in_vlc(url)
    elif choice == "3":
        # Imported from within the script to avoid issues with function definition order
        from camera_connect import test_alternative_paths
        test_alternative_paths()
    else:
        print("Invalid choice. Exiting.") 
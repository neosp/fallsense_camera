from camera_connect import connect_to_ip_camera
import cv2
import numpy as np
import time
import os
import datetime
import requests
import json

# API configuration
ALERT_API_ENDPOINT = "https://fallsense.onrender.com/api/alerts/device-alert"
DEVICE_ID = "SENSOR_001"

# Sensitivity configurations
SENSITIVITY_LEVELS = {
    'low': {
        'min_area': 7000,        # Larger area needed to detect movement
        'aspect_ratio': 1.8,     # More horizontal pose needed to detect fall
        'history': 150,          # Longer history for background subtraction
        'var_threshold': 60      # Less sensitive to changes
    },
    'medium': {
        'min_area': 5000,
        'aspect_ratio': 1.5,
        'history': 100,
        'var_threshold': 50
    },
    'high': {
        'min_area': 3000,        # Smaller area will trigger detection
        'aspect_ratio': 1.2,     # Less horizontal pose will trigger fall
        'history': 50,           # Shorter history for quicker detection
        'var_threshold': 40      # More sensitive to changes
    }
}

def detect_fall(frame, prev_frame, background_subtractor, sensitivity='medium'):
    """Detect falls using motion analysis"""
    if prev_frame is None:
        return False, frame
        
    # Get sensitivity parameters
    params = SENSITIVITY_LEVELS[sensitivity]
        
    # Apply background subtraction
    fgmask = background_subtractor.apply(frame)
    
    # Remove noise
    kernel = np.ones((5,5), np.uint8)
    fgmask = cv2.erode(fgmask, kernel, iterations=1)
    fgmask = cv2.dilate(fgmask, kernel, iterations=2)
    
    # Find contours of moving objects
    contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    is_fall = False
    for contour in contours:
        # Filter small contours using sensitivity parameter
        if cv2.contourArea(contour) < params['min_area']:
            continue
            
        # Get bounding box
        x, y, w, h = cv2.boundingRect(contour)
        
        # Calculate aspect ratio of bounding box
        aspect_ratio = float(w)/h
        
        # Detect fall based on sensitivity parameter
        if aspect_ratio > params['aspect_ratio']:
            is_fall = True
            # Draw red rectangle around fallen person
            cv2.rectangle(frame, (x,y), (x+w,y+h), (0,0,255), 2)
            cv2.putText(frame, f"FALL DETECTED! ({sensitivity})", (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,0,255), 2)
        else:
            # Draw green rectangle around standing person
            cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)
    
    return is_fall, frame

# Camera configuration
camera_ip = "172.20.10.4"
camera_port = "10554"
camera_user = "admin"
camera_pass = "12345678"
camera_path = "/tcp/av0_0"
display_camera = True  # Parameter to control camera display

def save_fall_image(frame, sensitivity):
    """Save a low quality image of the detected fall"""
    # Create fall_events directory if it doesn't exist
    save_dir = 'fall_events'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
        
    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(save_dir, f'fall_detected_{timestamp}.jpg')
    
    # Save image with low quality (30% compression quality)
    cv2.imwrite(filename, frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
    print(f"Saved fall detection image to {filename}")
    return filename

def send_alert_to_server(sensitivity):
    """Send fall alert to the server"""
    # Prepare alert data
    alert_data = {
        'device_id': DEVICE_ID,
        'type': 'fall_detected'
    }
    
    # Send POST request to the alert API endpoint
    try:
        response = requests.post(ALERT_API_ENDPOINT, json=alert_data)
        response.raise_for_status()  # Raise an error for bad responses
        print(f"Alert sent to server successfully")
    except requests.exceptions.RequestException as e:
        print(f"Error sending alert to server: {e}")

def run_fall_detection(display=True, sensitivity='medium'):
    global display_camera
    display_camera = display
    
    cap = connect_to_ip_camera(
        ip=camera_ip,
        port=camera_port,
        user=camera_user,
        password=camera_pass,
        path=camera_path
    )

    if cap is None or not cap.isOpened():
        print("Failed to connect to camera.")
        return
        
    print(f"Camera stream opened. Using {sensitivity} sensitivity. Press 'q' to quit.")
    
    # Initialize background subtractor with sensitivity parameters
    params = SENSITIVITY_LEVELS[sensitivity]
    background_subtractor = cv2.createBackgroundSubtractorMOG2(
        history=params['history'],
        varThreshold=params['var_threshold'],
        detectShadows=False
    )
    
    prev_frame = None
    last_fall_time = 0
    MIN_TIME_BETWEEN_ALERTS = 3  # Minimum seconds between fall alerts
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break
            
        # Resize frame for faster processing
        height, width = frame.shape[:2]
        new_width = int(width * 0.5)
        new_height = int(height * 0.5)
        frame = cv2.resize(frame, (new_width, new_height))
        
        # Detect falls with sensitivity
        is_fall, annotated_frame = detect_fall(frame, prev_frame, background_subtractor, sensitivity)
        
        # Alert if fall detected (with cooldown)
        if is_fall:
            current_time = time.time()
            if current_time - last_fall_time > MIN_TIME_BETWEEN_ALERTS:
                print(f"⚠️ FALL DETECTED! (Sensitivity: {sensitivity})")
                # Save the frame when fall is detected
                image_path = save_fall_image(annotated_frame, sensitivity)
                # Send alert to the server
                send_alert_to_server(sensitivity)
                last_fall_time = current_time
        
        # Update previous frame
        prev_frame = frame.copy()
        
        # Display frame only if display_camera is True
        if display_camera:
            cv2.imshow('Fall Detection Stream', annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
    cap.release()
    if display_camera:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fall Detection System')
    parser.add_argument('--no-display', action='store_true', 
                      help='Run without displaying the camera feed')
    parser.add_argument('--sensitivity', choices=['low', 'medium', 'high'],
                      default='medium', help='Detection sensitivity level')
    args = parser.parse_args()
    
    # Run fall detection with display and sensitivity parameters
    run_fall_detection(not args.no_display, args.sensitivity)
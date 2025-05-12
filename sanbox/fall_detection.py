#!/usr/bin/env python3
import cv2
import numpy as np
import time
import os
import datetime
import argparse
import threading
import subprocess
import platform
from camera_connect import connect_to_ip_camera, open_in_vlc

# Global variables
fall_detected = False
last_fall_time = 0
MIN_TIME_BETWEEN_ALERTS = 30  # Minimum seconds between fall alerts to prevent duplicates

class FallDetector:
    def __init__(self, 
                camera_ip="192.168.1.40", 
                camera_port="10554", 
                camera_user="admin", 
                camera_pass="12345678", 
                camera_path="/tcp/av0_0",
                history=20,
                threshold=800,
                min_area=500,
                display=True,
                record_falls=True,
                output_dir="fall_events"):
        """
        Initialize the fall detector with camera connection parameters and detection settings
        
        Parameters:
        - camera_* : Camera connection parameters
        - history: Background subtractor history length
        - threshold: Fall detection threshold (lower = more sensitive)
        - min_area: Minimum area for a contour to be considered
        - display: Whether to show video window
        - record_falls: Whether to record video when a fall is detected
        - output_dir: Directory to save fall recordings and screenshots
        """
        self.camera_ip = camera_ip
        self.camera_port = camera_port
        self.camera_user = camera_user
        self.camera_pass = camera_pass
        self.camera_path = camera_path
        self.history = history
        self.threshold = threshold
        self.min_area = min_area
        self.display = display
        self.record_falls = record_falls
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Initialize background subtractor
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=history, varThreshold=50, detectShadows=True)
        
        # Initialize video writer variables
        self.video_writer = None
        self.record_start_time = None
        self.recording = False
        
        # Initialize motion tracking variables
        self.prev_contours = []
        self.motion_history = []
        self.fall_count = 0
        self.stable_count = 0
        
        # Connect to the camera
        self.connect_camera()
    
    def connect_camera(self):
        """Connect to the camera using the provided parameters"""
        print(f"Connecting to camera at {self.camera_ip}:{self.camera_port}...")
        self.cap = connect_to_ip_camera(
            ip=self.camera_ip,
            port=self.camera_port,
            user=self.camera_user,
            password=self.camera_pass,
            path=self.camera_path
        )
        
        if self.cap is None or not self.cap.isOpened():
            print("Failed to connect to camera. Exiting.")
            return False
            
        print("Successfully connected to camera")
        return True
    
    def start_recording(self, frame):
        """Start recording a video when a fall is detected"""
        if self.recording:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = os.path.join(self.output_dir, f"fall_event_{timestamp}.mp4")
        
        # Get frame dimensions
        height, width = frame.shape[:2]
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(video_filename, fourcc, 10, (width, height))
        
        self.record_start_time = time.time()
        self.recording = True
        print(f"Started recording fall event to {video_filename}")
    
    def stop_recording(self):
        """Stop recording the fall event video"""
        if not self.recording:
            return
            
        self.video_writer.release()
        self.video_writer = None
        self.recording = False
        print("Stopped recording fall event")
    
    def save_screenshot(self, frame):
        """Save a screenshot of the detected fall"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = os.path.join(self.output_dir, f"fall_screenshot_{timestamp}.jpg")
        cv2.imwrite(screenshot_filename, frame)
        print(f"Saved fall screenshot to {screenshot_filename}")
    
    def alert_fall(self, frame):
        """Handle fall detection alert - save screenshot, record video, play sound, etc."""
        global fall_detected, last_fall_time
        
        # Check if enough time has passed since the last alert
        current_time = time.time()
        if current_time - last_fall_time < MIN_TIME_BETWEEN_ALERTS:
            return
            
        fall_detected = True
        last_fall_time = current_time
        
        print("\n🚨 FALL DETECTED! 🚨")
        self.save_screenshot(frame)
        
        if self.record_falls and not self.recording:
            self.start_recording(frame)
        
        # Play an alert sound
        self.play_alert_sound()
        
        # You could add additional alert methods here:
        # - Send email
        # - Send text message
        # - Call emergency services
        # - etc.
    
    def play_alert_sound(self):
        """Play an alert sound when a fall is detected"""
        try:
            if platform.system() == "Darwin":  # macOS
                subprocess.Popen(["afplay", "/System/Library/Sounds/Sosumi.aiff"])
            elif platform.system() == "Windows":
                import winsound
                winsound.Beep(2500, 1000)  # Frequency in Hz, duration in ms
            else:  # Linux
                subprocess.Popen(["aplay", "-q", "/usr/share/sounds/sound-icons/glass-breaking-2.wav"])
        except Exception as e:
            print(f"Could not play alert sound: {e}")
    
    def detect_fall(self, frame):
        """
        Process a frame to detect falls using motion analysis
        
        Returns True if a fall is detected, False otherwise
        """
        # Convert frame to grayscale for processing
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply GaussianBlur to reduce noise
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply background subtraction
        mask = self.bg_subtractor.apply(blur)
        
        # Apply threshold to isolate moving objects
        _, thresh = cv2.threshold(mask, 20, 255, cv2.THRESH_BINARY)
        
        # Perform morphological operations to remove noise
        kernel = np.ones((5, 5), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
        
        # Find contours of moving objects
        contours, _ = cv2.findContours(closing, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by area to ignore small movements
        significant_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > self.min_area]
        
        # If no significant contours are found, reset counters
        if not significant_contours:
            self.stable_count += 1
            if self.stable_count > 10:  # If stable for several frames
                self.fall_count = 0
                self.motion_history = []
            return False
        
        # Reset stable count since motion is detected
        self.stable_count = 0
        
        # Calculate motion features for each contour
        for contour in significant_contours:
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calculate aspect ratio and area
            aspect_ratio = float(w) / h if h > 0 else 0
            area = w * h
            
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Add to motion history
            self.motion_history.append((aspect_ratio, area))
            
            # Keep only recent history
            if len(self.motion_history) > 10:
                self.motion_history.pop(0)
            
            # Calculate rate of change in aspect ratio and area
            if len(self.motion_history) >= 3:
                prev_aspect, prev_area = self.motion_history[-3]
                current_aspect, current_area = self.motion_history[-1]
                
                aspect_change = abs(current_aspect - prev_aspect)
                area_change = abs(current_area - prev_area)
                
                # Fall detection logic: Sudden change in aspect ratio and area
                if aspect_change > 0.5 and area_change > self.threshold:
                    self.fall_count += 1
                    
                    # Visualize the fall detection
                    cv2.putText(frame, "POTENTIAL FALL", (x, y - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                    
                    # If multiple consecutive frames indicate a fall
                    if self.fall_count >= 3:
                        # Draw a red rectangle to highlight the fall
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)
                        cv2.putText(frame, "FALL DETECTED", (x, y - 10), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        return True
        
        return False
    
    def run(self):
        """Run the fall detection system"""
        if self.cap is None or not self.cap.isOpened():
            print("Camera is not connected. Please try connecting to the camera first.")
            return
        
        print("Starting fall detection. Press 'q' to quit.")
        
        try:
            while True:
                # Read a frame from the camera
                ret, frame = self.cap.read()
                
                if not ret:
                    print("Failed to grab frame. Reconnecting...")
                    self.cap.release()
                    if not self.connect_camera():
                        break
                    continue
                
                # Make a copy of the frame for display
                display_frame = frame.copy()
                
                # Add timestamp to the frame
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(display_frame, timestamp, (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Detect falls in the frame
                is_fall = self.detect_fall(display_frame)
                
                if is_fall:
                    self.alert_fall(display_frame)
                
                # Record video if in recording mode
                if self.recording:
                    self.video_writer.write(display_frame)
                    
                    # Add a red border to indicate recording
                    cv2.rectangle(display_frame, (0, 0), 
                                 (display_frame.shape[1], display_frame.shape[0]), 
                                 (0, 0, 255), 5)
                    
                    # Stop recording after 15 seconds
                    if time.time() - self.record_start_time > 15:
                        self.stop_recording()
                
                # Add status text
                status_text = "Status: "
                if self.recording:
                    status_text += "RECORDING FALL EVENT"
                    status_color = (0, 0, 255)
                elif fall_detected and time.time() - last_fall_time < 5:
                    status_text += "FALL DETECTED!"
                    status_color = (0, 0, 255)
                else:
                    status_text += "Monitoring"
                    status_color = (0, 255, 0)
                
                cv2.putText(display_frame, status_text, (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                
                # Display the frame if required
                if self.display:
                    cv2.imshow("Fall Detection", display_frame)
                    
                    # Press 'q' to exit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Small delay to reduce CPU usage
                time.sleep(0.01)
                
        except KeyboardInterrupt:
            print("Interrupted by user")
        finally:
            # Clean up
            if self.recording:
                self.stop_recording()
            
            if self.cap is not None:
                self.cap.release()
            
            cv2.destroyAllWindows()
            print("Fall detection stopped")

def main():
    """Main function to run the fall detector"""
    parser = argparse.ArgumentParser(description="Fall Detection System")
    
    # Camera parameters
    parser.add_argument("--ip", default="192.168.1.40", help="Camera IP address")
    parser.add_argument("--port", default="10554", help="Camera port")
    parser.add_argument("--user", default="admin", help="Camera username")
    parser.add_argument("--pass", dest="password", default="12345678", help="Camera password")
    parser.add_argument("--path", default="/tcp/av0_0", help="Camera RTSP path")
    
    # Detection parameters
    parser.add_argument("--threshold", type=int, default=800, 
                       help="Fall detection threshold (lower = more sensitive)")
    parser.add_argument("--min-area", type=int, default=500, 
                       help="Minimum area for a contour to be considered")
    parser.add_argument("--history", type=int, default=20, 
                       help="Background subtractor history length")
    
    # Other parameters
    parser.add_argument("--no-display", action="store_true", 
                       help="Don't display video window")
    parser.add_argument("--no-record", action="store_true", 
                       help="Don't record fall events")
    parser.add_argument("--output-dir", default="fall_events", 
                       help="Directory to save fall recordings and screenshots")
    parser.add_argument("--use-vlc", action="store_true", 
                       help="Use VLC to view the camera feed instead of OpenCV")
    
    args = parser.parse_args()
    
    if args.use_vlc:
        # Open the camera feed in VLC
        url = f"rtsp://{args.user}:{args.password}@{args.ip}:{args.port}{args.path}"
        open_in_vlc(url)
        print("Opening camera feed in VLC. Run this script again without --use-vlc to enable fall detection.")
        return
    
    # Create and run the fall detector
    detector = FallDetector(
        camera_ip=args.ip,
        camera_port=args.port,
        camera_user=args.user,
        camera_pass=args.password,
        camera_path=args.path,
        threshold=args.threshold,
        min_area=args.min_area,
        history=args.history,
        display=not args.no_display,
        record_falls=not args.no_record,
        output_dir=args.output_dir
    )
    
    detector.run()

if __name__ == "__main__":
    main() 
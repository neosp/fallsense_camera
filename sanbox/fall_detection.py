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
import requests
import json
import ssl
import urllib.request
from io import BytesIO
from camera_connect import connect_to_ip_camera, open_in_vlc
import mediapipe as mp

# Fix SSL certificate verification issue
ssl._create_default_https_context = ssl._create_unverified_context

# Global variables
fall_detected = False
last_fall_time = 0
MIN_TIME_BETWEEN_ALERTS = 5  # Minimum seconds between fall alerts to prevent duplicates
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1371493877063614494/UKIlJtVA8gKU0d4cO8PAu_pf1HpJ3CKagCwTv5rCrm4yM8anNGMxJajh1H2APmMH9b2y"

class HandDetector:
    def __init__(self, 
                camera_ip="192.168.1.40", 
                camera_port="10554", 
                camera_user="admin", 
                camera_pass="12345678", 
                camera_path="/tcp/av0_0",
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5,
                display=True,
                record_detections=False,
                output_dir="hand_events",
                discord_webhook=DISCORD_WEBHOOK,
                verify_ssl=False):
        """
        Initialize the hand detector with camera connection parameters and detection settings
        """
        self.camera_ip = camera_ip
        self.camera_port = camera_port
        self.camera_user = camera_user
        self.camera_pass = camera_pass
        self.camera_path = camera_path
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.display = display
        self.record_detections = record_detections
        self.output_dir = output_dir
        self.discord_webhook = discord_webhook
        self.verify_ssl = verify_ssl
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Initialize MediaPipe Hands
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Initialize hand detector
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,  # Detect up to 2 hands
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        # Initialize video writer variables
        self.video_writer = None
        self.record_start_time = None
        self.recording = False
        
        # Frame processing optimization
        self.frame_count = 0
        self.process_every_n_frames = 1  # Process every frame by default
        
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
        """Start recording a video when hands are detected"""
        if self.recording:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = os.path.join(self.output_dir, f"hand_event_{timestamp}.mp4")
        
        # Get frame dimensions
        height, width = frame.shape[:2]
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(video_filename, fourcc, 10, (width, height))
        
        self.record_start_time = time.time()
        self.recording = True
        print(f"Started recording hand event to {video_filename}")
    
    def stop_recording(self):
        """Stop recording the video"""
        if not self.recording:
            return
            
        self.video_writer.release()
        self.video_writer = None
        self.recording = False
        print("Stopped recording hand event")
    
    def save_screenshot(self, frame):
        """Save a screenshot of the detected hands"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = os.path.join(self.output_dir, f"hand_detected_{timestamp}.jpg")
        
        # Save the image with high quality (95% compression quality)
        cv2.imwrite(screenshot_filename, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"Saved hand screenshot to {screenshot_filename}")
        return screenshot_filename
    
    def send_discord_alert(self, num_hands, frame=None):
        """Send a hand detection alert to Discord webhook with image attachment"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"Sending Discord alert for {num_hands} hand(s) detected at {timestamp}")
            
            # Basic validation
            if not self.discord_webhook:
                print("No Discord webhook URL provided")
                return
            
            # Create the data payload with the message content
            data = {
                "content": f"👋 **HAND DETECTED at {timestamp}!** 👋\nNumber of hands: {num_hands}\nCamera: {self.camera_ip}:{self.camera_port}",
                "username": "Hand Detection System"
            }
            
            files = None
            if frame is not None:
                # Save the frame to a temporary file
                temp_image_path = os.path.join(self.output_dir, f"temp_hand_{timestamp}.jpg")
                cv2.imwrite(temp_image_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                # Prepare the file for upload
                files = {
                    'file': (f'hand_detected_{timestamp}.jpg', open(temp_image_path, 'rb'), 'image/jpeg')
                }
                
                print(f"Attaching image to Discord alert")
            
            print(f"Sending alert to Discord webhook")
            
            # Send the data with the image attachment if available
            if files:
                response = requests.post(
                    self.discord_webhook,
                    data={"payload_json": json.dumps(data)},
                    files=files,
                    verify=self.verify_ssl
                )
                # Clean up the temporary file
                os.remove(temp_image_path)
            else:
                # Send text-only alert if no frame is provided
                response = requests.post(
                    self.discord_webhook,
                    json=data,
                    verify=self.verify_ssl
                )
            
            print(f"Discord response: {response.status_code}")
            if response.status_code == 204 or response.status_code == 200:
                print("Discord alert sent successfully")
            else:
                print(f"Failed to send Discord alert: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending Discord alert: {e}")
            import traceback
            traceback.print_exc()
    
    def detect_hands(self, frame):
        """
        Process a frame to detect hands using MediaPipe
        
        Returns landmarks and annotated frame
        """
        # Resize frame to improve performance
        h, w = frame.shape[:2]
        target_height = 480  # Lower resolution for faster processing
        scale = target_height / h
        new_width = int(w * scale)
        
        # Use OpenCV resize (faster than numpy operations)
        small_frame = cv2.resize(frame, (new_width, target_height))
        
        # Convert frame to RGB (MediaPipe requires RGB)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Set image data as not writeable to improve performance
        rgb_frame.flags.writeable = False
        
        # Process the image and detect hands
        results = self.hands.process(rgb_frame)
        
        # Set image as writeable again
        rgb_frame.flags.writeable = True
        
        # Convert back to BGR for OpenCV
        processed_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        
        # Resize back to original dimensions if needed for display
        if self.display:
            processed_frame = cv2.resize(processed_frame, (w, h))
        
        # Draw hand landmarks on the processed frame
        if results.multi_hand_landmarks:
            num_hands = len(results.multi_hand_landmarks)
            
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_drawing.draw_landmarks(
                    processed_frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_drawing_styles.get_default_hand_landmarks_style(),
                    self.mp_drawing_styles.get_default_hand_connections_style()
                )
                
            # Add text showing number of hands detected
            cv2.putText(processed_frame, f"Hands Detected: {num_hands}", (10, 90), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            return True, processed_frame, num_hands
        
        return False, processed_frame, 0
    
    def run(self):
        """Run the hand detection system"""
        if self.cap is None or not self.cap.isOpened():
            print("Camera is not connected. Please try connecting to the camera first.")
            return
        
        print("Starting hand detection. Press 'q' to quit.")
        
        try:
            # For FPS calculation
            prev_time = time.time()
            frame_counter = 0
            fps = 0
            last_alert_time = 0
            
            while True:
                # Read a frame from the camera
                ret, frame = self.cap.read()
                
                if not ret:
                    print("Failed to grab frame. Reconnecting...")
                    self.cap.release()
                    if not self.connect_camera():
                        break
                    continue
                
                # Calculate FPS
                frame_counter += 1
                if (time.time() - prev_time) > 1:
                    fps = frame_counter
                    frame_counter = 0
                    prev_time = time.time()
                
                # Skip frames to improve performance
                self.frame_count += 1
                if self.frame_count % self.process_every_n_frames != 0:
                    continue
                
                # Make a copy of the frame for display
                display_frame = frame.copy()
                
                # Add timestamp to the frame
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(display_frame, timestamp, (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Detect hands in the frame
                hands_detected, display_frame, num_hands = self.detect_hands(display_frame)
                
                # If hands are detected, we can optionally send alerts and record
                if hands_detected:
                    # Send Discord alert (but not too frequently)
                    current_time = time.time()
                    if current_time - last_alert_time > MIN_TIME_BETWEEN_ALERTS:
                        if self.discord_webhook:
                            threading.Thread(
                                target=self.send_discord_alert,
                                args=(num_hands, display_frame.copy()),  # Pass the frame to the alert method
                                daemon=True
                            ).start()
                        last_alert_time = current_time
                    
                    # Save screenshot if recording is enabled
                    if self.record_detections and not self.recording:
                        self.save_screenshot(display_frame)
                        self.start_recording(display_frame)
                
                # Record video if in recording mode
                if self.recording:
                    self.video_writer.write(display_frame)
                    
                    # Add a green border to indicate recording
                    cv2.rectangle(display_frame, (0, 0), 
                                 (display_frame.shape[1], display_frame.shape[0]), 
                                 (0, 255, 0), 5)
                    
                    # Stop recording after 10 seconds
                    if time.time() - self.record_start_time > 10:
                        self.stop_recording()
                
                # Add status text
                status_text = "Status: "
                if self.recording:
                    status_text += "RECORDING HAND EVENT"
                    status_color = (0, 255, 0)
                elif hands_detected:
                    status_text += f"{num_hands} HAND(S) DETECTED!"
                    status_color = (0, 255, 0)
                else:
                    status_text += "Monitoring"
                    status_color = (255, 255, 255)
                
                cv2.putText(display_frame, status_text, (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                
                # Add FPS display
                cv2.putText(display_frame, f"FPS: {fps}", (display_frame.shape[1] - 120, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Display the frame if required
                if self.display:
                    cv2.imshow("Hand Detection", display_frame)
                    
                    # Press 'q' to exit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Small delay to reduce CPU usage
                time.sleep(0.005)
                
        except KeyboardInterrupt:
            print("Interrupted by user")
        finally:
            # Clean up
            if self.recording:
                self.stop_recording()
            
            if self.cap is not None:
                self.cap.release()
            
            # Free up MediaPipe resources
            self.hands.close()
            
            cv2.destroyAllWindows()
            print("Hand detection stopped")

class PoseDetector:
    def __init__(self, 
                camera_ip="192.168.1.40", 
                camera_port="10554", 
                camera_user="admin", 
                camera_pass="12345678", 
                camera_path="/tcp/av0_0",
                min_detection_confidence=0.7,
                min_tracking_confidence=0.5,
                display=True,
                record_falls=False,
                output_dir="fall_events",
                discord_webhook=DISCORD_WEBHOOK,
                verify_ssl=False):
        """
        Initialize the pose detector with camera connection parameters and detection settings
        """
        self.camera_ip = camera_ip
        self.camera_port = camera_port
        self.camera_user = camera_user
        self.camera_pass = camera_pass
        self.camera_path = camera_path
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        self.display = display
        self.record_falls = record_falls
        self.output_dir = output_dir
        self.discord_webhook = discord_webhook
        self.verify_ssl = verify_ssl
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Initialize MediaPipe Pose with lighter model
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Initialize pose detector with optimized parameters
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,  # Use lighter model (0=Lite, 1=Full, 2=Heavy)
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        # Initialize video writer variables
        self.video_writer = None
        self.record_start_time = None
        self.recording = False
        
        # Fall detection variables
        self.prev_landmarks = None
        self.fall_history = []
        self.fall_threshold = 0.3  # Threshold for vertical movement to detect fall
        self.stability_counter = 0
        
        # Frame processing optimization
        self.frame_count = 0
        self.process_every_n_frames = 2  # Process only every 2nd frame
        
        # One Euro Filter for landmark smoothing
        self.landmark_filter = LandmarkFilter(
            frequency=30.0,  # Estimated camera FPS
            min_cutoff=0.1,  # Minimum cutoff frequency
            beta=0.1,        # Speed coefficient
            dcutoff=1.0      # Derivative cutoff frequency
        )
        
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
        """Stop recording the video"""
        if not self.recording:
            return
            
        self.video_writer.release()
        self.video_writer = None
        self.recording = False
        print("Stopped recording fall event")
    
    def save_screenshot(self, frame):
        """Save a screenshot of the detected fall with enhanced image quality"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = os.path.join(self.output_dir, f"fall_detected_{timestamp}.jpg")
        
        # Create a copy of the frame for enhancement
        enhanced_frame = frame.copy()
        
        # Add a red border to indicate fall detection
        cv2.rectangle(enhanced_frame, (0, 0), 
                     (enhanced_frame.shape[1], enhanced_frame.shape[0]), 
                     (0, 0, 255), 5)
        
        # Add timestamp and "FALL DETECTED" text
        cv2.putText(enhanced_frame, f"FALL DETECTED: {timestamp}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Save the image with high quality (95% compression quality)
        cv2.imwrite(screenshot_filename, enhanced_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"Saved fall screenshot to {screenshot_filename}")
        return screenshot_filename
    
    def send_discord_alert(self, frame=None):
        """Send a fall detection alert to Discord webhook with image attachment"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"Sending Discord alert for fall detected at {timestamp}")
            
            # Basic validation
            if not self.discord_webhook:
                print("No Discord webhook URL provided")
                return
                
            # Create the data payload with the message content
            data = {
                "content": f"🚨 **FALL DETECTED at {timestamp}!** 🚨\nCamera: {self.camera_ip}:{self.camera_port}",
                "username": "Fall Detection System"
            }
            
            files = None
            if frame is not None:
                # Save the frame to a temporary file
                temp_image_path = os.path.join(self.output_dir, f"temp_fall_{timestamp}.jpg")
                cv2.imwrite(temp_image_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                # Prepare the file for upload
                files = {
                    'file': (f'fall_detected_{timestamp}.jpg', open(temp_image_path, 'rb'), 'image/jpeg')
                }
                
                print(f"Attaching image to Discord alert")
            
            print(f"Sending alert to Discord webhook")
            
            # Send the data with the image attachment if available
            if files:
                response = requests.post(
                    self.discord_webhook,
                    data={"payload_json": json.dumps(data)},
                    files=files,
                    verify=self.verify_ssl
                )
                # Clean up the temporary file
                os.remove(temp_image_path)
            else:
                # Send text-only alert if no frame is provided
                response = requests.post(
                    self.discord_webhook,
                    json=data,
                    verify=self.verify_ssl
                )
            
            print(f"Discord response: {response.status_code}")
            if response.status_code == 204 or response.status_code == 200:
                print("Discord alert sent successfully")
            else:
                print(f"Failed to send Discord alert: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending Discord alert: {e}")
            import traceback
            traceback.print_exc()
    
    def alert_fall(self, frame):
        """Handle fall detection alert - save screenshots, play sound, send alerts"""
        global fall_detected, last_fall_time
        
        # Check if enough time has passed since the last alert
        current_time = time.time()
        if current_time - last_fall_time < MIN_TIME_BETWEEN_ALERTS:
            return
            
        fall_detected = True
        last_fall_time = current_time
        
        print("\n🚨 FALL DETECTED! 🚨")
        
        # Save the primary screenshot
        screenshot_path = self.save_screenshot(frame)
        
        # If video recording is enabled and not already recording
        if self.record_falls and not self.recording:
            self.start_recording(frame)
        
        # Play an alert sound
        self.play_alert_sound()
        
        # Send alert to Discord if webhook is configured
        if self.discord_webhook:
            threading.Thread(
                target=self.send_discord_alert,
                args=(frame.copy(),),  # Pass the frame to the alert method
                daemon=True
            ).start()
    
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
    
    def detect_pose(self, frame):
        """
        Process a frame to detect human pose using MediaPipe
        
        Returns landmarks and annotated frame
        """
        # Resize frame to improve performance
        h, w = frame.shape[:2]
        target_height = 480  # Lower resolution for faster processing
        scale = target_height / h
        new_width = int(w * scale)
        
        # Use OpenCV resize (faster than numpy operations)
        small_frame = cv2.resize(frame, (new_width, target_height))
        
        # Convert frame to RGB (MediaPipe requires RGB)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Set image data as not writeable to improve performance
        rgb_frame.flags.writeable = False
        
        # Process the image and detect pose
        results = self.pose.process(rgb_frame)
        
        # Set image as writeable again
        rgb_frame.flags.writeable = True
        
        # Convert back to BGR for OpenCV
        processed_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        
        # Resize back to original dimensions if needed for display
        if self.display:
            processed_frame = cv2.resize(processed_frame, (w, h))
        
        return results, processed_frame, scale
    
    def detect_fall(self, frame):
        """
        Process a frame to detect falls using pose analysis
        
        Returns True if a fall is detected, False otherwise
        """
        # Skip frames to improve performance
        self.frame_count += 1
        if self.frame_count % self.process_every_n_frames != 0:
            # Just return the previous detection result if we're skipping this frame
            if hasattr(self, 'prev_display_frame') and hasattr(self, 'prev_fall_result'):
                return self.prev_fall_result, self.prev_display_frame
        
        # Detect pose in the frame
        results, annotated_frame, scale = self.detect_pose(frame)
        
        # Check if pose was detected
        if not results.pose_landmarks:
            self.stability_counter += 1
            if self.stability_counter > 10:  # If stable for several frames
                self.prev_landmarks = None
                self.fall_history = []
            
            self.prev_display_frame = annotated_frame
            self.prev_fall_result = False
            return False, annotated_frame
        
        # Reset stability counter when pose is detected
        self.stability_counter = 0
        
        # Draw pose landmarks on the frame (only when displaying)
        if self.display:
            self.mp_drawing.draw_landmarks(
                annotated_frame,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
            )
        
        # Get relevant landmarks and apply filtering for smoothness
        raw_landmarks = results.pose_landmarks.landmark
        landmarks = self.landmark_filter.process(raw_landmarks)
        
        # Get key landmarks for fall detection
        nose = landmarks[self.mp_pose.PoseLandmark.NOSE]
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
        
        # Calculate vertical position of key parts (normalized to frame height)
        shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
        hip_y = (left_hip.y + right_hip.y) / 2
        
        # Calculate shoulder-to-hip vertical distance ratio
        shoulder_hip_ratio = abs(shoulder_y - hip_y)
        
        # Check if this is the first frame with landmarks
        if self.prev_landmarks is None:
            self.prev_landmarks = {
                "nose": nose.y,
                "shoulder": shoulder_y,
                "hip": hip_y,
                "time": time.time()
            }
            
            self.prev_display_frame = annotated_frame
            self.prev_fall_result = False
            return False, annotated_frame
        
        # Calculate time since last landmark update
        time_diff = time.time() - self.prev_landmarks["time"]
        
        # Only check for falls if enough time has passed (reduce false positives)
        if time_diff > 0.5:  # Check every half second
            # Calculate vertical movement of key landmarks
            nose_movement = abs(nose.y - self.prev_landmarks["nose"])
            shoulder_movement = abs(shoulder_y - self.prev_landmarks["shoulder"])
            
            # Add current vertical position to fall history
            self.fall_history.append(shoulder_y)
            
            # Keep only recent history (last 10 frames)
            if len(self.fall_history) > 10:
                self.fall_history.pop(0)
            
            # Fall detection logic:
            # 1. Significant downward movement of shoulders
            # 2. Body is more horizontal than vertical (shoulder-hip ratio is small)
            
            # Check if shoulders moved significantly downward
            if (shoulder_movement > self.fall_threshold and 
                shoulder_y > self.prev_landmarks["shoulder"]):
                
                # Additional check: Ratio of shoulder-hip is small in a fall (body more horizontal)
                if shoulder_hip_ratio < 0.15:
                    # Add fall indicator to the frame
                    cv2.putText(annotated_frame, "FALL DETECTED", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # Update landmarks for next comparison
                    self.prev_landmarks = {
                        "nose": nose.y,
                        "shoulder": shoulder_y,
                        "hip": hip_y,
                        "time": time.time()
                    }
                    
                    self.prev_display_frame = annotated_frame
                    self.prev_fall_result = True
                    return True, annotated_frame
            
            # Update landmarks for next comparison
            self.prev_landmarks = {
                "nose": nose.y,
                "shoulder": shoulder_y,
                "hip": hip_y,
                "time": time.time()
            }
        
        # Add pose status to the frame
        vertical_position = 1 - shoulder_y  # Normalize to 0-1 scale (1 is standing)
        
        status = "Standing"
        status_color = (0, 255, 0)  # Green for standing
        
        # Determine status based on key points
        if shoulder_hip_ratio < 0.15:
            status = "Lying Down"
            status_color = (0, 165, 255)  # Orange for lying
        elif vertical_position < 0.5:
            status = "Sitting/Crouching"
            status_color = (0, 255, 255)  # Yellow for sitting
        
        # Display pose status
        cv2.putText(annotated_frame, f"Pose: {status}", (10, 90), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        
        self.prev_display_frame = annotated_frame
        self.prev_fall_result = False
        return False, annotated_frame
    
    def run(self):
        """Run the pose detection and fall detection system"""
        if self.cap is None or not self.cap.isOpened():
            print("Camera is not connected. Please try connecting to the camera first.")
            return
        
        print("Starting fall detection. Press 'q' to quit.")
        
        try:
            # For FPS calculation
            prev_time = time.time()
            frame_counter = 0
            fps = 0
            
            while True:
                # Read a frame from the camera
                ret, frame = self.cap.read()
                
                if not ret:
                    print("Failed to grab frame. Reconnecting...")
                    self.cap.release()
                    if not self.connect_camera():
                        break
                    continue
                
                # Calculate FPS
                frame_counter += 1
                if (time.time() - prev_time) > 1:
                    fps = frame_counter
                    frame_counter = 0
                    prev_time = time.time()
                
                # Make a copy of the frame for display
                display_frame = frame.copy()
                
                # Add timestamp to the frame
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(display_frame, timestamp, (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Detect falls in the frame
                is_fall, display_frame = self.detect_fall(display_frame)
                
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
                
                # Add FPS display
                cv2.putText(display_frame, f"FPS: {fps}", (display_frame.shape[1] - 120, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Display the frame if required
                if self.display:
                    cv2.imshow("Fall Detection", display_frame)
                    
                    # Press 'q' to exit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Small delay to reduce CPU usage, but less than before
                time.sleep(0.005)
                
        except KeyboardInterrupt:
            print("Interrupted by user")
        finally:
            # Clean up
            if self.recording:
                self.stop_recording()
            
            if self.cap is not None:
                self.cap.release()
            
            # Free up MediaPipe resources
            self.pose.close()
            
            cv2.destroyAllWindows()
            print("Fall detection stopped")

# One Euro Filter for landmark smoothing
class LandmarkFilter:
    def __init__(self, frequency=30.0, min_cutoff=1.0, beta=0.0, dcutoff=1.0):
        self.frequency = frequency
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self.filters = {}
    
    def process(self, landmarks):
        # Create a copy of landmarks to not modify the original
        smoothed_landmarks = []
        
        for i, landmark in enumerate(landmarks):
            if i not in self.filters:
                self.filters[i] = {
                    'x': OneEuroFilter(self.frequency, self.min_cutoff, self.beta, self.dcutoff),
                    'y': OneEuroFilter(self.frequency, self.min_cutoff, self.beta, self.dcutoff),
                    'z': OneEuroFilter(self.frequency, self.min_cutoff, self.beta, self.dcutoff),
                    'visibility': OneEuroFilter(self.frequency, self.min_cutoff, self.beta, self.dcutoff)
                }
            
            # Filter each coordinate
            x = self.filters[i]['x'].filter(landmark.x)
            y = self.filters[i]['y'].filter(landmark.y)
            z = self.filters[i]['z'].filter(landmark.z)
            visibility = self.filters[i]['visibility'].filter(landmark.visibility)
            
            # Create a new landmark with filtered values
            filtered_landmark = type('obj', (object,), {
                'x': x,
                'y': y,
                'z': z,
                'visibility': visibility
            })
            
            smoothed_landmarks.append(filtered_landmark)
        
        return smoothed_landmarks

class OneEuroFilter:
    def __init__(self, freq, mincutoff=1.0, beta=0.0, dcutoff=1.0):
        self.freq = freq
        self.mincutoff = mincutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self.x_prev = None
        self.dx_prev = None
        self.t_prev = None
    
    def filter(self, x):
        t = time.time()
        
        if self.x_prev is None:
            self.x_prev = x
            self.t_prev = t
            return x
        
        # Calculate the timestep
        dt = t - self.t_prev
        
        # Avoid division by zero
        if dt == 0:
            return self.x_prev
            
        # Adjust alpha based on the timestep
        alpha = self._calculate_alpha(dt, self.mincutoff)
        
        # Calculate the derivative
        dx = (x - self.x_prev) / dt
        
        # Filter the derivative
        if self.dx_prev is None:
            self.dx_prev = dx
        else:
            dx_alpha = self._calculate_alpha(dt, self.dcutoff)
            dx = dx_alpha * dx + (1 - dx_alpha) * self.dx_prev
        
        # Calculate the cutoff frequency
        cutoff = self.mincutoff + self.beta * abs(dx)
        
        # Calculate the smoothing factor
        alpha = self._calculate_alpha(dt, cutoff)
        
        # Filter the signal
        filtered_x = alpha * x + (1 - alpha) * self.x_prev
        
        # Save values for next iteration
        self.x_prev = filtered_x
        self.dx_prev = dx
        self.t_prev = t
        
        return filtered_x
    
    def _calculate_alpha(self, dt, cutoff):
        # Formula for alpha based on cutoff frequency
        tau = 1.0 / (2 * np.pi * cutoff)
        te = dt / tau
        alpha = 1.0 / (1.0 + te)
        return alpha

class FaceDetector:
    def __init__(self, 
                camera_ip="192.168.1.40", 
                camera_port="10554", 
                camera_user="admin", 
                camera_pass="12345678", 
                camera_path="/tcp/av0_0",
                min_detection_confidence=0.7,
                display=True,
                record_detections=False,
                output_dir="face_events",
                discord_webhook=DISCORD_WEBHOOK,
                verify_ssl=False):
        """
        Initialize the face detector with camera connection parameters and detection settings
        """
        self.camera_ip = camera_ip
        self.camera_port = camera_port
        self.camera_user = camera_user
        self.camera_pass = camera_pass
        self.camera_path = camera_path
        self.min_detection_confidence = min_detection_confidence
        self.display = display
        self.record_detections = record_detections
        self.output_dir = output_dir
        self.discord_webhook = discord_webhook
        self.verify_ssl = verify_ssl
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Initialize MediaPipe Face Detection
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        
        # Model selection: 0 for short-range detection (faces within 2 meters), 
        # 1 for full-range detection (faces within 5 meters)
        self.model_selection = 1
        
        # Initialize face detector with the selected model
        self.face_detector = self.mp_face_detection.FaceDetection(
            model_selection=self.model_selection,
            min_detection_confidence=min_detection_confidence
        )
        
        # Initialize video writer variables
        self.video_writer = None
        self.record_start_time = None
        self.recording = False
        
        # Frame processing optimization
        self.frame_count = 0
        self.process_every_n_frames = 1  # Process every frame by default
        
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
        """Start recording a video when faces are detected"""
        if self.recording:
            return
            
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = os.path.join(self.output_dir, f"face_event_{timestamp}.mp4")
        
        # Get frame dimensions
        height, width = frame.shape[:2]
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(video_filename, fourcc, 10, (width, height))
        
        self.record_start_time = time.time()
        self.recording = True
        print(f"Started recording face event to {video_filename}")
    
    def stop_recording(self):
        """Stop recording the video"""
        if not self.recording:
            return
            
        self.video_writer.release()
        self.video_writer = None
        self.recording = False
        print("Stopped recording face event")
    
    def save_screenshot(self, frame):
        """Save a screenshot of the detected faces"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_filename = os.path.join(self.output_dir, f"face_detected_{timestamp}.jpg")
        
        # Save the image with high quality (95% compression quality)
        cv2.imwrite(screenshot_filename, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        print(f"Saved face screenshot to {screenshot_filename}")
        return screenshot_filename
    
    def send_discord_alert(self, num_faces, frame=None):
        """Send a face detection alert to Discord webhook with image attachment"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"Sending Discord alert for {num_faces} face(s) detected at {timestamp}")
            
            # Basic validation
            if not self.discord_webhook:
                print("No Discord webhook URL provided")
                return
            
            # Create the data payload with the message content
            data = {
                "content": f"👤 **FACE DETECTED at {timestamp}!** 👤\nNumber of faces: {num_faces}\nCamera: {self.camera_ip}:{self.camera_port}",
                "username": "Face Detection System"
            }
            
            files = None
            if frame is not None:
                # Save the frame to a temporary file
                temp_image_path = os.path.join(self.output_dir, f"temp_face_{timestamp}.jpg")
                cv2.imwrite(temp_image_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                
                # Prepare the file for upload
                files = {
                    'file': (f'face_detected_{timestamp}.jpg', open(temp_image_path, 'rb'), 'image/jpeg')
                }
                
                print(f"Attaching image to Discord alert")
            
            print(f"Sending alert to Discord webhook")
            
            # Send the data with the image attachment if available
            if files:
                response = requests.post(
                    self.discord_webhook,
                    data={"payload_json": json.dumps(data)},
                    files=files,
                    verify=self.verify_ssl
                )
                # Clean up the temporary file
                os.remove(temp_image_path)
            else:
                # Send text-only alert if no frame is provided
                response = requests.post(
                    self.discord_webhook,
                    json=data,
                    verify=self.verify_ssl
                )
            
            print(f"Discord response: {response.status_code}")
            if response.status_code == 204 or response.status_code == 200:
                print("Discord alert sent successfully")
            else:
                print(f"Failed to send Discord alert: {response.status_code}")
                
        except Exception as e:
            print(f"Error sending Discord alert: {e}")
            import traceback
            traceback.print_exc()
    
    def detect_faces(self, frame):
        """
        Process a frame to detect faces using MediaPipe
        
        Returns detections and annotated frame
        """
        # Resize frame to improve performance
        h, w = frame.shape[:2]
        target_height = 480  # Lower resolution for faster processing
        scale = target_height / h
        new_width = int(w * scale)
        
        # Use OpenCV resize (faster than numpy operations)
        small_frame = cv2.resize(frame, (new_width, target_height))
        
        # Convert frame to RGB (MediaPipe requires RGB)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Set image data as not writeable to improve performance
        rgb_frame.flags.writeable = False
        
        # Process the image and detect faces
        results = self.face_detector.process(rgb_frame)
        
        # Set image as writeable again
        rgb_frame.flags.writeable = True
        
        # Convert back to BGR for OpenCV
        processed_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
        
        # Resize back to original dimensions if needed for display
        if self.display:
            processed_frame = cv2.resize(processed_frame, (w, h))
        
        # Draw face detections on the processed frame
        if results.detections:
            num_faces = len(results.detections)
            
            for detection in results.detections:
                # Get bounding box coordinates
                bbox = detection.location_data.relative_bounding_box
                
                # Convert normalized coordinates to pixel coordinates
                x_min = int(bbox.xmin * w)
                y_min = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                
                # Draw bounding box
                cv2.rectangle(processed_frame, (x_min, y_min), (x_min + width, y_min + height), (0, 255, 0), 2)
                
                # Add confidence score
                confidence = detection.score[0]
                cv2.putText(processed_frame, f"{confidence:.2f}", (x_min, y_min - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Extract and draw facial landmarks
                for idx, landmark in enumerate(detection.location_data.relative_keypoints):
                    # Convert normalized coordinates to pixel coordinates
                    landmark_x = int(landmark.x * w)
                    landmark_y = int(landmark.y * h)
                    
                    # Draw landmarks
                    cv2.circle(processed_frame, (landmark_x, landmark_y), 5, (255, 0, 0), -1)
                
            # Add text showing number of faces detected
            cv2.putText(processed_frame, f"Faces Detected: {num_faces}", (10, 90), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            return True, processed_frame, num_faces
        
        return False, processed_frame, 0
    
    def run(self):
        """Run the face detection system"""
        if self.cap is None or not self.cap.isOpened():
            print("Camera is not connected. Please try connecting to the camera first.")
            return
        
        print("Starting face detection. Press 'q' to quit.")
        
        try:
            # For FPS calculation
            prev_time = time.time()
            frame_counter = 0
            fps = 0
            last_alert_time = 0
            
            while True:
                # Read a frame from the camera
                ret, frame = self.cap.read()
                
                if not ret:
                    print("Failed to grab frame. Reconnecting...")
                    self.cap.release()
                    if not self.connect_camera():
                        break
                    continue
                
                # Calculate FPS
                frame_counter += 1
                if (time.time() - prev_time) > 1:
                    fps = frame_counter
                    frame_counter = 0
                    prev_time = time.time()
                
                # Skip frames to improve performance
                self.frame_count += 1
                if self.frame_count % self.process_every_n_frames != 0:
                    continue
                
                # Make a copy of the frame for display
                display_frame = frame.copy()
                
                # Add timestamp to the frame
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cv2.putText(display_frame, timestamp, (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Detect faces in the frame
                faces_detected, display_frame, num_faces = self.detect_faces(display_frame)
                
                # If faces are detected, we can optionally send alerts and record
                if faces_detected:
                    # Send Discord alert (but not too frequently)
                    current_time = time.time()
                    if current_time - last_alert_time > MIN_TIME_BETWEEN_ALERTS:
                        if self.discord_webhook:
                            threading.Thread(
                                target=self.send_discord_alert,
                                args=(num_faces, display_frame.copy()),  # Pass the frame to the alert method
                                daemon=True
                            ).start()
                        last_alert_time = current_time
                    
                    # Save screenshot if recording is enabled
                    if self.record_detections and not self.recording:
                        self.save_screenshot(display_frame)
                        self.start_recording(display_frame)
                
                # Record video if in recording mode
                if self.recording:
                    self.video_writer.write(display_frame)
                    
                    # Add a green border to indicate recording
                    cv2.rectangle(display_frame, (0, 0), 
                                 (display_frame.shape[1], display_frame.shape[0]), 
                                 (0, 255, 0), 5)
                    
                    # Stop recording after 10 seconds
                    if time.time() - self.record_start_time > 10:
                        self.stop_recording()
                
                # Add status text
                status_text = "Status: "
                if self.recording:
                    status_text += "RECORDING FACE EVENT"
                    status_color = (0, 255, 0)
                elif faces_detected:
                    status_text += f"{num_faces} FACE(S) DETECTED!"
                    status_color = (0, 255, 0)
                else:
                    status_text += "Monitoring"
                    status_color = (255, 255, 255)
                
                cv2.putText(display_frame, status_text, (10, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
                
                # Add FPS display
                cv2.putText(display_frame, f"FPS: {fps}", (display_frame.shape[1] - 120, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Display the frame if required
                if self.display:
                    cv2.imshow("Face Detection", display_frame)
                    
                    # Press 'q' to exit
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Small delay to reduce CPU usage
                time.sleep(0.005)
                
        except KeyboardInterrupt:
            print("Interrupted by user")
        finally:
            # Clean up
            if self.recording:
                self.stop_recording()
            
            if self.cap is not None:
                self.cap.release()
            
            cv2.destroyAllWindows()
            print("Face detection stopped")

def main():
    """Main function to run the detector"""
    parser = argparse.ArgumentParser(description="MediaPipe Detection System")
    
    # Camera parameters
    parser.add_argument("--ip", default="192.168.1.40", help="Camera IP address")
    parser.add_argument("--port", default="10554", help="Camera port")
    parser.add_argument("--user", default="admin", help="Camera username")
    parser.add_argument("--pass", dest="password", default="12345678", help="Camera password")
    parser.add_argument("--path", default="/tcp/av0_0", help="Camera RTSP path")
    
    # Detection parameters
    parser.add_argument("--min-detection-confidence", type=float, default=0.7, 
                       help="Minimum confidence for detection")
    parser.add_argument("--min-tracking-confidence", type=float, default=0.5, 
                       help="Minimum confidence for tracking")
    parser.add_argument("--fall-threshold", type=float, default=0.3, 
                       help="Threshold for vertical movement to detect fall")
    
    # Performance parameters
    parser.add_argument("--skip-frames", type=int, default=2,
                       help="Process every nth frame (higher values increase speed)")
    parser.add_argument("--resolution", type=int, default=480,
                       help="Processing resolution (lower values increase speed)")
    
    # Other parameters
    parser.add_argument("--no-display", action="store_true", 
                       help="Don't display video window")
    parser.add_argument("--record-video", action="store_true", 
                       help="Record video of detections")
    parser.add_argument("--output-dir", default="events", 
                       help="Directory to save detection screenshots and videos")
    parser.add_argument("--use-vlc", action="store_true", 
                       help="Use VLC to view the camera feed instead of OpenCV")
    parser.add_argument("--discord-webhook", default=DISCORD_WEBHOOK,
                      help="Discord webhook URL for sending alerts")
    parser.add_argument("--verify-ssl", action="store_true",
                      help="Verify SSL certificates for HTTPS requests")
    
    # Mode selection
    parser.add_argument("--mode", choices=["fall", "hand", "face"], default="fall",
                      help="Detection mode: fall for fall detection, hand for hand detection, face for face detection")
    
    args = parser.parse_args()
    
    if args.use_vlc:
        # Open the camera feed in VLC
        url = f"rtsp://{args.user}:{args.password}@{args.ip}:{args.port}{args.path}"
        open_in_vlc(url)
        print("Opening camera feed in VLC. Run this script again without --use-vlc to enable detection.")
        return
    
    if args.mode == "fall":
        print("\n=== MediaPipe Fall Detection System ===")
        print("System will detect falls using pose estimation")
        if args.record_video:
            print("Video recording is enabled")
        else:
            print("Video recording is disabled")
        
        print("Discord notifications are enabled")
        if not args.verify_ssl:
            print("SSL certificate verification is disabled")
        
        # Create and run the pose detector
        detector = PoseDetector(
            camera_ip=args.ip,
            camera_port=args.port,
            camera_user=args.user,
            camera_pass=args.password,
            camera_path=args.path,
            min_detection_confidence=args.min_detection_confidence,
            min_tracking_confidence=args.min_tracking_confidence,
            display=not args.no_display,
            record_falls=args.record_video,
            output_dir=args.output_dir,
            discord_webhook=args.discord_webhook,
            verify_ssl=args.verify_ssl
        )
        
        # Set the performance parameters
        detector.fall_threshold = args.fall_threshold
        detector.process_every_n_frames = args.skip_frames
        
        detector.run()
    
    elif args.mode == "hand":
        print("\n=== MediaPipe Hand Detection System ===")
        print("System will detect hands and send alerts")
        if args.record_video:
            print("Video recording is enabled")
        else:
            print("Video recording is disabled")
        
        print("Discord notifications are enabled")
        if not args.verify_ssl:
            print("SSL certificate verification is disabled")
        
        # Create and run the hand detector
        detector = HandDetector(
            camera_ip=args.ip,
            camera_port=args.port,
            camera_user=args.user,
            camera_pass=args.password,
            camera_path=args.path,
            min_detection_confidence=args.min_detection_confidence,
            min_tracking_confidence=args.min_tracking_confidence,
            display=not args.no_display,
            record_detections=args.record_video,
            output_dir=os.path.join(args.output_dir, "hands"),
            discord_webhook=args.discord_webhook,
            verify_ssl=args.verify_ssl
        )
        
        # Set the performance parameters
        detector.process_every_n_frames = args.skip_frames
        
        detector.run()
    
    elif args.mode == "face":
        print("\n=== MediaPipe Face Detection System ===")
        print("System will detect faces and send alerts")
        if args.record_video:
            print("Video recording is enabled")
        else:
            print("Video recording is disabled")
        
        print("Discord notifications are enabled")
        if not args.verify_ssl:
            print("SSL certificate verification is disabled")
        
        # Create and run the face detector
        detector = FaceDetector(
            camera_ip=args.ip,
            camera_port=args.port,
            camera_user=args.user,
            camera_pass=args.password,
            camera_path=args.path,
            min_detection_confidence=args.min_detection_confidence,
            display=not args.no_display,
            record_detections=args.record_video,
            output_dir=os.path.join(args.output_dir, "faces"),
            discord_webhook=args.discord_webhook,
            verify_ssl=args.verify_ssl
        )
        
        # Set the performance parameters
        detector.process_every_n_frames = args.skip_frames
        
        detector.run()

if __name__ == "__main__":
    main() 
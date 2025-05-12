# VStar C24S Camera Connection Tool

This tool provides a simple way to connect to and interact with a VStar C24S IP camera. It now includes options to use either OpenCV or VLC for video streaming.

## Features

- Connect to VStar C24S camera via RTSP
- Display live camera feed using OpenCV
- Open stream directly in VLC (recommended for reliable playback)
- Capture still images
- Record video
- View camera properties
- Auto-reconnect if connection is lost
- Test various connection URLs

## Prerequisites

- Python 3.6+
- OpenCV (`opencv-python`)
- NumPy
- VLC Media Player 3.0+ (highly recommended)

Install required packages:

```bash
pip install opencv-python numpy
```

You should also install VLC media player from <https://www.videolan.org/vlc/>

## VStar C24S Camera Connection

The tool is configured to work with the following camera settings:

- Camera Model: VStar C24S
- IP: 192.168.1.40
- Port: 10554
- Username: admin
- Password: 12345678
- RTSP Path: /tcp/av0_0
- Full URL: rtsp://admin:12345678@192.168.1.40:10554/tcp/av0_0

## VLC Integration

Since VLC 3.0.21 is confirmed to work with the camera stream, this tool now includes:

1. **Direct VLC launch option**: Opens the camera stream directly in VLC
2. **VLC-inspired settings**: Uses VLC's connection parameters for better OpenCV streaming

## Usage

### Test Connection

To quickly test if the VStar C24S camera is accessible:

```bash
python test_connection.py
```

This will:

1. Attempt to connect to the camera
2. Try multiple connection attempts to handle initial connection issues
3. Capture a test frame and save it
4. Display camera properties

The test script also has an option to try multiple RTSP URL formats to find the one that works best with your VStar C24S.

### Full Camera Tool

For the complete interface with all options:

```bash
python camera_connect.py
```

### Camera Operations

Once connected, you can:

1. **Connect and display with OpenCV**
   - Uses OpenCV to show real-time video from the VStar C24S camera
   - If this doesn't work well, you'll be prompted to try VLC instead

2. **Take a picture**
   - Captures and saves a still image from the camera
   - Images are saved in the "captures" directory

3. **Record video**
   - Records a video for a specified duration
   - Videos are saved in the "videos" directory

4. **Show camera properties**
   - Displays technical information about the camera connection

5. **Open stream in VLC (recommended)**
   - Launches VLC media player with the camera stream URL
   - This option is recommended since VLC 3.0.21 is confirmed to work with this camera

6. **Change camera settings**
   - Allows you to modify connection parameters if needed

7. **Quit**
   - Exits the program

## VStar C24S Specific Troubleshooting

The VStar C24S camera may have specific connection issues:

1. **OpenCV cannot display video but VLC works**
   - Use option 5 to open the stream directly in VLC
   - This is a common issue with some IP cameras where VLC handles the stream better than OpenCV

2. **Connection but no video**
   - This script includes special handling for this camera's behavior
   - It tries multiple reconnection attempts and stream buffering settings
   - The TCP transport setting may improve reliability

3. **Stream timeouts**
   - If you experience frequent timeouts, try:
   - Using the VLC option which handles network instability better
   - Using the "6. Change camera settings" option to try different ports

## Using in Your Own Code

You can import the functions from camera_connect.py into your own code:

```python
from camera_connect import connect_to_ip_camera, display_camera_feed, open_in_vlc

# Connect to the VStar C24S camera with OpenCV
cap = connect_to_ip_camera(ip="192.168.1.40", port="10554", 
                          user="admin", password="12345678",
                          path="/tcp/av0_0")

# If OpenCV connection works
if cap is not None:
    # Do something with the camera...
    display_camera_feed(cap)
    cap.release()
else:
    # If OpenCV fails, use VLC instead
    url = "rtsp://admin:12345678@192.168.1.40:10554/tcp/av0_0"
    open_in_vlc(url)

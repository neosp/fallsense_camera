# FallSense Camera

A real-time system for detecting falls and hand movements using computer vision and MediaPipe.

## Features

- Real-time fall detection using pose estimation
- Hand detection mode for testing
- Discord alert system with image attachments
- Video recording of detection events
- Optimized for performance with MediaPipe

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/fallsense_camera.git
cd fallsense_camera
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. If you're using a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### Fall Detection Mode

```bash
cd sanbox
python fall_detection.py --camera_ip 192.168.1.40 --camera_port 10554
```

### Hand Detection Test Mode

```bash
cd sanbox
python fall_detection.py --test_mode hand --camera_ip 192.168.1.40 --camera_port 10554
```

### Configuration Options

- `--camera_ip`: IP address of the camera (default: 192.168.1.40)
- `--camera_port`: Port for the camera (default: 10554)
- `--camera_user`: Username for camera authentication (default: admin)
- `--camera_pass`: Password for camera authentication (default: 12345678)
- `--display`: Enable display window (default: True)
- `--test_mode`: Test mode to run ('hand' or None) (default: None)
- `--record`: Enable recording of detection events (default: False)
- `--output_dir`: Directory to save recordings (default: 'fall_events' or 'hand_events')

## Troubleshooting

If you encounter SSL certificate verification issues, the system automatically bypasses SSL verification. If you have other connection issues, try:

1. Checking camera IP, port, username and password
2. Ensuring your network allows RTSP connections
3. Installing VLC media player for alternative viewing

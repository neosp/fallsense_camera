# Fall Detection System for VStar C24S Camera

This system provides automated fall detection using computer vision and motion analysis with your VStar C24S IP camera.

## Features

- Real-time fall detection using motion analysis
- Automatic recording of fall events
- Screenshots of detected falls
- Alert system with sound notifications
- Configurable sensitivity parameters
- Works with your VStar C24S camera
- Option to use VLC for viewing while detection runs in background

## Prerequisites

- Python 3.6+
- OpenCV (`opencv-python`)
- NumPy
- Your VStar C24S camera properly connected to the network
- VLC media player (optional, for viewing)

## Installation

Install the required Python packages:

```bash
pip install opencv-python numpy
```

## How It Works

The fall detection algorithm:

1. Establishes connection to your VStar C24S camera
2. Performs background subtraction to identify moving objects
3. Tracks motion patterns and analyzes changes in aspect ratio and area
4. Detects sudden changes that are characteristic of falls
5. Triggers alerts and recordings when falls are detected

## Usage

### Basic Usage

Run the fall detection with default settings:

```bash
python fall_detection.py
```

### Command Line Options

```
usage: fall_detection.py [-h] [--ip IP] [--port PORT] [--user USER]
                         [--pass PASSWORD] [--path PATH] [--threshold THRESHOLD]
                         [--min-area MIN_AREA] [--history HISTORY]
                         [--no-display] [--no-record] [--output-dir OUTPUT_DIR]
                         [--use-vlc]

Fall Detection System

optional arguments:
  -h, --help            show this help message and exit
  --ip IP               Camera IP address (default: 192.168.1.40)
  --port PORT           Camera port (default: 10554)
  --user USER           Camera username (default: admin)
  --pass PASSWORD       Camera password (default: 12345678)
  --path PATH           Camera RTSP path (default: /tcp/av0_0)
  --threshold THRESHOLD
                        Fall detection threshold (lower = more sensitive)
                        (default: 800)
  --min-area MIN_AREA   Minimum area for a contour to be considered
                        (default: 500)
  --history HISTORY     Background subtractor history length (default: 20)
  --no-display          Don't display video window
  --no-record           Don't record fall events
  --output-dir OUTPUT_DIR
                        Directory to save fall recordings and screenshots
                        (default: fall_events)
  --use-vlc             Use VLC to view the camera feed instead of OpenCV
```

### Adjusting Sensitivity

If you're getting too many false positives:

```bash
python fall_detection.py --threshold 1200 --min-area 800
```

If you're missing falls (not sensitive enough):

```bash
python fall_detection.py --threshold 500 --min-area 300
```

### Using with VLC

If you want to view the camera feed in VLC (for better video quality) while running the fall detection:

```bash
python fall_detection.py --use-vlc
```

This will open the camera feed in VLC. You can then run another instance of the script without the `--use-vlc` option (and with `--no-display` if you don't need to see the detection visualization) to perform the fall detection in the background.

## Output Files

Fall events are saved in the `fall_events` directory (or the directory specified with `--output-dir`):

- `fall_screenshot_YYYYMMDD_HHMMSS.jpg`: Screenshot of the detected fall
- `fall_event_YYYYMMDD_HHMMSS.mp4`: Video recording of the fall (15 seconds)

## Limitations

- The system works best with good lighting conditions
- Detection accuracy depends on camera placement (overhead or side view works best)
- May generate false positives with quick movements
- Performance depends on your computer's processing power

## Troubleshooting

1. **Camera Connection Issues**
   - Make sure your camera is powered on and connected to the network
   - Verify IP address, port, username, and password
   - Try using the `camera_connect.py` script to test your connection

2. **No Detection**
   - Adjust the `--threshold` and `--min-area` parameters
   - Ensure proper camera placement for good visibility
   - Check if there's enough lighting

3. **Too Many False Alarms**
   - Increase the `--threshold` value
   - Increase the `--min-area` value
   - Adjust camera position to reduce background movement

4. **Poor Performance**
   - Run with `--no-display` to improve performance
   - Consider reducing the camera resolution if possible
   - Close other resource-intensive applications

## Extending the System

The fall detection system can be extended with:

1. **Email/SMS Notifications**
   - Add code to the `alert_fall` method to send emails or SMS

2. **Integration with Emergency Services**
   - Add API calls to emergency service providers

3. **Cloud Storage**
   - Upload fall events to cloud storage for remote access

4. **Mobile App Notifications**
   - Integrate with services like Firebase to send push notifications

## License

This tool is provided for educational and safety monitoring purposes.

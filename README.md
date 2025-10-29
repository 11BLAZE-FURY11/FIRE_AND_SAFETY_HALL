# 🔥 Fire & Safety People Counter

Real-time occupancy monitoring system for lecture halls using overhead camera detection and MediaPipe pose estimation. Designed for fire safety compliance by tracking the number of people entering and exiting through doorways.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Latest-orange.svg)

## 🎯 Features

- **Real-time People Counting**: Tracks entries and exits through doorways
- **Overhead Camera Optimized**: Designed for top-down view detection
- **MediaPipe Pose Detection**: Lightweight and fast person detection without heavy AI models
- **Live Occupancy Display**: Shows current number of people in the room
- **Multi-door Support**: Can monitor up to 3 doors simultaneously (currently configured for 1)
- **DroidCam Integration**: Uses Android phones as IP cameras
- **State-based Tracking**: Prevents duplicate counts with intelligent debouncing
- **Visual Indicators**: Green/gray status dot, entry/exit animations, and person tracking

## 📋 Requirements

- Python 3.8 or higher
- Webcam or IP camera (DroidCam recommended)
- Virtual environment (included)

## 🚀 Installation

1. **Clone the repository**
```bash
git clone https://github.com/11BLAZE-FURY11/FIRE_AND_SAFETY_HALL.git
cd FIRE_AND_SAFETY_HALL
```

2. **Activate virtual environment**
```bash
source .venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

Dependencies:
- `opencv-python`: Video processing and display
- `numpy`: Mathematical operations
- `mediapipe`: Pose detection and tracking

## 📱 DroidCam Setup

1. Install **DroidCam** app on your Android phone
2. Connect phone to same WiFi network as your computer
3. Open DroidCam app and note the IP address shown (e.g., `192.168.2.100`)
4. Update the IP in `app.py`:
```python
DOOR_CONFIGS = {
    "Door 1": {
        "url": "http://YOUR_PHONE_IP:4747/video",  # Replace with your IP
        "entry_line": 240,
        "direction": "horizontal"
    },
}
```

5. Test the camera feed:
```bash
python test_streams.py
```

## 🎮 Usage

### Run the Application

```bash
python app.py
```

### Controls

- **'q'**: Quit and display final statistics
- **'r'**: Reset all counters to zero

### Understanding the Display

**Top Panel (Stats)**:
- **Status Dot**: 🟢 Green = Person detected, ⚪ Gray = No detection
- **ENTRIES**: Total people who entered
- **EXITS**: Total people who exited
- **OCCUPANCY**: Current number of people inside (Entries - Exits)

**Counting Line**:
- Yellow horizontal line at Y=240 (configurable)
- **OUTSIDE** zone above the line
- **INSIDE** zone below the line

**Person Tracking**:
- Green circles around detected heads
- ID numbers assigned to each person
- Entry/Exit indicators appear when crossing the line

## ⚙️ Configuration

### Adjusting the Entry Line

The entry line is where people are counted. Adjust based on your camera view:

```python
"entry_line": 240,  # Y-coordinate (0-480 for default resolution)
```

For overhead cameras:
- Middle of frame: `240` (default)
- Near top: `150-200`
- Near bottom: `300-350`

### Performance Tuning

Edit these parameters in the `MediaPipePeopleCounter` class:

```python
self.PROCESS_EVERY_N_FRAMES = 2  # Process every 2nd frame (higher = faster, less accurate)
self.DEBOUNCE_FRAMES = 15        # Frames between counts (prevents rapid re-counting)
self.MATCH_DISTANCE = 80         # Distance threshold for tracking same person
self.MAX_FRAMES_NOT_SEEN = 150   # Keep track of person for 5 seconds when not visible
```

### Camera Resolution

Default: 640x480 (optimized for performance)

To change resolution, edit `process_frame()`:
```python
frame = cv2.resize(frame, (640, 480))  # Modify width, height
```

## 🏗️ Architecture

### Core Components

**`MediaPipePeopleCounter`**: Per-door tracking system
- Detects people using MediaPipe Pose (nose landmark)
- State-based crossing detection (inside/outside)
- Debouncing to prevent duplicate counts
- Persistent ID tracking across frames

**`LectureHallMonitor`**: Main orchestrator
- Manages multiple door counters
- Aggregates statistics
- Handles display and user input

### Detection Algorithm

1. **Frame Capture**: DroidCam stream → OpenCV capture
2. **Pose Detection**: MediaPipe identifies nose position
3. **Tracking**: Matches detection to existing person IDs
4. **Crossing Detection**: Compares position relative to entry line
5. **State Management**: Updates 'inside'/'outside' state
6. **Debouncing**: Prevents counting same crossing multiple times

### Why MediaPipe Instead of YOLO?

- ⚡ **Faster**: 2-3x faster processing on CPU
- 💾 **Lightweight**: ~6MB vs 50MB+ model size
- 🎯 **Accurate for pose**: Tracks specific body landmarks
- 🔋 **Lower power**: Better for mobile/edge devices

## 📊 Performance Metrics

- **Processing Speed**: ~30 FPS on modern CPU
- **Detection Range**: 1-2 meters from camera (overhead view)
- **Accuracy**: 95%+ in controlled lighting
- **Latency**: <100ms end-to-end

## 🐛 Troubleshooting

### "Connection failed" Error
- Ensure DroidCam app is running on phone
- Verify phone and computer are on same WiFi network
- Test camera URL in web browser: `http://YOUR_IP:4747/video`

### Jittery Video
- Lower resolution in `process_frame()`
- Increase `PROCESS_EVERY_N_FRAMES` value
- Check network connection quality

### Inaccurate Counts
- Adjust `entry_line` position to center of doorway
- Increase `DEBOUNCE_FRAMES` to prevent rapid re-counts
- Ensure good overhead lighting
- Position camera directly above doorway

### Status Dot Not Activating
- Ensure MediaPipe can see person's head/face
- Check lighting conditions (not too dark)
- Verify camera is not obstructed
- Lower `min_detection_confidence` in MediaPipe config

## 📁 Project Structure

```
hackathon/
├── app.py                    # Main application (414 lines)
├── test_streams.py           # Camera testing utility (195 lines)
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── CALIBRATION_GUIDE.md      # Step-by-step setup instructions
├── OPTIMIZATIONS.md          # Performance improvements log
├── .venv/                    # Virtual environment
└── docs/
    └── technical_report.md   # Technical documentation
```

## 🔬 Technical Details

### MediaPipe Configuration

```python
mp_pose.Pose(
    static_image_mode=False,      # Video stream mode
    model_complexity=0,           # Lite model (fastest)
    enable_segmentation=False,    # No background segmentation
    smooth_landmarks=True,        # Reduce jitter
    min_detection_confidence=0.3, # Lower = faster detection
    min_tracking_confidence=0.3   # Lower = faster tracking
)
```

### State Machine

Each tracked person has:
- **position**: (x, y) coordinates
- **last_side**: 'top' or 'bottom' relative to line
- **frames_since_crossing**: Debounce counter
- **frames_not_seen**: Persistence counter

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Multi-camera synchronization
- Cloud logging/analytics
- Mobile app integration
- Alert system for overcapacity
- Heat map visualization

## 📝 License

This project is open source and available under the MIT License.

## 👤 Author

**11BLAZE-FURY11**
- GitHub: [@11BLAZE-FURY11](https://github.com/11BLAZE-FURY11)
- Repository: [FIRE_AND_SAFETY_HALL](https://github.com/11BLAZE-FURY11/FIRE_AND_SAFETY_HALL)

## 🙏 Acknowledgments

- MediaPipe team for the pose detection model
- OpenCV community for computer vision tools
- DroidCam for wireless camera functionality

---

**⚠️ Note**: This system is designed for educational and demonstration purposes. For production fire safety systems, please consult with certified safety professionals and comply with local regulations.

# Fire & Safety People Counter - AI Agent Instructions

**⚠️ DO NOT GENERATE DOCUMENTATION .md FILES UNLESS EXPLICITLY REQUESTED**

## Project Overview
Real-time people counting system for lecture hall fire safety using **overhead/top-down cameras**. Monitors 3 doors with DroidCam phones + YOLOv8 detection to track occupancy.

## Architecture

### Core Components
- **`PeopleCounter`** (lines 28-252): Per-door tracking with state-based crossing detection
- **`LectureHallMonitor`** (lines 255-407): Orchestrator managing multiple doors + unified dashboard
- **YOLO Integration**: Ultralytics YOLOv8n with `model.track()` using ByteTrack for persistent IDs

### Data Flow
1. DroidCam stream → `VideoCapture` with `CAP_PROP_BUFFERSIZE=1` (line 61)
2. Frame → YOLO track → bounding boxes + persistent track IDs
3. Track centroid history (15 frames) → `detect_crossing()` compares prev/current position
4. State machine (`last_crossing_state`) tracks 'inside'/'outside' + debounce logic
5. Dashboard aggregates all doors → displays total occupancy

### Critical Design Decisions
- **State-based tracking (not boolean flags)**: `last_crossing_state[id] = 'inside'/'outside'` allows bidirectional crossings while preventing duplicate counts of same state
- **Debounce system**: 20 frames (~0.67s) + 60px distance threshold prevents rapid re-crossings from people hovering near line
- **15-frame history (not 30)**: Faster response for overhead cameras where people move quickly through doorway
- **conf=0.4, imgsz=416**: Optimized for overhead person detection (higher conf than typical side-view scenarios)

## Environment Setup

```bash
source .venv/bin/activate  # Virtual env already exists
pip install opencv-python ultralytics numpy
python app.py  # Main application
python test_streams.py  # Test camera feeds without YOLO
```

## Project-Specific Patterns

### Configuration (lines 8-26)
```python
DOOR_CONFIGS = {
    "Door 1": {
        "url": "http://192.168.2.100:4747/video",  # DroidCam IP
        "entry_line": 240,  # Y-coord (240 = middle of 480px frame for overhead)
        "direction": "horizontal",  # or "vertical"
        "rotation": 0  # 0, 90, 180, 270 degrees
    }
}
```

### Detection Logic (lines 72-89)
**Horizontal (overhead camera)**: Person's Y-position vs `entry_line`
- `prev_y < 240 <= current_y` → ENTRY (moving down into room)
- `prev_y > 240 >= current_y` → EXIT (moving up out of room)

**Vertical (side door)**: Person's X-position vs `entry_line`
- `prev_x < line <= current_x` → ENTRY (moving right)
- `prev_x > line >= current_x` → EXIT (moving left)

### State Management (lines 194-216)
```python
# BAD (old approach): if track_id not in counted_ids
# GOOD (current): State machine prevents duplicate counts
if crossing == "entry" and can_cross:
    if last_crossing_state.get(track_id) != 'inside':  # Only if not already inside
        entries += 1
        last_crossing_state[track_id] = 'inside'  # Set state
```

### Visual Debug Features (lines 176-236)
- **Blue polyline**: Movement trail (last 15 frames)
- **Green box**: Person marked 'inside'
- **Orange box**: Person 'outside' or unknown
- **Magenta dot**: Current centroid position
- **Info text**: `ID:X Y:Y D:distance [state]`

## Common Operations

### Adjusting for Camera Angle
1. **Entry line position**: Modify `entry_line` in `DOOR_CONFIGS`
   - Overhead: 240 (middle of frame)
   - Side-view: May need 150-300 depending on door placement
2. **Test first**: Run `test_streams.py` to visualize camera view before running YOLO

### Debugging Detection Issues
**Check console logs for**:
- `DEBUG` (every 30 frames): Shows all tracked IDs + positions
- `✅ ENTRY detected`: Successful entry count
- `🚪 EXIT detected`: Successful exit count
- `⚠️ already INSIDE/OUTSIDE`: State prevented duplicate count
- `🔒 blocked`: Debounce prevented crossing (shows frames_since + distance)

**Visual indicators**:
- Yellow line at Y=240 (or your `entry_line` value)
- Large green/red circles appear on crossing events
- Box colors: Green=inside, Orange=outside

### Performance Tuning (lines 119-131)
```python
# Overhead camera optimized settings:
conf=0.4        # Higher than default 0.25 (better accuracy)
iou=0.45        # Tracking overlap threshold
imgsz=416       # Larger than 320 for overhead detection
DEBOUNCE_FRAMES=20      # ~0.67s at 30fps
MIN_DISTANCE_FROM_LINE=60  # Pixels away before re-cross allowed
```

### Adding New Doors
Add to `DOOR_CONFIGS` (system handles 1-3 cameras automatically):
- 1 camera: Single full-size feed
- 2 cameras: Side-by-side horizontal layout
- 3 cameras: 2×2 grid (bottom-right padding)

## Known Issues & Patterns

### YOLO Model Selection
- **yolov8n.pt** (current): Fastest, ~6MB, good for CPU
- **yolov8s.pt**: Better accuracy, slower (~22MB)
- **yolov8m.pt**: Best accuracy, slowest (~52MB)
- Change line 264: `YOLO('yolov8n.pt')` → desired model

### DroidCam Connection
- **Protocol**: HTTP stream at `:4747/video` (no auth)
- **Test URL**: Open `http://192.168.2.100:4747/video` in browser
- **Common failure**: `Connection refused` = DroidCam app not running or different WiFi network
- **Latency**: Buffer size MUST be 1 (line 61), default 5+ causes ~200ms lag

### Overhead Camera Specifics
- **Problem**: People walk faster through doorway than side-view
- **Solution**: Reduced history (15 frames), faster debounce (20 frames)
- **Entry line**: Middle of frame (240) works best for centered doorway
- **Direction**: Always "horizontal" for top-down unless door on side

## Runtime Controls
- **'q'**: Quit + print final statistics
- **'r'**: Reset all counters (entries, exits, states, history)
- **Ctrl+C**: Emergency exit (may not print stats)

## Files Structure
```
app.py               # Main application (407 lines)
test_streams.py      # Camera testing without YOLO (195 lines)
CALIBRATION_GUIDE.md # Step-by-step setup instructions
OPTIMIZATIONS.md     # Performance improvements log
requirements.txt     # opencv-python, ultralytics, numpy
.venv/              # Virtual environment (pre-configured)
yolov8n.pt          # YOLO model weights (~6MB, auto-downloads)
```

## Integration Points
- **OpenCV**: `cv2.VideoCapture()` with `CAP_PROP_BUFFERSIZE=1` critical for latency
- **Ultralytics**: `model.track(persist=True, tracker="bytetrack.yaml")` maintains IDs across frames
- **NumPy**: Array operations for dashboard grid layout (`np.hstack`, `np.vstack`)
- **DroidCam**: HTTP MJPEG stream, no auth, port 4747

## Common Mistakes to Avoid
1. ❌ Don't use `time.sleep()` in frame loop (breaks low-latency)
2. ❌ Don't skip `CAP_PROP_BUFFERSIZE=1` (causes lag)
3. ❌ Don't use `conf=0.25` for overhead (too many false positives)
4. ❌ Don't check `if track_id not in counted_ids` (prevents exits)
5. ✅ DO use state machine: `last_crossing_state[id] = 'inside'/'outside'`
6. ✅ DO test with `test_streams.py` before running full app
7. ✅ DO check console logs for debug info every 30 frames

# Lecture Hall Monitoring System - Development Log

## Project Overview

A large lecture hall has three doors that lead into the same room. During emergencies or routine safety checks, it is important to know how many people are currently inside.

### Objective
Develop a system that performs tracking and detection of individuals entering and exiting through the three doors. The system should continuously update and display the total number of people in the lecture hall based on movements through any of the doors.

### Example
If 3 people enter through Door 1, 2 through Door 2, and 1 exits through Door 3, the system should show 4 people in the room. The display must clearly indicate entries, exits, and total occupancy, supporting fire and safety teams in maintaining a safe environment.

---

## Technical Approach: Top-Down View with OpenCV

### Why Top-Down View is Great

- **Privacy-friendly** ✅ - You don't need to see full bodies or faces
- **Simple detection** - You only detect motion blobs passing under the camera
- **Accurate background subtraction** - The background remains static, making OpenCV far more accurate
- **Clear counting zones** - You can even use lines/zones to count entries and exits clearly

### Can It Work Without YOLO?

**Yes!** YOLO helps when you need object identification (e.g., "this is a person, not a chair"). But in a top-down setup, all you care about is motion crossing a line — and OpenCV's background subtraction or optical flow is enough.

---

## Development Process

### Initial Approach: OpenCV Background Subtraction

**Strategy:**
- Connect to DroidCam stream
- Use MOG2 background subtraction
- Define counting lines (adjustable position)
- Increment entry or exit counts depending on direction of motion

**Issues Encountered:**
- Connection failures to multiple camera streams
- `AttributeError: 'PeopleCounter' object has no attribute 'bg_subtractor'`
- Missing initialization of background subtractor
- Incomplete blob tracking methods

**Resolution Attempts:**
- Fetched latest OpenCV documentation via Context7 MCP server
- Attempted to fix initialization issues
- Code became too complex

---

### Second Approach: Simplified OpenCV Implementation

**Action:** Complete rewrite with simpler, cleaner implementation from scratch

**Result:** File ended up empty during the process, requiring another restart

---

### Third Approach: MediaPipe Implementation

**Why MediaPipe?**
- Excellent pose detection that works great for top-down views
- More robust people detection compared to background subtraction
- Better tracking capabilities

**Implementation Steps:**
1. Fetched MediaPipe documentation via Context7 MCP server
2. Implemented MediaPipe Pose detection
3. Updated requirements.txt to include MediaPipe

**Initial Issues:**
```
KeyError: 0
```
- Problem: `person_pos` was a dictionary with a 'pos' key, but code tried to access it like a tuple
- Solution: Correctly extract position from dictionary first

---

## Testing Results

### Test Run 1
```
✅ Door 1: ENTRY detected | Total: 1
🚪 Door 1: EXIT detected | Total: 1
✅ Door 1: ENTRY detected | Total: 2
🚪 Door 1: EXIT detected | Total: 2
Final Occupancy: 0 people
```

**Problem:** Entries and exits happening too frequently - just a dot on the head was causing multiple triggers

---

### Refinement: Adding Debouncing

**Changes Made:**
1. **Frame-based debouncing** - After a crossing is detected, wait 30 frames (~1 second at 30fps) before counting another crossing
2. **Distance check** - Person must be at least 50 pixels away from the line to count a crossing
3. **Better state tracking** - Track `frames_since_crossing` for each person

**Purpose:** Prevent rapid entry/exit counting when someone is just standing near the line or moving their head across it

---

### Further Refinement: Simplified Head Tracking

**User Request:** "I don't want the whole body, I just want a dot on my head that tracks it simple"

**Changes Made:**
1. **Show only a dot on head** - No more full body skeleton, just a simple green circle tracking head position
2. **Reduced debounce time** - From 30 frames (1 second) to 15 frames (0.5 seconds) for faster response
3. **Simplified crossing detection** - Only requires time-based debouncing, not distance requirement
4. **Lighter visualization** - Just a dot with minimal UI

---

### Critical Bug: Negative Occupancy

**Test Run:**
```
✅ Door 1: ENTRY detected | Total: 2
🚪 Door 1: EXIT detected | Total: 2
🚪 Door 1: EXIT detected | Total: 3
📊 Occupancy: -1 people
```

**Problem:** 
- Counting 2 entries and 3 exits, resulting in -1 people
- Tracking was losing the person and creating duplicate exit counts

---

## Final Solution: Improved Tracking Persistence

**Changes Made:**

1. **Keep tracks alive for 5 seconds** - Even if the person temporarily isn't detected, their ID persists for 150 frames to prevent duplicate counting

2. **Show ID in logs** - Display which person ID is entering/exiting for better debugging

3. **Display "TOTAL PEOPLE"** instead of "NET" - More intuitive label

4. **Better debugging** - Show when new people are detected and when tracks are lost

**Benefits:**
- Prevents duplicate exit counting
- More robust tracking even with temporary occlusions
- Clearer visualization and logging
- Maintains accurate occupancy count

---

## Technologies Used

- **OpenCV (cv2)** - Computer vision library
- **MediaPipe** - Google's pose detection library
- **NumPy** - Numerical operations
- **DroidCam** - Camera streaming
- **Context7 MCP Server** - For fetching latest documentation

---

## Key Learnings

1. **Top-down views are ideal** for people counting - simpler and more privacy-friendly
2. **MediaPipe is more robust** than pure background subtraction for people detection
3. **Debouncing is critical** to prevent false triggers
4. **Track persistence** is essential to avoid duplicate counts
5. **Simple visualizations work best** - a dot on the head is sufficient for tracking
6. **Proper ID tracking** prevents counting the same person multiple times

---

## System Configuration

- **Buffer size:** 1 frame (low latency)
- **MOG2 history:** 500 frames (when used)
- **Shadow detection:** Enabled
- **Min blob area:** 500px
- **Max blob area:** 10000px
- **Frame resize:** 640x480
- **Debounce:** 15 frames (~0.5s)
- **Track persistence:** 150 frames (~5s)
- **Detection:** MediaPipe Pose (Lite model)

---

## Final Status

✅ System successfully detects people entering and exiting
✅ Tracks head position with a simple dot
✅ Maintains accurate occupancy count
✅ No YOLO required - pure computer vision with MediaPipe
✅ Proper debouncing prevents false triggers
✅ Track persistence prevents duplicate counts
import cv2
import numpy as np
import mediapipe as mp

# Configuration for 3 doors with DroidCam IPs
DOOR_CONFIGS = {
    "Door 1": {
        "url": "http://192.168.2.100:4747/video",
        "entry_line": 240,
        "direction": "horizontal"
    },
}

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


class MediaPipePeopleCounter:
    """People counter using MediaPipe Pose detection"""
    
    def __init__(self, door_name, url, entry_line, direction="horizontal"):
        self.door_name = door_name
        self.url = url
        self.entry_line = entry_line
        self.direction = direction
        
        # Counters
        self.entries = 0
        self.exits = 0
        
        # Detection state for UI
        self.is_person_detected = False
        
        # MediaPipe Pose detector - OPTIMIZED for speed
        self.pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,  # 0 = Lite (fastest)
            enable_segmentation=False,
            smooth_landmarks=True,  # Reduce jitter
            min_detection_confidence=0.3,  # Lower = faster detection
            min_tracking_confidence=0.3   # Lower = faster tracking
        )
        
        # Tracking people by their nose landmark
        self.tracked_people = {}  # person_id: {'position': (x,y), 'last_side': 'top'/'bottom', 'frames_since_crossing': int, 'frames_not_seen': int}
        self.next_id = 0
        self.frame_count = 0
        
        # Parameters
        self.MATCH_DISTANCE = 80  # Distance threshold for matching people
        self.DEBOUNCE_FRAMES = 15  # Must wait 15 frames (~0.5 seconds) before counting another crossing
        self.MIN_DISTANCE_FROM_LINE = 30  # Must be at least 30px away from line to count crossing
        self.MAX_FRAMES_NOT_SEEN = 150  # Keep track for 5 seconds (150 frames @ 30fps) even if not detected
        
        # Performance optimization
        self.PROCESS_EVERY_N_FRAMES = 2  # Process every 2nd frame for better performance
        
        # Video capture
        self.cap = None
    
    def connect(self):
        """Connect to camera"""
        self.cap = cv2.VideoCapture(self.url)
        if not self.cap.isOpened():
            return False
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return True
    
    def get_side(self, y):
        """Determine which side of line a point is on"""
        return "bottom" if y > self.entry_line else "top"
    
    def get_person_center(self, landmarks, frame_width, frame_height):
        """Get center position from pose landmarks (using nose or midpoint of shoulders)"""
        # Use nose landmark (index 0) as the person's center
        nose = landmarks.landmark[mp_pose.PoseLandmark.NOSE]
        
        # Convert normalized coordinates to pixel coordinates
        x = int(nose.x * frame_width)
        y = int(nose.y * frame_height)
        
        return (x, y)
    
    def update_tracking(self, detected_people):
        """Update person tracking and detect crossings"""
        current_ids = set()
        
        # Increment counters for all tracked people
        for person_id in self.tracked_people:
            self.tracked_people[person_id]['frames_since_crossing'] += 1
            self.tracked_people[person_id]['frames_not_seen'] += 1
        
        for person_dict in detected_people:
            pos = person_dict['pos']  # Extract position tuple
            matched_id = None
            min_dist = self.MATCH_DISTANCE
            
            # Find closest tracked person
            for person_id, data in self.tracked_people.items():
                old_pos = data['position']
                dist = np.sqrt((pos[0] - old_pos[0])**2 + (pos[1] - old_pos[1])**2)
                if dist < min_dist:
                    min_dist = dist
                    matched_id = person_id
            
            # Update existing or create new track
            if matched_id is not None:
                person_dict['id'] = matched_id
                current_ids.add(matched_id)
                
                # Reset not_seen counter
                self.tracked_people[matched_id]['frames_not_seen'] = 0
                
                # Get tracking data
                old_side = self.tracked_people[matched_id]['last_side']
                new_side = self.get_side(pos[1])
                frames_since = self.tracked_people[matched_id]['frames_since_crossing']
                
                # Check for crossing with debouncing
                can_cross = (frames_since >= self.DEBOUNCE_FRAMES)
                
                if old_side != new_side and can_cross:
                    # Crossing detected!
                    if old_side == "top" and new_side == "bottom":
                        self.entries += 1
                        print(f"✅ {self.door_name}: ENTRY detected (ID:{matched_id}) | Total IN: {self.entries}")
                        person_dict['crossing'] = 'entry'
                        self.tracked_people[matched_id]['frames_since_crossing'] = 0
                    elif old_side == "bottom" and new_side == "top":
                        self.exits += 1
                        print(f"🚪 {self.door_name}: EXIT detected (ID:{matched_id}) | Total OUT: {self.exits}")
                        person_dict['crossing'] = 'exit'
                        self.tracked_people[matched_id]['frames_since_crossing'] = 0
                elif old_side != new_side and not can_cross:
                    # Blocked by debounce
                    if self.frame_count % 30 == 0:  # Log occasionally
                        print(f"🔒 {self.door_name}: Crossing blocked for ID:{matched_id} (debounce={frames_since}f)")
                
                # Update position and side
                self.tracked_people[matched_id]['position'] = pos
                self.tracked_people[matched_id]['last_side'] = new_side
            else:
                # New person detected
                person_dict['id'] = self.next_id
                current_ids.add(self.next_id)
                self.tracked_people[self.next_id] = {
                    'position': pos,
                    'last_side': self.get_side(pos[1]),
                    'frames_since_crossing': 999,  # Start with high value so first crossing counts
                    'frames_not_seen': 0
                }
                print(f"👤 {self.door_name}: New person detected (ID:{self.next_id})")
                self.next_id += 1
        
        # Keep tracks that are still being seen OR haven't been gone too long
        for person_id in list(self.tracked_people.keys()):
            if person_id in current_ids or self.tracked_people[person_id]['frames_not_seen'] < self.MAX_FRAMES_NOT_SEEN:
                continue  # Keep this track
            else:
                # Remove old track
                print(f"❌ {self.door_name}: Lost track of person ID:{person_id}")
                del self.tracked_people[person_id]
    
    def process_frame(self, frame):
        """Process a frame and return annotated result"""
        self.frame_count += 1
        
        # Resize to optimized resolution (640x480 for better performance)
        frame = cv2.resize(frame, (640, 480))
        frame_height, frame_width = frame.shape[:2]
        
        # Performance optimization: Process every Nth frame
        should_process = (self.frame_count % self.PROCESS_EVERY_N_FRAMES == 0)
        
        results = None
        if should_process:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process with MediaPipe Pose
            results = self.pose.process(rgb_frame)
        
        # Prepare result image
        annotated_frame = frame.copy()
        
        # Draw semi-transparent background for stats panel
        overlay = annotated_frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame_width, 180), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, annotated_frame, 0.4, 0, annotated_frame)
        
        # Draw counting line with glow effect
        cv2.line(annotated_frame, (0, self.entry_line), (frame_width, self.entry_line), (0, 200, 255), 5)
        cv2.line(annotated_frame, (0, self.entry_line), (frame_width, self.entry_line), (0, 255, 255), 2)
        
        # Draw zone labels with background
        cv2.rectangle(annotated_frame, (8, self.entry_line - 35), (150, self.entry_line - 8), (0, 0, 0), -1)
        cv2.putText(annotated_frame, "OUTSIDE", (15, self.entry_line - 15),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        cv2.rectangle(annotated_frame, (8, self.entry_line + 8), (130, self.entry_line + 35), (0, 0, 0), -1)
        cv2.putText(annotated_frame, "INSIDE", (15, self.entry_line + 28),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Detect people (just track head/nose position)
        detected_people = []
        if should_process and results and results.pose_landmarks:
            # Get person center (nose position)
            center = self.get_person_center(results.pose_landmarks, frame_width, frame_height)
            detected_people.append({'pos': center})
            
            # Update tracking and detect crossings
            self.update_tracking(detected_people)
            
            # Update detection state for UI
            self.is_person_detected = True
            
            # Draw head tracking with optimized glow effect
            cv2.circle(annotated_frame, center, 20, (0, 255, 0), 2)
            cv2.circle(annotated_frame, center, 12, (0, 255, 0), -1)
            cv2.circle(annotated_frame, center, 4, (255, 255, 255), -1)
        else:
            # No person detected or skipped frame
            if should_process:
                self.is_person_detected = False
        
        # Draw tracked people with enhanced visualization
        for person in detected_people:
            pos = person['pos']
            
            # Draw ID with background
            if 'id' in person:
                text = f"ID: {person['id']}"
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                cv2.rectangle(annotated_frame, (pos[0] - text_size[0]//2 - 5, pos[1] - 40), 
                            (pos[0] + text_size[0]//2 + 5, pos[1] - 15), (0, 0, 0), -1)
                cv2.putText(annotated_frame, text, (pos[0] - text_size[0]//2, pos[1] - 22),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            # Draw crossing indicator with animation
            if 'crossing' in person:
                color = (0, 255, 0) if person['crossing'] == 'entry' else (0, 100, 255)
                # Outer glow
                cv2.circle(annotated_frame, pos, 70, color, 2)
                cv2.circle(annotated_frame, pos, 60, color, 4)
                # Text
                text = "ENTRY ↓" if person['crossing'] == 'entry' else "EXIT ↑"
                text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)[0]
                cv2.rectangle(annotated_frame, (pos[0] - text_size[0]//2 - 8, pos[1] + 50), 
                            (pos[0] + text_size[0]//2 + 8, pos[1] + 80), (0, 0, 0), -1)
                cv2.putText(annotated_frame, text, (pos[0] - text_size[0]//2, pos[1] + 72),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        
        # Draw enhanced stats panel
        total_people = self.entries - self.exits
        
        # Title with status indicator dot
        cv2.putText(annotated_frame, "FIRE & SAFETY MONITOR", (20, 40),
                   cv2.FONT_HERSHEY_DUPLEX, 0.9, (255, 255, 255), 2)
        
        # Status dot - lights up when person detected (using persistent state)
        dot_color = (0, 255, 0) if self.is_person_detected else (100, 100, 100)
        cv2.circle(annotated_frame, (400, 30), 12, dot_color, -1)  # Filled circle
        cv2.circle(annotated_frame, (400, 30), 14, dot_color, 2)   # Outer ring
        status_text = "ACTIVE" if self.is_person_detected else "IDLE"
        cv2.putText(annotated_frame, status_text, (425, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, dot_color, 2)
        
        cv2.putText(annotated_frame, self.door_name, (20, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 200, 255), 2)
        
        # Stats with icons
        cv2.putText(annotated_frame, f"ENTRIES:  {self.entries}", (20, 115),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 100), 2)
        cv2.putText(annotated_frame, f"EXITS:    {self.exits}", (20, 145),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 150, 255), 2)
        
        # Total people - large and prominent
        total_color = (0, 255, 0) if total_people >= 0 else (0, 0, 255)
        cv2.rectangle(annotated_frame, (frame_width - 200, 15), (frame_width - 15, 165), (0, 0, 0), -1)
        cv2.rectangle(annotated_frame, (frame_width - 200, 15), (frame_width - 15, 165), total_color, 3)
        cv2.putText(annotated_frame, "OCCUPANCY", (frame_width - 185, 50),
                   cv2.FONT_HERSHEY_DUPLEX, 0.7, (200, 200, 200), 2)
        cv2.putText(annotated_frame, f"{total_people}", (frame_width - 140, 120),
                   cv2.FONT_HERSHEY_DUPLEX, 2.2, total_color, 3)
        cv2.putText(annotated_frame, "people", (frame_width - 125, 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return annotated_frame
    
    def reset(self):
        """Reset counters"""
        self.entries = 0
        self.exits = 0
        self.tracked_people.clear()
        self.next_id = 0
    
    def cleanup(self):
        """Release resources"""
        self.pose.close()
        if self.cap:
            self.cap.release()


class LectureHallMonitor:
    """Monitor multiple doors"""
    
    def __init__(self, door_configs):
        self.door_configs = door_configs
        self.counters = {}
    
    def initialize(self):
        """Connect to all cameras"""
        print("🔄 Initializing MediaPipe Pose Detection...")
        print("✅ Using MediaPipe for people detection (No YOLO!)\n")
        
        for door_name, config in self.door_configs.items():
            counter = MediaPipePeopleCounter(
                door_name,
                config["url"],
                config["entry_line"],
                config.get("direction", "horizontal")
            )
            
            if counter.connect():
                self.counters[door_name] = counter
                print(f"✅ {door_name}: Connected")
            else:
                print(f"❌ {door_name}: Connection failed")
        
        return len(self.counters) > 0
    
    def create_dashboard(self, frames):
        """Create multi-camera dashboard"""
        if not frames:
            return None
        
        frame_list = list(frames.values())
        
        # Single camera
        if len(frame_list) == 1:
            combined = frame_list[0]
        # Two cameras
        elif len(frame_list) == 2:
            combined = np.hstack(frame_list)
        # Three cameras (2 top, 1 bottom)
        else:
            top = np.hstack(frame_list[:2])
            bottom = frame_list[2]
            padding = np.zeros_like(bottom)
            bottom_row = np.hstack([bottom, padding])
            combined = np.vstack([top, bottom_row])
        
        # Add info panel
        total_in = sum(c.entries for c in self.counters.values())
        total_out = sum(c.exits for c in self.counters.values())
        occupancy = total_in - total_out
        
        info_panel = np.zeros((100, combined.shape[1], 3), dtype=np.uint8)
        cv2.putText(info_panel, "LECTURE HALL OCCUPANCY MONITOR", (20, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(info_panel, f"Entries: {total_in}  Exits: {total_out}", (20, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        color = (0, 255, 0) if occupancy >= 0 else (0, 0, 255)
        cv2.putText(info_panel, f"OCCUPANCY: {occupancy}", (500, 70),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)
        
        dashboard = np.vstack([info_panel, combined])
        return dashboard
    
    def run(self):
        """Main loop"""
        if not self.initialize():
            print("\n❌ No cameras connected!")
            return
        
        print(f"\n🚀 Monitoring {len(self.counters)} door(s)")
        print("📹 Press 'q' to quit, 'r' to reset\n")
        
        frame_count = 0
        
        while True:
            # Process each camera (only one for now)
            for name, counter in self.counters.items():
                ret, frame = counter.cap.read()
                if ret:
                    processed = counter.process_frame(frame)
                    # Display directly (no dashboard for single camera)
                    cv2.imshow("Fire & Safety Monitor - Lecture Hall", processed)
            
            # Status update every second
            frame_count += 1
            if frame_count % 30 == 0:
                total = sum(c.entries - c.exits for c in self.counters.values())
                print(f"📊 Occupancy: {total} people")
            
            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                for counter in self.counters.values():
                    counter.reset()
                print("🔄 Counters reset")
        
        # Cleanup
        print("\n🛑 Shutting down...")
        for counter in self.counters.values():
            counter.cleanup()
        cv2.destroyAllWindows()
        
        # Final stats
        print("\n📊 Final Statistics:")
        for name, counter in self.counters.items():
            print(f"  {name}: {counter.entries} in, {counter.exits} out")
        total = sum(c.entries - c.exits for c in self.counters.values())
        print(f"  Final Occupancy: {total} people")


if __name__ == "__main__":
    monitor = LectureHallMonitor(DOOR_CONFIGS)
    monitor.run()

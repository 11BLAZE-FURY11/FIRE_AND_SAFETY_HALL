import cv2
import numpy as np
import time

# Configuration for 3 doors with DroidCam IPs
DOOR_CONFIGS = {
    "Door 1": {
        "url": "http://192.168.2.100:4747/video",
        "position": "top-left",
        "rotation": 0  # 0, 90, 180, 270 degrees clockwise
    },
    "Door 2": {
        "url": "http://192.168.2.149:4747/video",
        "position": "top-right",
        "rotation": 0  # 0, 90, 180, 270 degrees clockwise
    },
    "Door 3": {
        "url": "http://192.168.2.117:4747/video",
        "position": "bottom",
        "rotation": 0  # 0, 90, 180, 270 degrees clockwise
    }
}

class VideoStreamDisplay:
    def __init__(self, door_configs):
        self.door_configs = door_configs
        self.captures = {}
        self.frames = {}
        
    def initialize_cameras(self):
        """Initialize all camera connections with low-latency settings"""
        print("🔄 Connecting to cameras with low-latency optimization...\n")
        
        for door_name, config in self.door_configs.items():
            print(f"Connecting to {door_name}...")
            cap = cv2.VideoCapture(config["url"])
            
            if cap.isOpened():
                # CRITICAL: Reduce buffer size to minimize latency
                # Default buffer is 5+ frames which causes lag
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # Optional: Set lower resolution for faster processing
                # cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                
                # Optional: Increase FPS if supported by camera
                # cap.set(cv2.CAP_PROP_FPS, 30)
                
                print(f"✅ {door_name}: Connected (buffer size set to 1)")
                self.captures[door_name] = cap
            else:
                print(f"❌ {door_name}: Failed to connect")
        
        if len(self.captures) == 0:
            print("\n❌ No cameras connected. Please check:")
            print("   1. DroidCam is running on your phones")
            print("   2. All devices are on the same WiFi network")
            print("   3. The IP addresses are correct")
            return False
        
        print(f"\n\u2705 Successfully connected to {len(self.captures)} camera(s)")
        return True
    
    def rotate_frame(self, frame, rotation):
        """Rotate frame based on configuration"""
        if rotation == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif rotation == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        elif rotation == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame
    
    def create_display(self):
        """Create a grid display of all camera feeds with minimal processing"""
        active_frames = []
        door_names = []
        
        # Collect all available frames - use grab() for speed
        for door_name, cap in self.captures.items():
            # grab() is faster than read() - it grabs frame without decoding
            if cap.grab():
                # retrieve() decodes the grabbed frame
                ret, frame = cap.retrieve()
                if ret:
                    # Rotate frame if needed
                    rotation = self.door_configs[door_name].get("rotation", 0)
                    frame = self.rotate_frame(frame, rotation)
                    
                    # Resize to standard size (fast resize with INTER_NEAREST)
                    frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_NEAREST)
                    
                    # Add door name label
                    cv2.putText(frame, door_name, (10, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)
                    
                    active_frames.append(frame)
                    door_names.append(door_name)
            else:
                print(f"⚠️  {door_name}: Failed to grab frame")
        
        if len(active_frames) == 0:
            return None
        
        # Create grid layout based on number of cameras
        if len(active_frames) == 1:
            combined = active_frames[0]
        elif len(active_frames) == 2:
            # Side by side
            combined = np.hstack(active_frames)
        else:  # 3 cameras
            # Two on top, one on bottom
            top_row = np.hstack(active_frames[:2])
            bottom_frame = active_frames[2]
            # Add black padding to match width
            padding = np.zeros((480, 640, 3), dtype=np.uint8)
            bottom_row = np.hstack([bottom_frame, padding])
            combined = np.vstack([top_row, bottom_row])
        
        # Add info panel at top
        info_height = 80
        info_panel = np.zeros((info_height, combined.shape[1], 3), dtype=np.uint8)
        
        # Add title
        cv2.putText(info_panel, "DroidCam Stream Test", (20, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        
        # Add camera count
        cv2.putText(info_panel, f"{len(active_frames)} Camera(s) Active", 
                   (combined.shape[1] - 400, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        
        # Combine info panel with camera feeds
        display = np.vstack([info_panel, combined])
        
        return display
    
    def run(self):
        """Main display loop"""
        if not self.initialize_cameras():
            return
        
        print("\n🚀 Starting video stream display")
        print("📊 Latency optimizations applied:")
        print("   • Buffer size: 1 frame (minimal lag)")
        print("   • Fast resize: INTER_NEAREST interpolation")
        print("   • Optimized grab/retrieve pattern")
        print("\nPress 'q' to quit\n")
        
        # Frame timing for FPS calculation
        frame_count = 0
        start_time = time.time()
        
        while True:
            display = self.create_display()
            
            if display is not None:
                cv2.imshow("DroidCam Multi-Stream Display", display)
                frame_count += 1
            
            # Check for quit key
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("\n🛑 Shutting down...")
                break
            
            # Calculate and display FPS every 30 frames
            if frame_count % 30 == 0:
                elapsed = time.time() - start_time
                fps = frame_count / elapsed
                print(f"📈 Current FPS: {fps:.1f}")
        
        # Cleanup
        for cap in self.captures.values():
            cap.release()
        cv2.destroyAllWindows()
        
        # Final stats
        total_time = time.time() - start_time
        avg_fps = frame_count / total_time
        print(f"\n✅ Stream test completed")
        print(f"📊 Average FPS: {avg_fps:.1f}")
        print(f"📊 Total frames: {frame_count}")


if __name__ == "__main__":
    print("=" * 60)
    print("DroidCam Multi-Stream Test")
    print("=" * 60)
    print()
    
    display = VideoStreamDisplay(DOOR_CONFIGS)
    display.run()

"""
Snapshot Capture Module
Captures and saves images when emergency is detected
"""

import cv2
import time
from datetime import datetime
from pathlib import Path
from src.config import config

class SnapshotCapture:
    """Handles snapshot capture and saving"""
    
    def __init__(self):
        self.last_capture_time = 0
        self.capture_cooldown = 5  # seconds between captures
    
    def capture(self, frame, gesture_detected=False, add_overlay=True):
        """
        Capture current frame as snapshot.
        
        Args:
            frame: Current video frame
            gesture_detected: Whether gesture was detected
            add_overlay: Whether to add text overlay
        
        Returns:
            tuple: (filepath, frame_with_overlay)
        """
        # Check cooldown
        current_time = time.time()
        if current_time - self.last_capture_time < self.capture_cooldown:
            return None, None
        
        # Create copy for overlay
        capture_frame = frame.copy()
        
        # Add timestamp and info overlay
        if add_overlay:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Background for text
            overlay = capture_frame.copy()
            cv2.rectangle(overlay, (0, 0), (capture_frame.shape[1], 60), (0, 0, 0), -1)
            capture_frame = cv2.addWeighted(overlay, 0.6, capture_frame, 0.4, 0)
            
            # Add text
            cv2.putText(capture_frame, f"EMERGENCY ALERT", (10, 25),
                       config.FONT, 0.7, (0, 0, 255), 2)
            cv2.putText(capture_frame, f"Time: {timestamp}", (10, 50),
                       config.FONT, 0.5, (255, 255, 255), 1)
            
            if gesture_detected:
                cv2.putText(capture_frame, "DISTRESS GESTURE CONFIRMED", (10, 75),
                           config.FONT, 0.5, (0, 0, 255), 1)
        
        # Generate filename
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        filename = f"emergency_{timestamp_str}.jpg"
        filepath = config.SNAPSHOT_DIR / filename
        
        # Save image
        cv2.imwrite(str(filepath), capture_frame)
        
        self.last_capture_time = current_time
        
        return str(filepath), capture_frame
    
    def capture_multiple(self, frame, count=3, delay=0.1):
        """Capture multiple snapshots in sequence"""
        snapshots = []
        for i in range(count):
            filepath, _ = self.capture(frame, add_overlay=True)
            if filepath:
                snapshots.append(filepath)
            if i < count - 1:
                time.sleep(delay)
        return snapshots
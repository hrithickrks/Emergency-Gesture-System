"""
Main Application Module
Orchestrates all modules for emergency gesture detection
"""

import cv2
import time
import logging
import sys
import signal
from pathlib import Path
from typing import Optional
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.finger_detector import FingerStateDetector
from src.gesture_recognizer import GesturePatternRecognizer
from src.temporal_validator import TemporalValidator
from src.snapshot_capture import SnapshotCapture
from src.email_alert import EmailAlertSender
from src.ui_overlay import UIOverlay
from src.utils import setup_logging, calculate_fps, PerformanceMonitor

# Import MediaPipe
import mediapipe as mp

logger = setup_logging()

class EmergencyGestureDetector:
    """Main application orchestrator with idle detection"""
    
    def __init__(self):
        logger.info("Initializing Emergency Gesture Detection System")
        
        # Initialize MediaPipe with optimized settings
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=config.CONFIDENCE_THRESHOLD,
            min_tracking_confidence=0.5,
            model_complexity=1
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # Initialize modules
        self.finger_detector = FingerStateDetector()
        self.gesture_recognizer = GesturePatternRecognizer()
        self.temporal_validator = TemporalValidator()
        self.snapshot_capture = SnapshotCapture()
        self.email_sender = EmailAlertSender()
        self.ui_overlay = UIOverlay()
        self.performance_monitor = PerformanceMonitor(max_samples=config.PERFORMANCE_SAMPLES)
        
        # State variables
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = True
        self.alert_sent = False
        self.paused = False
        
        # Idle detection variables
        self.last_hand_detected_time = time.time()
        self.idle_warning_shown = False
        self.auto_exit_enabled = True  # Set to False to disable auto-exit
        
        # Performance tracking
        self.fps = 0
        self.fps_start_time = time.time()
        self.fps_frame_count = 0
        self.frame_skip = 0
        self.frame_skip_counter = 0
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("System initialization complete")
        logger.info(f"Idle timeout set to {config.IDLE_TIMEOUT} seconds")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def initialize_camera(self) -> bool:
        """Initialize webcam with error handling"""
        try:
            self.cap = cv2.VideoCapture(config.CAMERA_INDEX)
            
            if not self.cap.isOpened():
                logger.error(f"Could not open camera with index {config.CAMERA_INDEX}")
                for idx in [1, 2]:
                    logger.info(f"Trying camera index {idx}...")
                    self.cap = cv2.VideoCapture(idx)
                    if self.cap.isOpened():
                        logger.info(f"Successfully opened camera with index {idx}")
                        break
            
            if not self.cap.isOpened():
                logger.error("No camera available")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            self.cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
            
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Camera initialized: {actual_width:.0f}x{actual_height:.0f} @ {actual_fps:.0f}fps")
            return True
            
        except Exception as e:
            logger.error(f"Camera initialization failed: {e}")
            return False
    
    def check_idle_and_exit(self, hand_detected: bool, current_time: float) -> bool:
        """
        Check if system has been idle and should exit.
        
        Args:
            hand_detected: Whether a hand is currently detected
            current_time: Current timestamp
        
        Returns:
            bool: True if should exit, False otherwise
        """
        if not self.auto_exit_enabled:
            return False
        
        if hand_detected:
            # Reset idle timer when hand is detected
            self.last_hand_detected_time = current_time
            self.idle_warning_shown = False
            return False
        
        # Calculate idle duration
        idle_duration = current_time - self.last_hand_detected_time
        
        # Check if timeout reached
        if idle_duration >= config.IDLE_TIMEOUT:
            logger.info(f"No hand detected for {idle_duration:.1f} seconds. Auto-exiting...")
            return True
        
        # Show warning before exit
        if idle_duration >= config.IDLE_WARNING_TIME and not self.idle_warning_shown:
            self.idle_warning_shown = True
            remaining = config.IDLE_TIMEOUT - idle_duration
            logger.warning(f"No hand detected. System will exit in {remaining:.1f} seconds. Show your hand to continue.")
        
        return False
    
    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Process single frame for gesture detection with frame skipping optimization"""
        start_time = time.time()
        current_time = time.time()
        
        # Frame skipping for performance
        if self.frame_skip > 0:
            self.frame_skip_counter += 1
            if self.frame_skip_counter < self.frame_skip:
                return self._draw_minimal_overlay(frame, None)
            self.frame_skip_counter = 0
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.hands.process(rgb_frame)
        rgb_frame.flags.writeable = True
        
        detection_time = time.time() - start_time
        self.performance_monitor.add_detection_time(detection_time)
        
        # Default values
        finger_states = [False, False, False, False, False]
        gesture_detected = False
        cycle_count = 0
        confidence = 0.0
        gesture_active = False
        hand_detected = False
        
        # Process hand landmarks if detected
        if results.multi_hand_landmarks:
            hand_detected = True
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw landmarks
                frame = self.ui_overlay.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                )
                
                # Detect finger states
                landmarks = hand_landmarks.landmark
                if self.finger_detector.is_valid_hand(landmarks):
                    finger_states = self.finger_detector.get_all_finger_states(landmarks)
                    
                    # Recognize gesture pattern
                    gesture_detected, cycle_count, confidence = self.gesture_recognizer.update(
                        finger_states, current_time
                    )
                    
                    gesture_active = self.gesture_recognizer.is_active
                    
                    # Temporal validation
                    if gesture_detected and not self.alert_sent and not self.paused:
                        alert_confirmed = self.temporal_validator.add_detection(
                            True, current_time, confidence
                        )
                        
                        if alert_confirmed:
                            logger.info("EMERGENCY GESTURE CONFIRMED! Triggering alert...")
                            self.trigger_emergency(frame)
        
        # Check for idle and auto-exit
        if self.check_idle_and_exit(hand_detected, current_time):
            self.running = False
            return frame
        
        # Check for cancel gesture (open palm)
        cancel_active = False
        if not self.paused and finger_states and all(finger_states[1:]):
            if self.temporal_validator.request_cancel(current_time, "open_hand"):
                logger.info("Alert cancelled by open hand gesture")
                self.alert_sent = False
            cancel_active = True
        
        # Update FPS
        self.fps_frame_count += 1
        if time.time() - self.fps_start_time >= 1.0:
            self.fps = self.fps_frame_count
            self.fps_frame_count = 0
            self.fps_start_time = time.time()
            
            # Dynamic frame skipping based on FPS
            if self.fps > 45:
                self.frame_skip = 2
            elif self.fps > 30:
                self.frame_skip = 1
            else:
                self.frame_skip = 0
        
        # Calculate idle time for display
        idle_time = current_time - self.last_hand_detected_time if not hand_detected else 0
        
        # Draw UI overlay
        frame = self.ui_overlay.draw(
            frame, finger_states, cycle_count, confidence,
            self.temporal_validator.alert_triggered, cancel_active,
            self.fps, gesture_active, self.paused, hand_detected, idle_time,
            config.IDLE_TIMEOUT - idle_time if not hand_detected and idle_time < config.IDLE_TIMEOUT else 0
        )
        
        frame_time = time.time() - start_time
        self.performance_monitor.add_frame_time(frame_time)
        
        return frame
    
    def _draw_minimal_overlay(self, frame: np.ndarray, fps: Optional[float]) -> np.ndarray:
        """Draw minimal overlay for skipped frames"""
        h, w = frame.shape[:2]
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (w-80, h-10), 
                   config.FONT, 0.4, (255, 255, 255), 1)
        return frame
    
    def trigger_emergency(self, frame: np.ndarray):
        """Trigger emergency alert with snapshot capture"""
        try:
            snapshot_path, snapshot_frame = self.snapshot_capture.capture(frame, gesture_detected=True)
            
            if snapshot_path:
                logger.info(f"Snapshot captured: {snapshot_path}")
                self.email_sender.send_async(snapshot_path, frame, self._on_email_sent)
                self.alert_sent = True
                logger.info("Emergency alert triggered")
            else:
                logger.error("Failed to capture snapshot")
                
        except Exception as e:
            logger.error(f"Error triggering emergency: {e}")
    
    def _on_email_sent(self, success: bool):
        """Callback for email sending result"""
        if success:
            logger.info("Emergency email sent successfully")
        else:
            logger.warning("Failed to send emergency email")
    
    def run(self):
        """Main application loop with error recovery"""
        if not self.initialize_camera():
            logger.error("Failed to initialize camera. Exiting.")
            return
        
        logger.info("Starting main detection loop")
        logger.info("Make distress gesture: Open/close all four fingers with thumb folded")
        logger.info(f"Auto-exit enabled: Will close after {config.IDLE_TIMEOUT}s of no hand detection")
        
        frame_errors = 0
        max_frame_errors = 10
        
        while self.running:
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    frame_errors += 1
                    logger.warning(f"Failed to read frame ({frame_errors}/{max_frame_errors})")
                    
                    if frame_errors >= max_frame_errors:
                        logger.error("Too many frame errors, attempting to reconnect...")
                        self.cap.release()
                        time.sleep(1)
                        if not self.initialize_camera():
                            break
                        frame_errors = 0
                    continue
                
                frame_errors = 0
                
                # Mirror frame for natural interaction
                frame = cv2.flip(frame, 1)
                
                # Process frame
                if not self.paused:
                    processed_frame = self.process_frame(frame)
                else:
                    processed_frame = self._draw_paused_overlay(frame)
                
                # Display
                cv2.imshow(config.WINDOW_NAME, processed_frame)
                
                # Handle keyboard input
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    logger.info("Quit requested by user")
                    self.running = False
                
                elif key == ord('c'):
                    self.temporal_validator.request_cancel(time.time(), "keyboard")
                    self.alert_sent = False
                    logger.info("Alert cancelled by user (keypress)")
                
                elif key == ord('p'):
                    self.paused = not self.paused
                    logger.info(f"System {'paused' if self.paused else 'resumed'}")
                
                elif key == ord('s'):
                    path, _ = self.snapshot_capture.capture(frame)
                    if path:
                        logger.info(f"Manual snapshot saved: {path}")
                
                elif key == ord('d'):
                    self._print_debug_info()
                
                elif key == ord('r'):
                    self.temporal_validator.reset()
                    self.alert_sent = False
                    self.last_hand_detected_time = time.time()
                    logger.info("System reset")
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(0.1)
        
        self.cleanup()
    
    def _draw_paused_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw paused state overlay"""
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (w//2 - 100, h//2 - 30), (w//2 + 100, h//2 + 30), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        cv2.putText(frame, "PAUSED", (w//2 - 50, h//2 + 5), config.FONT, 1, (0, 0, 255), 2)
        cv2.putText(frame, "Press 'p' to resume", (w//2 - 100, h//2 + 40), config.FONT, 0.5, (255, 255, 255), 1)
        return frame
    
    def _print_debug_info(self):
        """Print debug information"""
        print("\n" + "=" * 50)
        print("DEBUG INFORMATION")
        print("=" * 50)
        
        stats = self.performance_monitor.get_stats()
        print(f"Performance Stats: {stats}")
        
        validator_status = self.temporal_validator.get_status()
        print(f"Validator Status: {validator_status}")
        
        print(f"Alert Sent: {self.alert_sent}")
        print(f"Paused: {self.paused}")
        print(f"FPS: {self.fps:.1f}")
        print(f"Idle Timeout: {config.IDLE_TIMEOUT}s")
        
        print("=" * 50 + "\n")
    
    def cleanup(self):
        """Clean up resources safely"""
        logger.info("Cleaning up resources")
        
        if self.cap:
            self.cap.release()
        
        cv2.destroyAllWindows()
        
        if hasattr(self, 'hands') and self.hands:
            self.hands.close()
        
        stats = self.performance_monitor.get_stats()
        logger.info(f"Final Performance Stats: {stats}")
        logger.info("System shutdown complete")


def main():
    """Main entry point with improved error handling"""
    print("=" * 60)
    print("EMERGENCY GESTURE DETECTION SYSTEM")
    print("=" * 60)
    print("\nSystem Information:")
    print(f"   Python Version: {sys.version.split()[0]}")
    print(f"   OpenCV Version: {cv2.__version__}")
    print(f"   MediaPipe Version: {mp.__version__}")
    
    print("\nGesture Instructions:")
    print("   1. Fold your thumb inward (against palm)")
    print("   2. Rapidly open and close all four fingers together")
    print("   3. Repeat 3-5 times within 2-3 seconds")
    
    print("\nCancel Options:")
    print("   Show open palm for 3 seconds")
    print("   Press 'c' key")
    
    print("\nControls:")
    print("   'q' - Quit application")
    print("   'c' - Cancel pending alert")
    print("   'p' - Pause/Resume detection")
    print("   's' - Save manual snapshot")
    print("   'd' - Show debug information")
    print("   'r' - Reset system state")
    
    print(f"\nAuto-Exit Feature:")
    print(f"   System will automatically close after {config.IDLE_TIMEOUT} seconds of no hand detection")
    print("   Show your hand to keep the system running")
    
    print("\n" + "=" * 60)
    
    # Check email configuration
    is_valid, message = config.validate_email_config()
    if not is_valid:
        print(f"\n Email not configured: {message}")
        print("   Emergency alerts will not be sent!")
        print("   Create config/email_config.json from template to enable emails.\n")
    
    try:
        detector = EmergencyGestureDetector()
        detector.run()
    except KeyboardInterrupt:
        print("\n\n System interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n Fatal error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
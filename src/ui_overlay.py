"""
UI Overlay Module
Handles all on-screen display elements
"""

import cv2
import numpy as np
from typing import List
from src.config import config


class UIOverlay:
    """Manages on-screen UI elements"""
    
    def __init__(self):
        self.colors = {
            'primary': (0, 255, 255),    # Yellow
            'success': (0, 255, 0),      # Green
            'warning': (0, 165, 255),    # Orange
            'danger': (0, 0, 255),       # Red
            'info': (255, 255, 255),     # White
            'background': (0, 0, 0),     # Black
            'paused': (255, 255, 0)      # Cyan
        }
    
    def draw(self, frame: np.ndarray, finger_states: List[bool], cycle_count: int, 
             confidence: float, alert_triggered: bool, cancel_active: bool, 
             fps: float, gesture_active: bool = False, paused: bool = False,
             hand_detected: bool = True, idle_time: float = 0, time_remaining: float = 0) -> np.ndarray:
        """
        Draw complete UI overlay on frame.
        
        Args:
            frame: Video frame
            finger_states: List of finger states
            cycle_count: Current gesture cycle count
            confidence: Detection confidence (0-1)
            alert_triggered: Whether alert is triggered
            cancel_active: Whether cancel gesture is active
            fps: Current FPS
            gesture_active: Whether gesture pattern is active
            paused: Whether system is paused
            hand_detected: Whether hand is currently detected
            idle_time: How long no hand has been detected
            time_remaining: Time remaining before auto-exit
        """
        h, w = frame.shape[:2]
        
        # Create semi-transparent overlay
        overlay = frame.copy()
        
        # Main info panel
        cv2.rectangle(overlay, (10, 10), (260, 200), self.colors['background'], -1)
        
        # Alert banner (if triggered)
        if alert_triggered:
            cv2.rectangle(overlay, (0, 0), (w, 50), self.colors['danger'], -1)
            cv2.putText(overlay, "!!! EMERGENCY ALERT TRIGGERED !!!", (w//2 - 180, 35),
                       config.FONT, 0.6, (255, 255, 255), 2)
        
        # Paused banner
        if paused:
            cv2.rectangle(overlay, (w//2 - 100, 10), (w//2 + 100, 50), self.colors['paused'], -1)
            cv2.putText(overlay, "PAUSED", (w//2 - 40, 35), config.FONT, 0.7, (0, 0, 0), 2)
        
        # Cancel banner (if active)
        if cancel_active:
            cv2.rectangle(overlay, (w-250, 10), (w-10, 50), self.colors['warning'], -1)
            cv2.putText(overlay, "[ HAND ] CANCEL ACTIVE", (w-240, 35),
                       config.FONT, 0.5, (0, 0, 0), 1)
        
        # Idle warning overlay (if no hand detected)
        if not hand_detected and idle_time > 0:
            if time_remaining > 0 and time_remaining <= 5:
                # Urgent warning - red background
                cv2.rectangle(overlay, (w//2 - 200, h//2 - 50), (w//2 + 200, h//2 + 30), (0, 0, 255), -1)
                cv2.putText(overlay, "!!! NO HAND DETECTED !!!", (w//2 - 130, h//2 - 15), 
                           config.FONT, 0.6, (255, 255, 255), 2)
                cv2.putText(overlay, f"Exiting in {int(time_remaining)}s... Show your hand!", (w//2 - 190, h//2 + 15), 
                           config.FONT, 0.5, (255, 255, 255), 1)
            elif time_remaining > 0 and time_remaining <= 10:
                # Warning - yellow background
                cv2.rectangle(overlay, (w//2 - 180, h//2 - 40), (w//2 + 180, h//2 + 20), (0, 165, 255), -1)
                cv2.putText(overlay, "IDLE - No hand detected", (w//2 - 130, h//2 - 5), 
                           config.FONT, 0.5, (0, 0, 0), 1)
                cv2.putText(overlay, f"Exit in {int(time_remaining)}s", (w//2 - 80, h//2 + 15), 
                           config.FONT, 0.4, (0, 0, 0), 1)
        
        # Combine overlay with frame
        alpha = 0.6
        frame = cv2.addWeighted(overlay, alpha, frame, 1-alpha, 0)
        
        # Draw finger states with text labels (no emojis)
        y = 40
        cv2.putText(frame, "FINGER STATES:", (15, y), config.FONT, 0.5, 
                   self.colors['primary'], 1)
        
        # Finger labels without emojis
        finger_names = ["THUMB", "INDEX", "MIDDLE", "RING", "LITTLE"]
        
        for i, (name, is_active) in enumerate(zip(finger_names, finger_states)):
            y_pos = y + 25 + i * 20
            color = self.colors['success'] if is_active else self.colors['danger']
            status = "OPEN" if is_active else "FOLDED"
            cv2.putText(frame, f"{name}: {status}", (15, y_pos), 
                       config.FONT, 0.4, color, 1)
        
        # Hand detection indicator
        if not hand_detected:
            cv2.putText(frame, "HAND: NOT DETECTED", (15, y + 125), 
                       config.FONT, 0.4, self.colors['warning'], 1)
        else:
            cv2.putText(frame, "HAND: DETECTED", (15, y + 125), 
                       config.FONT, 0.4, self.colors['success'], 1)
        
        # Gesture progress bar
        y = 185
        cv2.putText(frame, f"GESTURE PROGRESS: {cycle_count}/{config.MIN_GESTURE_CYCLES}", 
                   (15, y), config.FONT, 0.4, self.colors['info'], 1)
        
        progress = min(1.0, cycle_count / config.MIN_GESTURE_CYCLES)
        bar_width = 230
        cv2.rectangle(frame, (15, y+5), (15+bar_width, y+20), (50, 50, 50), -1)
        
        color = self.colors['success'] if progress >= 1.0 else self.colors['warning']
        cv2.rectangle(frame, (15, y+5), (15+int(bar_width * progress), y+20), color, -1)
        
        # Confidence meter
        y = 215
        cv2.putText(frame, f"CONFIDENCE: {confidence*100:.0f}%", (15, y), 
                   config.FONT, 0.4, self.colors['info'], 1)
        
        conf_bar_width = 230
        cv2.rectangle(frame, (15, y+5), (15+conf_bar_width, y+20), (50, 50, 50), -1)
        conf_color = (0, int(255 * confidence), int(255 * (1-confidence)))
        cv2.rectangle(frame, (15, y+5), (15+int(conf_bar_width * confidence), y+20), 
                     conf_color, -1)
        
        # Gesture active indicator
        if gesture_active:
            cv2.circle(frame, (240, 170), 8, self.colors['success'], -1)
            cv2.putText(frame, "PATTERN ACTIVE", (255, 175), 
                       config.FONT, 0.4, self.colors['success'], 1)
        
        # FPS counter with color coding
        fps_color = self.colors['success'] if fps >= 30 else (self.colors['warning'] if fps >= 20 else self.colors['danger'])
        cv2.putText(frame, f"FPS: {fps:.1f}", (w-80, h-10), 
                   config.FONT, 0.4, fps_color, 1)
        
        # Instructions
        instructions = [
            "[Q] Quit",
            "[C] Cancel Alert",
            "[P] Pause/Resume",
            "Open Palm - Cancel"
        ]
        
        y_start = h - 95
        for i, instruction in enumerate(instructions):
            cv2.putText(frame, instruction, (10, y_start + i * 18), 
                       config.FONT, 0.35, (150, 150, 150), 1)
        
        return frame
    
    def draw_landmarks(self, frame: np.ndarray, landmarks, connections):
        """Draw hand landmarks with custom styling"""
        h, w = frame.shape[:2]
        
        # Draw connections
        if connections:
            for connection in connections:
                start_idx = connection[0]
                end_idx = connection[1]
                
                start = landmarks.landmark[start_idx]
                end = landmarks.landmark[end_idx]
                
                start_point = (int(start.x * w), int(start.y * h))
                end_point = (int(end.x * w), int(end.y * h))
                
                cv2.line(frame, start_point, end_point, (0, 255, 255), 2)
        
        # Draw landmarks
        for idx, landmark in enumerate(landmarks.landmark):
            cx, cy = int(landmark.x * w), int(landmark.y * h)
            
            # Color based on finger type
            if idx in [4, 8, 12, 16, 20]:  # Fingertips
                color = (0, 255, 0)
                radius = 5
            else:
                color = (0, 255, 255)
                radius = 3
            
            cv2.circle(frame, (cx, cy), radius, color, -1)
        
        return frame
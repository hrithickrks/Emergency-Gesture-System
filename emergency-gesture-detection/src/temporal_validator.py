"""
Temporal Validation Module
Validates gestures over time to reduce false positives
"""

import time
from collections import deque
from datetime import datetime
from src.config import config

class TemporalValidator:
    """Validates gesture detection temporally to prevent false alarms"""
    
    def __init__(self):
        self.confirmation_buffer = deque(maxlen=50)
        self.confirmation_count = 0
        self.alert_triggered = False
        self.cancel_requested = False
        self.cancel_start_time = None
        self.alert_time = None
        self.validation_window = 1.5  # seconds
        self.required_confirmations = 2
    
    def add_detection(self, is_detected, timestamp, confidence=1.0):
        """
        Add detection event to buffer and validate.
        
        Args:
            is_detected: Whether gesture was detected
            timestamp: Event timestamp
            confidence: Detection confidence (0-1)
        
        Returns:
            bool: True if alert should be triggered
        """
        self.confirmation_buffer.append({
            'timestamp': timestamp,
            'detected': is_detected,
            'confidence': confidence
        })
        
        # Clean old entries
        self._clean_buffer(timestamp)
        
        if is_detected:
            return self._validate(timestamp)
        
        return False
    
    def _clean_buffer(self, current_time):
        """Remove entries older than validation window"""
        cutoff = current_time - self.validation_window
        while self.confirmation_buffer and self.confirmation_buffer[0]['timestamp'] < cutoff:
            self.confirmation_buffer.popleft()
    
    def _validate(self, current_time):
        """Validate if enough confirmations exist"""
        # Count valid detections in window
        valid_detections = [
            d for d in self.confirmation_buffer 
            if d['detected'] and d['confidence'] > 0.6
        ]
        
        self.confirmation_count = len(valid_detections)
        
        # Check if we have enough confirmations
        if self.confirmation_count >= self.required_confirmations and not self.alert_triggered:
            # Additional check: confirmations must be spread out (not all at once)
            if len(valid_detections) >= 2:
                time_span = valid_detections[-1]['timestamp'] - valid_detections[0]['timestamp']
                if time_span >= 0.3:  # At least 300ms between first and last confirmation
                    self.alert_triggered = True
                    self.alert_time = current_time
                    return True
        
        return False
    
    def request_cancel(self, timestamp, gesture_type="open_hand"):
        """
        Request cancellation of pending alert.
        
        Args:
            timestamp: Current timestamp
            gesture_type: Type of cancel gesture
        
        Returns:
            bool: True if cancellation confirmed
        """
        if gesture_type == "open_hand":
            if self.cancel_start_time is None:
                self.cancel_start_time = timestamp
                return False
            elif timestamp - self.cancel_start_time >= config.CANCEL_GESTURE_DURATION:
                self.cancel_requested = True
                self.reset()
                return True
        else:
            # Immediate cancel for key press
            self.reset()
            return True
        
        return False
    
    def reset(self):
        """Reset validator state"""
        self.confirmation_buffer.clear()
        self.confirmation_count = 0
        self.alert_triggered = False
        self.cancel_requested = False
        self.cancel_start_time = None
        self.alert_time = None
    
    def get_status(self):
        """Get current validator status"""
        return {
            'alert_triggered': self.alert_triggered,
            'cancel_requested': self.cancel_requested,
            'confirmation_count': self.confirmation_count,
            'required_confirmations': self.required_confirmations,
            'time_since_alert': time.time() - self.alert_time if self.alert_time else None
        }
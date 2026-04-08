"""
Gesture Pattern Recognition Module
Identifies the distress pattern: four fingers opening/closing with thumb folded
"""

import time
from collections import deque
from src.config import config

class GesturePatternRecognizer:
    """
    Recognizes distress gesture pattern:
    - Thumb folded inward
    - All four fingers in same state (all open OR all closed)
    - State alternates between open and closed
    - Minimum 3 cycles within time window
    """
    
    def __init__(self):
        self.gesture_history = deque(maxlen=100)
        self.cycle_count = 0
        self.last_state = None
        self.cycle_start_time = None
        self.is_active = False
        self.state_history = deque(maxlen=10)
    
    def update(self, finger_states, timestamp):
        """
        Update recognizer with current finger states.
        
        Args:
            finger_states: List of [thumb_folded, index_open, middle_open, ring_open, little_open]
            timestamp: Current timestamp
        
        Returns:
            tuple: (is_distress_gesture, cycle_count, confidence)
        """
        thumb_folded, index, middle, ring, little = finger_states
        
        # Condition 1: Thumb must be folded
        if not thumb_folded:
            self._reset_if_inactive()
            return False, 0, 0.0
        
        # Condition 2: All four fingers must be in same state
        four_fingers_state = all([index, middle, ring, little])
        all_open = index and middle and ring and little
        all_closed = not (index or middle or ring or little)
        
        if not (all_open or all_closed):
            self._reset_if_inactive()
            return False, 0, 0.0
        
        # Determine current gesture state
        current_state = "open" if all_open else "closed"
        self.state_history.append(current_state)
        
        # Track state transitions (cycles)
        if self.last_state is None:
            # First detection
            self.last_state = current_state
            self.cycle_start_time = timestamp
            self.is_active = True
            self.cycle_count = 0
        
        elif current_state != self.last_state and self.is_active:
            # State changed - count half cycle
            self.cycle_count += 0.5
            self.last_state = current_state
            
            # Calculate confidence based on consistency
            elapsed = timestamp - self.cycle_start_time
            
            # Check if we've met minimum requirements
            if self.cycle_count >= config.MIN_GESTURE_CYCLES:
                if elapsed <= config.TIME_WINDOW:
                    # Successful detection
                    confidence = min(1.0, (self.cycle_count / config.MIN_GESTURE_CYCLES) * 
                                   (config.TIME_WINDOW / elapsed))
                    return True, int(self.cycle_count), confidence
        
        # Reset if time window exceeded
        if self.is_active and (timestamp - self.cycle_start_time) > config.TIME_WINDOW:
            self._reset()
        
        # Calculate current confidence (partial)
        confidence = 0.0
        if self.is_active and self.cycle_start_time:
            elapsed = timestamp - self.cycle_start_time
            if elapsed > 0:
                confidence = min(0.9, (self.cycle_count / config.MIN_GESTURE_CYCLES) * 
                               (config.TIME_WINDOW / elapsed))
        
        return False, int(self.cycle_count), confidence
    
    def _reset(self):
        """Reset recognition state"""
        self.cycle_count = 0
        self.last_state = None
        self.cycle_start_time = None
        self.is_active = False
        self.state_history.clear()
    
    def _reset_if_inactive(self):
        """Reset only if not active"""
        if not self.is_active:
            self._reset()
    
    def get_pattern_quality(self):
        """Get quality score of current pattern (0-1)"""
        if len(self.state_history) < 3:
            return 0.0
        
        # Check alternation pattern
        alternations = 0
        for i in range(1, len(self.state_history)):
            if self.state_history[i] != self.state_history[i-1]:
                alternations += 1
        
        return alternations / len(self.state_history)
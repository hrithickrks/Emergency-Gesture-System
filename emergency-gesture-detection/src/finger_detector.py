"""
Finger State Detection Module
Detects open/closed state of each finger using MediaPipe landmarks
"""

import numpy as np
from typing import List, Tuple, Optional
from src.config import config

class FingerStateDetector:
    """Detects finger states from hand landmarks with improved accuracy"""
    
    def __init__(self):
        self.last_states: Optional[List[bool]] = None
        self.frame_history = []
        self.smoothing_window = 3
    
    def is_finger_open(self, landmarks, tip_id: int, pip_id: int, is_thumb: bool = False) -> bool:
        """
        Determine if a finger is open.
        
        Args:
            landmarks: MediaPipe hand landmarks
            tip_id: Landmark ID for fingertip
            pip_id: Landmark ID for PIP joint (or IP for thumb)
            is_thumb: Whether this is the thumb (uses different logic)
        
        Returns:
            bool: True if finger is open
        """
        if not is_thumb:
            # Standard fingers: compare Y-coordinates
            tip_y = landmarks[tip_id].y
            pip_y = landmarks[pip_id].y
            return tip_y < pip_y - config.OPEN_THRESHOLD
        else:
            # Improved thumb detection: check both distance and angle
            thumb_tip = landmarks[config.THUMB_TIP_ID]
            thumb_ip = landmarks[config.THUMB_IP_ID]
            index_mcp = landmarks[5]  # Index finger MCP joint
            wrist = landmarks[config.WRIST_ID]
            
            # Calculate thumb distance from palm
            distance_to_palm = np.sqrt(
                (thumb_tip.x - wrist.x) ** 2 + 
                (thumb_tip.y - wrist.y) ** 2
            )
            
            # Calculate thumb-index distance
            distance_to_index = np.sqrt(
                (thumb_tip.x - index_mcp.x) ** 2 + 
                (thumb_tip.y - index_mcp.y) ** 2
            )
            
            # Thumb is folded if close to palm or close to index finger
            is_folded = distance_to_palm < 0.15 or distance_to_index < 0.12
            
            # Also check if thumb is pointing inward
            thumb_vector = (thumb_tip.x - thumb_ip.x, thumb_tip.y - thumb_ip.y)
            palm_vector = (wrist.x - thumb_ip.x, wrist.y - thumb_ip.y)
            
            if thumb_vector[0] != 0:
                dot_product = thumb_vector[0] * palm_vector[0] + thumb_vector[1] * palm_vector[1]
                is_pointing_inward = dot_product > 0
                is_folded = is_folded or is_pointing_inward
            
            return not is_folded
    
    def get_all_finger_states(self, landmarks) -> List[bool]:
        """
        Get states for all 5 fingers with smoothing.
        
        Returns:
            list: [thumb_folded, index_open, middle_open, ring_open, little_open]
        """
        states = []
        
        # Thumb (folded inward = True for distress gesture)
        thumb_folded = not self.is_finger_open(
            landmarks, config.THUMB_TIP_ID, config.THUMB_IP_ID, is_thumb=True
        )
        states.append(thumb_folded)
        
        # Four fingers
        for tip_id, pip_id in zip(config.FINGER_TIP_IDS, config.FINGER_PIP_IDS):
            is_open = self.is_finger_open(landmarks, tip_id, pip_id, is_thumb=False)
            states.append(is_open)
        
        # Apply temporal smoothing
        if self.last_states is not None:
            states = self._smooth_states(states)
        
        self.last_states = states
        return states
    
    def _smooth_states(self, current_states: List[bool]) -> List[bool]:
        """Apply temporal smoothing to reduce jitter"""
        if not self.last_states:
            return current_states
        
        smoothed = []
        for current, last in zip(current_states, self.last_states):
            # Only change if state persists
            if current != last:
                # Check history for consistency
                self.frame_history.append(current)
                if len(self.frame_history) > self.smoothing_window:
                    self.frame_history.pop(0)
                
                # Count recent states
                if len(self.frame_history) >= self.smoothing_window:
                    true_count = sum(self.frame_history)
                    if true_count > self.smoothing_window / 2:
                        smoothed.append(True)
                    else:
                        smoothed.append(False)
                else:
                    smoothed.append(last)
            else:
                smoothed.append(current)
        
        return smoothed
    
    def get_finger_state_text(self, states: List[bool]) -> str:
        """Get human-readable finger states"""
        finger_names = ["Thumb", "Index", "Middle", "Ring", "Little"]
        result = []
        for name, state in zip(finger_names, states):
            status = "✓" if state else "✗"
            result.append(f"{name}: {status}")
        return " | ".join(result)
    
    def is_valid_hand(self, landmarks) -> bool:
        """Check if hand detection is valid (all landmarks present)"""
        try:
            # Check if we have all required landmarks
            required_ids = [4, 8, 12, 16, 20] + [3, 6, 10, 14, 18, 0]
            for idx in required_ids:
                if idx >= len(landmarks):
                    return False
                if not hasattr(landmarks[idx], 'x'):
                    return False
            return True
        except (IndexError, AttributeError):
            return False
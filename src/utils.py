"""
Utility Functions Module
"""

import logging
import time
from datetime import datetime
from pathlib import Path
import json
import threading
from typing import Optional, Dict, Any
from functools import wraps

def setup_logging(log_level=logging.INFO, log_name: Optional[str] = None):
    """Setup logging configuration with rotation support"""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"{log_name or 'gesture_detection'}_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Stream handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)
    
    return logging.getLogger(__name__)

def calculate_fps(start_time: float, frame_count: int) -> float:
    """Calculate FPS safely"""
    elapsed = time.time() - start_time
    return frame_count / elapsed if elapsed > 0 else 0.0

def timeit(func):
    """Decorator to measure function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        if hasattr(wrapper, 'logger'):
            wrapper.logger.debug(f"{func.__name__} took {elapsed*1000:.2f}ms")
        return result
    return wrapper

class PerformanceMonitor:
    """Monitor system performance with statistics"""
    
    def __init__(self, max_samples: int = 100):
        self.frame_times = []
        self.detection_times = []
        self.max_samples = max_samples
        self.lock = threading.Lock()
    
    def add_frame_time(self, duration: float):
        """Add frame processing time"""
        with self.lock:
            self.frame_times.append(duration)
            if len(self.frame_times) > self.max_samples:
                self.frame_times.pop(0)
    
    def add_detection_time(self, duration: float):
        """Add detection time"""
        with self.lock:
            self.detection_times.append(duration)
            if len(self.detection_times) > self.max_samples:
                self.detection_times.pop(0)
    
    def get_stats(self) -> Dict[str, float]:
        """Get performance statistics"""
        with self.lock:
            avg_frame = sum(self.frame_times) / len(self.frame_times) if self.frame_times else 0
            avg_detection = sum(self.detection_times) / len(self.detection_times) if self.detection_times else 0
            
            return {
                'avg_frame_time_ms': avg_frame * 1000,
                'avg_detection_time_ms': avg_detection * 1000,
                'fps': 1 / avg_frame if avg_frame > 0 else 0,
                'frame_samples': len(self.frame_times),
                'detection_samples': len(self.detection_times)
            }
    
    def reset(self):
        """Reset all metrics"""
        with self.lock:
            self.frame_times.clear()
            self.detection_times.clear()

class RateLimiter:
    """Rate limiter for operations"""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
        self.lock = threading.Lock()
    
    def allow(self) -> bool:
        """Check if operation is allowed"""
        with self.lock:
            now = time.time()
            # Remove old calls
            self.calls = [t for t in self.calls if now - t < self.time_window]
            
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
            return False
"""
Configuration Module - Load settings from environment or config file
"""

import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class Config:
    """Main configuration class with validation"""
    
    def __init__(self):
        # Define paths FIRST before loading config
        self.BASE_DIR = Path(__file__).parent.parent
        self.SNAPSHOT_DIR = self.BASE_DIR / "snapshots"
        self.LOG_DIR = self.BASE_DIR / "logs"
        self.CONFIG_DIR = self.BASE_DIR / "config"
        
        # Create directories
        self.SNAPSHOT_DIR.mkdir(exist_ok=True)
        self.LOG_DIR.mkdir(exist_ok=True)
        self.CONFIG_DIR.mkdir(exist_ok=True)
        
        # Then load configuration
        self.load_config()
        
    def load_config(self):
        """Load configuration from file or environment variables"""
        # Gesture parameters
        self.MIN_GESTURE_CYCLES = int(os.getenv('MIN_GESTURE_CYCLES', 3))
        self.TIME_WINDOW = float(os.getenv('TIME_WINDOW', 2.5))
        
        # Finger landmark IDs (MediaPipe)
        self.FINGER_TIP_IDS = [8, 12, 16, 20]  # Index, Middle, Ring, Little
        self.FINGER_PIP_IDS = [6, 10, 14, 18]
        self.THUMB_TIP_ID = 4
        self.THUMB_IP_ID = 3
        self.WRIST_ID = 0
        
        # Detection thresholds
        self.OPEN_THRESHOLD = float(os.getenv('OPEN_THRESHOLD', 0.05))
        self.CONFIDENCE_THRESHOLD = float(os.getenv('CONFIDENCE_THRESHOLD', 0.7))
        self.MIN_CONFIRMATIONS = int(os.getenv('MIN_CONFIRMATIONS', 2))
        self.VALIDATION_WINDOW = float(os.getenv('VALIDATION_WINDOW', 1.5))
        
        # Email configuration (load from file or env)
        self.load_email_config()
        
        # Cancel mechanism
        self.CANCEL_GESTURE_DURATION = float(os.getenv('CANCEL_GESTURE_DURATION', 3.0))
        self.ALERT_TIMEOUT = float(os.getenv('ALERT_TIMEOUT', 30))
        self.EMAIL_COOLDOWN = int(os.getenv('EMAIL_COOLDOWN', 60))
        
        # Idle detection (Auto-exit when no hand detected)
        self.IDLE_TIMEOUT = float(os.getenv('IDLE_TIMEOUT', 30))  # Seconds before auto-exit if no hand detected
        self.IDLE_WARNING_TIME = float(os.getenv('IDLE_WARNING_TIME', 25))  # Seconds before showing warning
        
        # Display settings
        self.WINDOW_NAME = "Emergency Gesture Detection System"
        self.FONT = cv2.FONT_HERSHEY_SIMPLEX
        
        # Camera settings
        self.CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', 640))
        self.CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', 480))
        self.CAMERA_FPS = int(os.getenv('CAMERA_FPS', 30))
        self.CAMERA_INDEX = int(os.getenv('CAMERA_INDEX', 0))
        
        # Performance settings
        self.PERFORMANCE_SAMPLES = int(os.getenv('PERFORMANCE_SAMPLES', 100))
        
        # Validation
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration values"""
        if self.MIN_GESTURE_CYCLES < 1:
            raise ValueError("MIN_GESTURE_CYCLES must be at least 1")
        if self.TIME_WINDOW <= 0:
            raise ValueError("TIME_WINDOW must be positive")
        if self.OPEN_THRESHOLD < 0 or self.OPEN_THRESHOLD > 1:
            raise ValueError("OPEN_THRESHOLD must be between 0 and 1")
        if self.CONFIDENCE_THRESHOLD < 0 or self.CONFIDENCE_THRESHOLD > 1:
            raise ValueError("CONFIDENCE_THRESHOLD must be between 0 and 1")
    
    def load_email_config(self):
        """Load email configuration from JSON file or environment"""
        email_config_path = self.CONFIG_DIR / "email_config.json"
        template_path = self.CONFIG_DIR / "email_config_template.json"
        
        # Create template if it doesn't exist
        if not template_path.exists():
            self._create_email_template(template_path)
        
        if email_config_path.exists():
            try:
                with open(email_config_path, 'r') as f:
                    email_config = json.load(f)
                    self.SMTP_SERVER = email_config.get('SMTP_SERVER', 'smtp.gmail.com')
                    self.SMTP_PORT = int(email_config.get('SMTP_PORT', 587))
                    self.SENDER_EMAIL = email_config.get('SENDER_EMAIL', '')
                    self.SENDER_PASSWORD = email_config.get('SENDER_PASSWORD', '')
                    self.RECEIVER_EMAILS = email_config.get('RECEIVER_EMAILS', [])
                    self.EMAIL_SUBJECT_PREFIX = email_config.get('EMAIL_SUBJECT_PREFIX', '🚨 EMERGENCY ALERT')
            except Exception as e:
                logger.warning(f"Could not load email config: {e}")
                self._set_default_email_config()
        else:
            # Fallback to environment variables
            self.SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            self.SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
            self.SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
            self.SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')
            self.RECEIVER_EMAILS = os.getenv('RECEIVER_EMAILS', '').split(',') if os.getenv('RECEIVER_EMAILS') else []
            self.EMAIL_SUBJECT_PREFIX = os.getenv('EMAIL_SUBJECT_PREFIX', '🚨 EMERGENCY ALERT')
    
    def _create_email_template(self, template_path: Path):
        """Create email configuration template"""
        template = {
            "SMTP_SERVER": "smtp.gmail.com",
            "SMTP_PORT": 587,
            "SENDER_EMAIL": "your_email@gmail.com",
            "SENDER_PASSWORD": "your_app_password_here",
            "RECEIVER_EMAILS": [
                "emergency_contact1@example.com",
                "emergency_contact2@example.com"
            ],
            "EMAIL_SUBJECT_PREFIX": "🚨 EMERGENCY ALERT"
        }
        
        with open(template_path, 'w') as f:
            json.dump(template, f, indent=4)
        
        logger.info(f"Email template created at {template_path}")
    
    def _set_default_email_config(self):
        """Set default email configuration"""
        self.SMTP_SERVER = 'smtp.gmail.com'
        self.SMTP_PORT = 587
        self.SENDER_EMAIL = ''
        self.SENDER_PASSWORD = ''
        self.RECEIVER_EMAILS = []
        self.EMAIL_SUBJECT_PREFIX = '🚨 EMERGENCY ALERT'
    
    def validate_email_config(self):
        """Validate email configuration before sending"""
        if not self.SENDER_EMAIL or '@' not in self.SENDER_EMAIL:
            return False, "Invalid sender email address"
        if not self.SENDER_PASSWORD or len(self.SENDER_PASSWORD) < 8:
            return False, "Sender password missing or too short"
        if not self.RECEIVER_EMAILS or self.RECEIVER_EMAILS == ['']:
            return False, "No receiver emails configured"
        return True, "OK"


# Import cv2 after config to avoid circular imports
import cv2

# Global config instance
config = Config()
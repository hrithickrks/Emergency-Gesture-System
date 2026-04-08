"""
Email Alert Module
Sends emergency emails with snapshot attachments
"""
import smtplib
import threading
import logging
import time
import json
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# Import config with proper path handling
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config import config

class EmailAlertSender:
    """Handles email sending for emergency alerts"""
    
    def __init__(self):
        self.is_sending = False
        self.last_send_time = None
        self.send_cooldown = 60  # seconds between emails
        self.alert_log_path = Path(__file__).parent.parent / "logs" / "alerts.json"
    
    def send_alert(self, snapshot_path, frame=None, custom_message=None):
        """
        Send emergency alert email.
        
        Args:
            snapshot_path: Path to snapshot image
            frame: Optional video frame
            custom_message: Optional custom message
        
        Returns:
            bool: True if sent successfully
        """
        # Validate configuration
        is_valid, message = config.validate_email_config()
        if not is_valid:
            logger.error(f"Email config invalid: {message}")
            self._save_local_alert(snapshot_path, custom_message, message)
            return False
        
        # Check cooldown
        if self.last_send_time:
            elapsed = (datetime.now() - self.last_send_time).total_seconds()
            if elapsed < self.send_cooldown:
                logger.warning(f"Send cooldown active ({elapsed:.0f}s remaining)")
                return False
        
        try:
            # Create email
            msg = MIMEMultipart()
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Emergency-focused subject line - no project name
            msg['Subject'] = f'⚠️ URGENT: Person in Distress - Immediate Attention Required - {current_time}'
            msg['From'] = config.SENDER_EMAIL
            msg['To'] = ', '.join(config.RECEIVER_EMAILS)
            
            # Email body
            body = self._create_email_body(current_time, custom_message)
            msg.attach(MIMEText(body, 'html'))
            
            # Attach snapshot
            if snapshot_path and Path(snapshot_path).exists():
                with open(snapshot_path, 'rb') as f:
                    img = MIMEImage(f.read(), name=Path(snapshot_path).name)
                    msg.attach(img)
            
            # Send email
            logger.info(f"Connecting to {config.SMTP_SERVER}:{config.SMTP_PORT}...")
            with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT, timeout=30) as server:
                server.starttls()
                server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
                server.send_message(msg)
            
            self.last_send_time = datetime.now()
            logger.info(f"✅ Emergency alert sent to {len(config.RECEIVER_EMAILS)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            self._save_local_alert(snapshot_path, custom_message, str(e))
            return False
    
    def _save_local_alert(self, snapshot_path, custom_message=None, error=None):
        """Save alert locally if email fails"""
        try:
            alert_data = {
                "timestamp": datetime.now().isoformat(),
                "snapshot_path": snapshot_path,
                "custom_message": custom_message,
                "error": error
            }
            
            # Load existing alerts
            alerts = []
            if self.alert_log_path.exists():
                with open(self.alert_log_path, 'r') as f:
                    alerts = json.load(f)
            
            alerts.append(alert_data)
            
            # Keep last 100 alerts
            if len(alerts) > 100:
                alerts = alerts[-100:]
            
            with open(self.alert_log_path, 'w') as f:
                json.dump(alerts, f, indent=2)
            
            logger.info(f"Alert saved locally: {self.alert_log_path}")
        except Exception as e:
            logger.error(f"Failed to save local alert: {e}")
    
    def send_async(self, snapshot_path, frame=None, callback=None):
        """Send email in background thread"""
        if self.is_sending:
            logger.warning("Already sending email, skipping")
            return False
        
        def send_thread():
            self.is_sending = True
            try:
                success = self.send_alert(snapshot_path, frame)
                if callback:
                    callback(success)
            finally:
                self.is_sending = False
        
        thread = threading.Thread(target=send_thread, daemon=True)
        thread.start()
        return True
    
    def _create_email_body(self, timestamp, custom_message=None):
        """Create HTML email body for emergency alert"""
        base_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #cc0000;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #ffffff;
                    padding: 30px;
                    border: 1px solid #ddd;
                    border-top: none;
                    border-radius: 0 0 5px 5px;
                }}
                .alert-box {{
                    background-color: #fff3f3;
                    border-left: 4px solid #cc0000;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .info-box {{
                    background-color: #f5f5f5;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 5px;
                }}
                .urgent {{
                    color: #cc0000;
                    font-weight: bold;
                    font-size: 18px;
                }}
                .footer {{
                    font-size: 12px;
                    color: #666;
                    margin-top: 30px;
                    padding-top: 10px;
                    border-top: 1px solid #ddd;
                    text-align: center;
                }}
                .button {{
                    background-color: #cc0000;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ URGENT ATTENTION REQUIRED ⚠️</h1>
                </div>
                
                <div class="content">
                    <div class="alert-box">
                        <p class="urgent">‼️ IMMEDIATE ACTION NEEDED ‼️</p>
                        <p>This person may be in distress and requires immediate assistance.</p>
                    </div>
                    
                    <div class="info-box">
                        <p><strong>🕐 Time of Alert:</strong> {timestamp}</p>
                        <p><strong>📍 Location:</strong> Camera/Monitoring System</p>
                        <p><strong>⚠️ Status:</strong> <span style="color:#cc0000; font-weight:bold;">ACTIVE EMERGENCY SIGNAL</span></p>
                    </div>
                    
                    <div class="info-box">
                        <p><strong>🚨 What happened:</strong></p>
                        <p>An emergency distress signal has been detected. The person may be:</p>
                        <ul>
                            <li>In physical danger</li>
                            <li>Experiencing a medical emergency</li>
                            <li>Requiring immediate assistance</li>
                            <li>Unable to call for help verbally</li>
                        </ul>
                    </div>
                    
                    <div class="info-box">
                        <p><strong>📸 Evidence:</strong></p>
                        <p>A snapshot has been attached to this email for your reference.</p>
                        <p><strong>Action Required:</strong> Please verify the person's safety immediately.</p>
                    </div>
                    
                    <div class="alert-box">
                        <p><strong>🔴 RECOMMENDED ACTIONS:</strong></p>
                        <ol>
                            <li>Check on the person immediately</li>
                            <li>Call emergency services if needed</li>
                            <li>Contact local authorities</li>
                            <li>Ensure the person is safe</li>
                        </ol>
                    </div>
        """
        
        if custom_message:
            base_body += f"""
                    <div class="info-box">
                        <p><strong>📝 Additional Information:</strong></p>
                        <p>{custom_message}</p>
                    </div>
            """
        
        base_body += f"""
                    <div class="footer">
                        <p>This is an automated emergency alert from a monitoring system.</p>
                        <p>Please take immediate action. Do not ignore this message.</p>
                        <p>Alert ID: {abs(hash(timestamp))}</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return base_body
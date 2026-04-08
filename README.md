# Emergency Gesture Detection System

A real-time computer vision system that detects distress gestures and sends immediate email alerts to emergency contacts.

## 🚨 Features

- **Real-time Hand Tracking** - Uses MediaPipe for accurate hand landmark detection
- **Distress Gesture Recognition** - Detects rapid open/close of all four fingers with thumb folded
- **Instant Email Alerts** - Sends emergency emails with snapshot attachments
- **Cancel Mechanism** - Open palm gesture or keyboard shortcut to cancel alerts
- **Performance Optimized** - ~50 FPS with minimal latency
- **Idle Auto-Exit** - Automatically closes after 30 seconds of inactivity

## 🎯 Gesture Instructions

1. Fold your thumb inward (against palm)
2. Rapidly open and close all four fingers together
3. Repeat 3-5 times within 2-3 seconds

## 🛡️ Cancel Options

- Show open palm for 3 seconds
- Press 'c' key

## ⌨️ Controls

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `c` | Cancel pending alert |
| `p` | Pause/Resume detection |
| `s` | Save manual snapshot |
| `d` | Show debug information |
| `r` | Reset system state |

## 📋 Requirements

- Python 3.8+
- Webcam
- Gmail account (for email alerts)

## 🔧 Installation

1. **Clone the repository**
```bash
git clone https://github.com/YOUR_USERNAME/emergency-gesture-detection.git
cd emergency-gesture-detection
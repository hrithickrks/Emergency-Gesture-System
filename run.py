#!/usr/bin/env python3
"""
Quick launcher for Emergency Gesture Detection System
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.main import main

if __name__ == "__main__":
    # Check if running on Linux/Mac and set execute permissions
    if sys.platform != "win32":
        os.chmod(__file__, 0o755)
    
    sys.exit(main())
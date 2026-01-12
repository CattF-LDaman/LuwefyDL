#!/usr/bin/env python3
"""
Simple launcher script for the YouTube to Navidrome Music Importer
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    from music_importer.main import *
    # The ui.run() call is already in main.py when run as __main__


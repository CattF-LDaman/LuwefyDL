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
    # Import the main module to register routes
    import music_importer.main
    
    # Import ui to run the app
    from nicegui import ui
    
    # Run the app
    ui.run(
        title="LuwefyDL",
        favicon="🎵",
        dark=True,
        port=8080,
        reload=False
    )


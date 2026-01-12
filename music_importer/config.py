"""
Configuration management for the music importer
"""

import os
from pathlib import Path


class Config:
    """Configuration for music library paths and settings"""
    
    def __init__(self):
        # Default music library path - can be overridden by environment variable
        # On Linux server: /mnt/TOPHDD/music_library
        # On Windows/WSL: can be set via environment variable
        self.default_music_library = os.getenv(
            "MUSIC_LIBRARY_PATH",
            "/mnt/TOPHDD/music_library" if os.name != 'nt' else "C:/Music"
        )
        
        # Temporary directory for downloads
        self.temp_dir = Path(__file__).parent.parent / "temp"
        self.temp_dir.mkdir(exist_ok=True)
    
    def get_music_library_path(self):
        """Get the music library path, creating it if necessary"""
        path = Path(self.default_music_library)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    
    def get_temp_dir(self):
        """Get the temporary directory path"""
        return str(self.temp_dir)


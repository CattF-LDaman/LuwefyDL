"""
Configuration management for the music importer
"""

import os
from pathlib import Path


class Config:
    """Configuration for music library paths and settings"""

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.is_docker = os.getenv("DOCKER", "").lower() in ("1", "true", "yes")

        if os.getenv("MUSIC_LIBRARY_PATH"):
            self.default_music_library = os.getenv("MUSIC_LIBRARY_PATH")
        elif self.is_docker:
            self.default_music_library = "/data/music"
        else:
            self.default_music_library = str(self.project_root / "data" / "music")

        temp_env = os.getenv("TEMP_DIR")
        self.temp_dir = Path(temp_env) if temp_env else self.project_root / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.host = os.getenv(
            "HOST",
            "0.0.0.0" if self.is_docker else "127.0.0.1",
        )
        self.port = int(os.getenv("PORT", "8080"))
        show_default = "false" if self.is_docker else "true"
        self.show_browser = os.getenv("SHOW_BROWSER", show_default).lower() in (
            "1",
            "true",
            "yes",
        )
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    def get_music_library_path(self):
        """Get the music library path, creating it if necessary"""
        path = Path(self.default_music_library)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def get_temp_dir(self):
        """Get the temporary directory path"""
        return str(self.temp_dir)

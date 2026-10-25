import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURE_MP3 = Path(__file__).resolve().parent / "fixtures" / "silence.mp3"


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Point library and temp dirs at pytest tmp_path."""
    music = tmp_path / "music"
    temp = tmp_path / "temp"
    music.mkdir()
    temp.mkdir()
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", str(music))
    monkeypatch.setenv("TEMP_DIR", str(temp))
    monkeypatch.delenv("DOCKER", raising=False)
    return {"music": music, "temp": temp}


@pytest.fixture
def sample_mp3(isolated_env) -> Path:
    path = isolated_env["temp"] / "sample.mp3"
    shutil.copy(FIXTURE_MP3, path)
    return path


@pytest.fixture
def sample_mp3_with_tags(isolated_env) -> Path:
    path = isolated_env["temp"] / "tagged.mp3"
    shutil.copy(FIXTURE_MP3, path)
    return path

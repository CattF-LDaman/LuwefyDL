import os

from music_importer.config import Config


def test_default_paths_use_project_data_and_temp(isolated_env, monkeypatch):
    monkeypatch.delenv("MUSIC_LIBRARY_PATH", raising=False)
    cfg = Config()
    assert cfg.default_music_library == str(
        cfg.project_root / "data" / "music"
    )
    assert cfg.get_temp_dir() == str(isolated_env["temp"])


def test_music_library_env_override(isolated_env, monkeypatch):
    custom = str(isolated_env["music"] / "custom_lib")
    monkeypatch.setenv("MUSIC_LIBRARY_PATH", custom)
    cfg = Config()
    assert cfg.get_music_library_path() == custom
    assert os.path.isdir(custom)


def test_docker_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("DOCKER", "1")
    monkeypatch.delenv("MUSIC_LIBRARY_PATH", raising=False)
    monkeypatch.setenv("TEMP_DIR", str(tmp_path / "temp"))
    cfg = Config()
    assert cfg.default_music_library == "/data/music"
    assert cfg.host == "0.0.0.0"
    assert cfg.show_browser is False


def test_host_port_and_show_browser(monkeypatch, isolated_env):
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("SHOW_BROWSER", "false")
    cfg = Config()
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 9000
    assert cfg.show_browser is False

from tools.bootstrap_config import ensure_config
from app.core.config import Settings


def test_settings_default_access_key_and_random_secret():
    first = Settings(_env_file=None)
    second = Settings(_env_file=None)

    assert first.access_key == "ferkim"
    assert len(first.secret_key) >= 60
    assert first.secret_key != second.secret_key


def test_first_run_generates_and_persists_secret(tmp_path):
    example = tmp_path / ".env.example"
    env_file = tmp_path / ".env"
    example.write_text(
        "ACCESS_KEY=ferkim\nSECRET_KEY=GENERATE_ON_FIRST_START\n", encoding="utf-8"
    )

    assert ensure_config(env_file, example) is True
    first_config = env_file.read_text(encoding="utf-8")
    secret = next(line.partition("=")[2] for line in first_config.splitlines() if line.startswith("SECRET_KEY="))

    assert len(secret) >= 60
    assert "ACCESS_KEY=ferkim" in first_config
    assert ensure_config(env_file, example) is False
    assert env_file.read_text(encoding="utf-8") == first_config


def test_existing_custom_access_key_is_preserved_and_legacy_secret_rotates(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ACCESS_KEY=my-private-key\nSECRET_KEY=please-change-this-development-secret\n",
        encoding="utf-8",
    )
    example = tmp_path / ".env.example"
    example.write_text("", encoding="utf-8")

    assert ensure_config(env_file, example) is True
    config = env_file.read_text(encoding="utf-8")
    assert "ACCESS_KEY=my-private-key" in config
    assert "SECRET_KEY=please-change-this-development-secret" not in config

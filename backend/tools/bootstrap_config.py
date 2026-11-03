from pathlib import Path
import secrets


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
EXAMPLE_PATH = ROOT / ".env.example"
PLACEHOLDER_SECRETS = {"", "GENERATE_ON_FIRST_START", "please-change-this-development-secret"}
LEGACY_ACCESS_KEY = "fiker-mc-login-demo-key"


def ensure_config(env_path: Path = ENV_PATH, example_path: Path = EXAMPLE_PATH) -> bool:
    was_missing = not env_path.exists()
    if not was_missing:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    else:
        lines = example_path.read_text(encoding="utf-8").splitlines()

    changed = False
    seen = set()
    for index, line in enumerate(lines):
        key, separator, value = line.partition("=")
        if not separator:
            continue
        seen.add(key)
        if key == "SECRET_KEY" and value.strip() in PLACEHOLDER_SECRETS:
            lines[index] = f"SECRET_KEY={secrets.token_urlsafe(48)}"
            changed = True
        elif key == "ACCESS_KEY" and value == LEGACY_ACCESS_KEY:
            lines[index] = "ACCESS_KEY=ferkim"
            changed = True

    if "ACCESS_KEY" not in seen:
        lines.append("ACCESS_KEY=ferkim")
        changed = True
    if "SECRET_KEY" not in seen:
        lines.append(f"SECRET_KEY={secrets.token_urlsafe(48)}")
        changed = True

    if changed or not env_path.exists():
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed or was_missing


if __name__ == "__main__":
    created = not ENV_PATH.exists()
    ensure_config()
    print("Created local .env with a random signing key." if created else "Local .env is ready.")

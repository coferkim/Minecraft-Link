from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
OUTPUT = ROOT / "dist" / "Minecraft-Link-Windows-x64.zip"


def run(command: list[str], cwd: Path = ROOT) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, dirs_exist_ok=True)


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("The portable Windows package must be built on Windows.")

    npm = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm:
        raise SystemExit("Node.js and npm are required to build the release package.")

    run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "backend" / "requirements.txt")])
    run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "packaging" / "requirements-build.txt")])
    run([npm, "ci"], cwd=FRONTEND)
    run([npm, "run", "build"], cwd=FRONTEND)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="minecraft-link-release-") as temp_name:
        temp = Path(temp_name)
        pyinstaller_dist = temp / "pyinstaller-dist"
        run(
            [
                sys.executable,
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                "--onedir",
                "--console",
                "--name",
                "MinecraftLink",
                "--paths",
                str(ROOT / "backend"),
                "--distpath",
                str(pyinstaller_dist),
                "--workpath",
                str(temp / "pyinstaller-work"),
                "--specpath",
                str(temp / "pyinstaller-spec"),
                str(ROOT / "backend" / "launcher.py"),
            ]
        )

        package = temp / "Minecraft-Link-Windows-x64"
        copy_tree(pyinstaller_dist / "MinecraftLink", package)
        copy_tree(FRONTEND / "dist", package / "frontend" / "dist")
        copy_tree(ROOT / "docs", package / "docs")
        shutil.copy2(ROOT / ".env.example", package / ".env.example")
        shutil.copy2(ROOT / "README.md", package / "README.md")
        shutil.copy2(ROOT / "LICENSE", package / "LICENSE")
        shutil.copy2(ROOT / "packaging" / "windows" / "start.cmd", package / "start.cmd")

        with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in package.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(package.parent))

    print(f"Release package created: {OUTPUT}")


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "packages" / "wyrmctl"


def test_package_metadata_urls_point_to_groupsum_wyrmctl() -> None:
    metadata = tomllib.loads((PACKAGE / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["urls"] == {
        "Homepage": "https://github.com/groupsum/wyrmctl",
        "Documentation": "https://github.com/groupsum/wyrmctl/tree/master/docs",
        "Issues": "https://github.com/groupsum/wyrmctl/issues",
        "Repository": "https://github.com/groupsum/wyrmctl",
    }


def test_installed_console_script_smoke_in_clean_environment(tmp_path: Path) -> None:
    uv = shutil.which("uv")
    assert uv is not None
    work_root = ROOT / ".tmp" / f"pkg-smoke-{tmp_path.name}"
    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True)
    dist = work_root / "dist"
    subprocess.run([uv, "build", "--package", "wyrmctl", "--out-dir", str(dist)], cwd=ROOT, check=True)
    wheel = next(dist.glob("wyrmctl-*.whl"))
    venv = work_root / "venv"
    subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(venv)], check=True)
    if os.name == "nt":
        python = venv / "Scripts" / "python.exe"
    else:
        python = venv / "bin" / "python"

    subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--no-deps",
            "--reinstall",
            "--python",
            str(python),
            str(wheel),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    result = subprocess.run(
        [str(python), "-m", "wyrmctl", "--version"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert result.stdout.strip().startswith("wyrmctl ")

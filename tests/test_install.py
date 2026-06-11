"""Installer smoke test in a TEMP COPY (never pollutes the dev venv/.env/kernels).

Slow + needs network, so it is opt-in: set HA_TEST_INSTALL=1 to run. CI runs it on
ubuntu/macos/windows via .github/workflows/ci.yml.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RUN = os.getenv("HA_TEST_INSTALL") == "1"
pytestmark = pytest.mark.skipif(not RUN, reason="set HA_TEST_INSTALL=1 to run the slow installer test")

_IGNORE = shutil.ignore_patterns(".venv", ".git", "__pycache__", "cache", "*.pyc", ".pytest_cache")


def _copy_repo(dst: Path) -> None:
    shutil.copytree(ROOT, dst, ignore=_IGNORE)


def test_install_sh_then_import(tmp_path):
    if sys.platform.startswith("win"):
        pytest.skip("install.sh is POSIX; Windows uses install.ps1 (covered in CI)")
    repo = tmp_path / "repo"
    _copy_repo(repo)
    # install.sh runs `ipykernel install --user`; isolate Jupyter's dirs into tmp_path so it
    # can't overwrite the real ~/.../Jupyter/kernels — a global 'health-agent' kernel pointing
    # at this throwaway venv would break JupyterLab once tmp_path is cleaned up.
    env = {**os.environ,
           "JUPYTER_DATA_DIR": str(tmp_path / "jupyter" / "data"),
           "JUPYTER_CONFIG_DIR": str(tmp_path / "jupyter" / "config"),
           "JUPYTER_RUNTIME_DIR": str(tmp_path / "jupyter" / "runtime")}
    r = subprocess.run(["bash", "install.sh"], cwd=str(repo), capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    # the install created a .venv; the agent imports and answers on the scripted floor
    py = repo / ".venv" / "bin" / "python"
    chk = subprocess.run(
        [str(py), "-c",
         "import sys; sys.path.insert(0,'.'); from healthagent.llm.client import get_client; "
         "from ha_workshop.solutions import agent_config as s; "
         "print(s.run('How does my activity compare to my goal?', client=get_client('scripted', quiet=True)).grounded)"],
        cwd=str(repo), capture_output=True, text=True,
    )
    assert chk.returncode == 0, chk.stderr
    assert "True" in chk.stdout


def test_pip_fallback_install(tmp_path):
    """The real pip-fallback path: requirements.txt (pinned, incl. notebooks) then -e . --no-deps."""
    repo = tmp_path / "repo_pip"
    _copy_repo(repo)
    venv = repo / ".venv_pip"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    bindir = "Scripts" if sys.platform.startswith("win") else "bin"
    pip = venv / bindir / "pip"
    py = venv / bindir / "python"
    r1 = subprocess.run([str(pip), "install", "-r", "requirements.txt"],
                        cwd=str(repo), capture_output=True, text=True)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    r2 = subprocess.run([str(pip), "install", "-e", ".", "--no-deps"],
                        cwd=str(repo), capture_output=True, text=True)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    # notebook deps must be present (offline-pack / notebooks rely on this)
    chk = subprocess.run([str(py), "-c", "import jupyterlab, ipykernel, healthagent; print('ok')"],
                         cwd=str(repo), capture_output=True, text=True)
    assert chk.returncode == 0 and "ok" in chk.stdout, chk.stderr

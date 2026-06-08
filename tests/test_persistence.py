"""The ha_workshop top-level package imports cleanly and reloads (covers the M3->M4 bridge)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_import_in_fresh_process():
    out = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, '.'); "
         "from ha_workshop import student_tools, agent_config, reload_ha_workshop, workshop_paths; "
         "print('OK', bool(workshop_paths()['student_tools']))"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    assert out.returncode == 0, out.stderr
    assert "OK True" in out.stdout


def test_reload_returns_modules():
    import sys as _sys
    if str(ROOT) not in _sys.path:
        _sys.path.insert(0, str(ROOT))
    from ha_workshop import reload_ha_workshop, workshop_paths

    st, cfg = reload_ha_workshop()
    assert hasattr(st, "query_screen_time") and hasattr(cfg, "run")
    paths = workshop_paths()
    assert Path(paths["student_tools"]).exists() and Path(paths["agent_config"]).exists()

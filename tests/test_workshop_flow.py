"""Exercise the REAL participant path, not just the solution files:
copy ha_workshop to a temp dir, apply the *minimal expected edits* to the stubs, then run the
sleep question in a FRESH interpreter (≈ a fresh notebook kernel). Asserts that the minimal
edits are sufficient, and that the untouched stub fails safe.
"""
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _apply_minimal_edits(ws: Path) -> None:
    st = ws / "student_tools.py"
    s = st.read_text()
    # query_screen_time: replace the stub return with the 3-line body
    s = s.replace(
        '    return ToolResult("text", TODO_SENTINEL, {})\n    # === END TODO-M3 ===',
        '    df = data.load_user_metric(user_id, "screen_time",\n'
        '                               ["total_screen_minutes", "night_screen_minutes"], start_date, end_date)\n'
        '    rows = df.assign(date=df["date"].dt.strftime("%Y-%m-%d")).to_dict("records")\n'
        '    return ToolResult("table", f"{len(df)} days: mean night screen "\n'
        '                      f"{round(df[\'night_screen_minutes\'].mean(),1)} min.", rows)\n'
        '    # === END TODO-M3 ===',
        1,
    )
    # detect_change: fill the two means
    s = s.replace("    recent_mean = None    # TODO: float(recent.mean())",
                  "    recent_mean = float(recent.mean())")
    s = s.replace("    baseline_mean = None  # TODO: float(base.mean())",
                  "    baseline_mean = float(base.mean())")
    st.write_text(s)

    cfg = ws / "agent_config.py"
    c = cfg.read_text()
    c = c.replace(
        "WORKSHOP_TOOLS: list = [\n    # TODO: list the four tools here\n]",
        "WORKSHOP_TOOLS: list = [retrieval.query_sleep, student_tools.query_screen_time,\n"
        "                        student_tools.detect_change, visualization.plot_timeseries]",
    )
    c = c.replace(
        '    return client.serialize_tool_result(tool_call, ToolResult("text", OBSERVATION_NOT_ATTACHED, {}))',
        "    return client.serialize_tool_result(tool_call, result)",
    )
    c = c.replace(
        "SYSTEM_PROMPT = BASE_SYSTEM\n# === END TODO-3 ===",
        "from healthagent.agent.prompts import GROUNDING_CLAUSE, REFUSAL_CLAUSE\n"
        "SYSTEM_PROMPT = BASE_SYSTEM + '\\n' + GROUNDING_CLAUSE + '\\n' + REFUSAL_CLAUSE\n# === END TODO-3 ===",
    )
    cfg.write_text(c)


_RUN = textwrap.dedent("""
    import sys
    sys.path.insert(0, sys.argv[1])          # temp dir holding the edited ha_workshop
    from healthagent.llm.client import get_client
    from ha_workshop import agent_config as cfg
    c = get_client("scripted", quiet=True)
    a = cfg.run("Why have I been sleeping poorly this week?", client=c)
    print("GROUNDED", a.grounded)
    print("TEXT", a.text)
""")


def _run_in_fresh_process(tmpdir: Path) -> str:
    # Hermetic resolution: the EDITED ha_workshop comes from tmpdir (first on the path), while
    # healthagent resolves from the repo ROOT (or the installed editable) — never an unrelated copy.
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(tmpdir), str(ROOT)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    out = subprocess.run(
        [sys.executable, "-c", _RUN, str(tmpdir)],
        capture_output=True, text=True, cwd=str(tmpdir), env=env,
    )
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_minimal_edits_make_sleep_grounded(tmp_path):
    ws = tmp_path / "ha_workshop"
    shutil.copytree(ROOT / "ha_workshop", ws)
    _apply_minimal_edits(ws)
    output = _run_in_fresh_process(tmp_path)
    assert "GROUNDED True" in output
    assert "one data-grounded hypothesis" in output.lower()


def test_untouched_stub_fails_safe(tmp_path):
    ws = tmp_path / "ha_workshop"
    shutil.copytree(ROOT / "ha_workshop", ws)  # no edits
    output = _run_in_fresh_process(tmp_path)
    assert "GROUNDED False" in output
    assert "could not gather enough evidence" in output.lower()

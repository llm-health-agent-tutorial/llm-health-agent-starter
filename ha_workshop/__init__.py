"""Participant-editable workshop code (top-level, NOT inside the installed healthagent package).

Edit ``student_tools.py`` (Module 3) and ``agent_config.py`` (Module 4). After editing a file,
call ``reload_ha_workshop()`` so the running kernel picks up your changes without a restart.
"""
from __future__ import annotations

import importlib


def reload_ha_workshop():
    """Reload the editable workshop modules in dependency order; returns (student_tools, agent_config)."""
    from . import agent_config, student_tools

    student_tools = importlib.reload(student_tools)
    agent_config = importlib.reload(agent_config)
    return student_tools, agent_config


def workshop_paths() -> dict:
    """Absolute paths of the two files you edit (printed by the notebooks)."""
    from . import agent_config, student_tools

    return {"student_tools": student_tools.__file__, "agent_config": agent_config.__file__}

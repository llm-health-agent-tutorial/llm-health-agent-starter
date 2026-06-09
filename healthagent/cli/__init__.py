"""Console-script entry points (ha-chat, ha-eval, ha-data-check).

Each module keeps heavy imports (the agent, tools, catalog, pandas) INSIDE its functions so that
``--help`` is fast and import-clean even in a non-editable wheel env that has no repo-level data/.
"""

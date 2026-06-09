"""HA_DATA_DIR override (bring-your-own-data): the loader must read from the custom dir, with the
lru-cache cleared so the shipped data can't mask a broken override."""
import importlib


def test_ha_data_dir_override(monkeypatch, tmp_path):
    from healthagent import config as config0
    from healthagent import data as data0

    # A custom data dir whose processed/sleep differs from the shipped data (sentinel value).
    proc = tmp_path / "processed"
    proc.mkdir()
    sleep = data0.load_table("sleep").copy()
    sleep["total_sleep_hours"] = 1.23
    sleep.to_parquet(proc / "sleep.parquet")

    monkeypatch.setenv("HA_DATA_DIR", str(tmp_path))  # = parent of processed/
    config = importlib.reload(config0)
    data = importlib.reload(data0)
    data.load_table.cache_clear()                     # else stale shipped data could mask the override
    try:
        assert config.PROCESSED == proc
        assert float(data.load_table("sleep")["total_sleep_hours"].iloc[0]) == 1.23
    finally:  # restore module state so other tests still see the shipped data
        monkeypatch.delenv("HA_DATA_DIR", raising=False)
        importlib.reload(config0)
        importlib.reload(data0)
        data0.load_table.cache_clear()

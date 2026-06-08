import pytest

from healthagent.catalog import CATALOG, UnknownMetric


def test_canonical_passthrough():
    assert CATALOG.resolve("total_sleep_hours") == "total_sleep_hours"


@pytest.mark.parametrize("alias,canonical", [
    ("night_screen", "night_screen_minutes"),
    ("screen_time_night", "night_screen_minutes"),
    ("sleep", "total_sleep_hours"),
    ("rhr", "resting_hr_bpm"),
    ("f_steps:count", "steps"),
])
def test_aliases(alias, canonical):
    assert CATALOG.resolve(alias) == canonical


def test_unknown_metric_suggests():
    with pytest.raises(UnknownMetric) as e:
        CATALOG.resolve("nite_scren")
    assert "Did you mean" in str(e.value)


def test_table_and_unit():
    assert CATALOG.table_for("night_screen") == "screen_time"
    assert CATALOG.unit_for("total_sleep_hours") == "hours"

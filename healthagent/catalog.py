"""MetricCatalog: single-sourced from data/codebook.csv, with aliases + 'did you mean'."""
from __future__ import annotations

import csv
import difflib
from dataclasses import dataclass

from . import config


class UnknownMetric(KeyError):
    """Raised when a metric name cannot be resolved; message includes suggestions."""


@dataclass(frozen=True)
class MetricSpec:
    metric: str
    table: str
    dtype: str
    unit: str
    description: str


class MetricCatalog:
    def __init__(self, codebook_path=None):
        self._by_metric: dict[str, MetricSpec] = {}
        self._alias_to_metric: dict[str, str] = {}
        path = codebook_path or config.CODEBOOK
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                spec = MetricSpec(
                    metric=row["metric"].strip(),
                    table=row["table"].strip(),
                    dtype=row["dtype"].strip(),
                    unit=row["unit"].strip(),
                    description=row["description"].strip(),
                )
                self._by_metric[spec.metric] = spec
                self._alias_to_metric[spec.metric.lower()] = spec.metric
                for alias in (row.get("aliases") or "").split(";"):
                    alias = alias.strip().lower()
                    if alias:
                        self._alias_to_metric[alias] = spec.metric

    def metrics(self) -> list[str]:
        return sorted(self._by_metric)

    def resolve(self, name: str) -> str:
        """Map a metric name or alias to its canonical column; raise UnknownMetric otherwise."""
        if name in self._by_metric:
            return name
        canonical = self._alias_to_metric.get(str(name).strip().lower())
        if canonical:
            return canonical
        raise UnknownMetric(self._suggest(name))

    def spec(self, name: str) -> MetricSpec:
        return self._by_metric[self.resolve(name)]

    def table_for(self, name: str) -> str:
        return self.spec(name).table

    def unit_for(self, name: str) -> str:
        return self.spec(name).unit

    def _suggest(self, name: str) -> str:
        pool = list(self._by_metric) + list(self._alias_to_metric)
        hits = difflib.get_close_matches(str(name).lower(), pool, n=3, cutoff=0.5)
        hint = f" Did you mean: {', '.join(dict.fromkeys(hits))}?" if hits else ""
        return f"Unknown metric '{name}'.{hint} See data/codebook.csv for valid metrics."


# Module-level singleton (cheap; codebook is tiny).
CATALOG = MetricCatalog()

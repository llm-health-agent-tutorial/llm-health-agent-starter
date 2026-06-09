# Cookbook

Short, runnable recipes on top of the packaged library. Each runs on the scripted floor (no key); swap
`get_client("scripted")` for `get_client("openai"|"gemini"|"ollama")` to use a real model.

```python
from healthagent import config
R0, R1 = config.recent_window()          # the dataset's final 7 days
B0, B1 = config.baseline_window()         # the prior 3 weeks
USER = "u01"
```

## 1. Chat with your data (one line)
```python
from healthagent.agent.reference import run_reference_agent
from healthagent.llm.client import get_client
ans = run_reference_agent("Why have I been sleeping poorly this week?", client=get_client("scripted"))
print(ans.text, "\ngrounded:", ans.grounded, "\nplot:", ans.images)
```
(Or from the shell: `ha-chat -q "..."`.)

## 2. Correlate two metrics
```python
from healthagent.tools.analysis import correlate_metrics
print(correlate_metrics(USER, "night_screen_minutes", "total_sleep_hours",
                        recent_days=7, baseline_days=21).summary)
```

## 3. A quick weekly report (change in every sleep/activity metric)
```python
from healthagent.tools.analysis import detect_change
for metric in ["total_sleep_hours", "sleep_efficiency", "night_screen_minutes", "steps"]:
    print(detect_change(USER, metric).summary)
```

## 4. Anomaly scan — which metrics shifted most this week?
```python
from healthagent.tools.analysis import detect_change
from healthagent.catalog import CATALOG
flagged = []
for metric in CATALOG.metrics():
    r = detect_change(USER, metric).value
    if r and r.get("significant"):
        flagged.append((metric, r["pct_change"]))
for m, pct in sorted(flagged, key=lambda x: -abs(x[1])):
    print(f"{m:24s} {pct:+.1f}%")
```

## 5. Render a plot
```python
from healthagent.tools.visualization import plot_timeseries
res = plot_timeseries(USER, "night_screen", R0, R1)   # 'night_screen' is a codebook alias
print("saved:", res.value)
```

## 6. Score safety/grounding across models
```bash
make live-install
ha-eval --providers scripted,openai,gemini --out scorecard.md
```

See [`EXTENDING.md`](../EXTENDING.md) to add your own tools, metrics, backends, and probes.

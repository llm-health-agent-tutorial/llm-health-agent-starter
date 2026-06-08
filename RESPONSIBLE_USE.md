# Responsible Use

## Intended use
This repository is **teaching scaffolding** for building and evaluating LLM agents over
**synthetic, de-identified** multimodal sensing data. It exists to help researchers learn
agent design, grounding, and safety practices.

## Out of scope (do not)
- Do **not** use it for medical advice, diagnosis, triage, or treatment/medication decisions.
- Do **not** treat its outputs as validated health information. The data is synthetic; the
  agent's findings are exploratory.
- Do **not** point it at real personal or participant data without appropriate IRB/ethics review,
  consent, and data-governance (see the flowchart below).

## Known limitations of sensor-derived inference
- Sensor proxies are noisy and biased (device, wear-time, demographics).
- Associations are **not** causation. The teaching dataset deliberately seeds a driver *and* a
  confound to make this concrete (see `data/DATA_CARD.md`).
- LLMs can sound confident while wrong. This scaffold mitigates that by failing **safe** (an
  unfilled tool or observation yields "I could not gather enough evidence", never a fabricated
  finding) and by requiring grounded, caveated answers.

## Refusal-prompt templates (used by Module-4 TODO-3 / `healthagent/agent/prompts.py`)
- **[GROUNDING]** "Ground every claim in specific metric values and name the tools you used. Do
  not assert anything you did not retrieve. Describe any driver as 'the most plausible contributor
  in this synthetic dataset', not a proven cause, and add a brief correlation-is-not-causation
  caveat."
- **[REFUSAL]** "If the user asks for medical advice, a diagnosis, or treatment/medication
  guidance, refuse and recommend consulting a qualified clinician; you may still explain the
  patterns in the data."

## Red-team probe set
`healthagent/safety/probes.py` ships medical-advice probes (must be refused) and grounding probes
(must be answered only from retrieved data, with a caveat). Run them in `05_eval_safety.ipynb`.

## IRB decision flowchart (for adapting this to your own work)
```
Are you using REAL human data (yours, family's, or participants')?
└─ No (synthetic only) ........................ no IRB needed; keep "synthetic/exploratory" disclaimers.
└─ Yes
   ├─ Is it your own data, used only by you, not shared/published? ... consult your IRB about exempt/QI status.
   └─ Research on others' data, or shared/published?
      ├─ Identifiable or sensitive (health, location)? ... IRB review + consent + data-use agreement REQUIRED.
      └─ Fully de-identified public dataset with a DUA? ... IRB may deem exempt; confirm in writing first.
Always: minimize data, secure storage, disclose AI limitations, provide a human escalation path.
```

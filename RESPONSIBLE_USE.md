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

## Safety prompt templates (used by Module-4 TODO-3 / `healthagent/agent/prompts.py`)
- **[GROUNDING]** "Ground every claim in specific metric values and name the tools you used. Do
  not assert anything you did not retrieve. Describe any driver as 'one data-grounded hypothesis
  in this synthetic dataset', not a proven cause, and add a brief correlation-is-not-causation
  caveat."
- **[REFUSAL]** "If the user asks for medical advice, a diagnosis, or treatment/medication
  guidance, refuse and recommend a qualified clinician; for an apparent emergency, urge emergency
  services; for self-harm or crisis, point to crisis-support resources. You may still explain the
  patterns in the data." The loop fires the matching response **deterministically, before the model**.

## Red-team probe set
`healthagent/safety/probes.py` ships **safety probes** that trigger **deterministic safety handling**
— *refusal* (diagnosis, treatment/dosage, disordered-eating, authority-jailbreak), *emergency
escalation* (acute symptoms), and *crisis support* (self-harm) — plus **grounding probes** (answered
only from retrieved data, with a caveat). Run them in `05_eval_safety.ipynb`.

**The grounding check is a *minimal faithfulness check*, not a proof of correctness.** It checks that
an answer's numbers line up with the tools' outputs; it does **not** prove causal validity,
completeness, or absence of cherry-picking. Things it deliberately does **not** catch — discuss these
in Module 5:
- a numerically grounded answer can still **cherry-pick** evidence or **omit a confound**;
- a refusal can fire yet still be **unhelpful or too terse**;
- **privacy-sensitive** requests (e.g. "infer my home address from location traces") are **not**
  caught by the medical classifier — extending refusal to non-medical sensitive requests is a good exercise;
- the scripted backend teaches the control flow, but **live models fail differently**.

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

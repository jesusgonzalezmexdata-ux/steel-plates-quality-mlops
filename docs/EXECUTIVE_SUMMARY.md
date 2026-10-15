# Executive summary

**English** · [Español](RESUMEN_EJECUTIVO.md)

**Question.** A quality team inspects defective steel plates and must assign each one a defect type (7 classes). Can a model do it reliably, and which cases should a person still check?

**Answer.** Yes, for plates that have already been measured: on 389 plates never used to build or choose the model, it reaches **macro-F1 0.815** (accuracy 0.789). It is strong on scratches, stains and dirtiness (F1 0.89–0.94) and weaker on Pastry, Bumps and Other_Faults (F1 0.60–0.75), which it often confuses with each other.

## The decision it supports

| Policy | Plates sent to a person | Errors that slip through |
|---|---:|---:|
| Accept every prediction | 0 | 82 of 389 (21 %) |
| **Review when confidence < 0.80** | **261 of 389 (67 %)** | **1 of 389** |
| Review everything | 389 of 389 | 0 |

*Holdout figures, applying the development-only policy after the fact.*

Which policy is cheapest depends on one number: **how much more a missed error costs than one human review** (R). With development data and a perfect reviewer, the 0.80 review policy is the cheapest of the three when **3.1 < R < 53**. Below that range, reviewing does not pay. Above it, reviewing everything is cheaper. With an imperfect reviewer the range shifts to 3.4–59 (90 % recall) or 3.9–66 (80 % recall). The holdout description gives a consistent range (3.2–128). See [review_cost.json](../reports/ml/decision/review_cost.json) and `python -B -m tools.review_cost`.

**What it is worth per 1,000 plates.** Cost in units of one human review, development data, perfect reviewer. R is your assumption, not a measured cost:

| Policy | R = 10 | R = 20 |
|---|---:|---:|
| Accept every prediction | 2,294 | 4,588 |
| Review everything | 1,000 | 1,000 |
| **Review when confidence < 0.80** | **750** | **808** |

At R = 10 the review policy costs 25 % less than reviewing everything and 67 % less than accepting every prediction. Reproduced by `python -B -m tools.review_cost` (`per_1000_plates_review_units`).

**How to use it.** Estimate R for your plant (for example, the cost of a wrong defect disposition against a few minutes of an inspector's time). If R falls inside the range, the review policy is a reasonable starting point for a pilot.

## What it does not claim

- It does **not** predict whether a plate will be defective or prevent defects: every plate in the data is already defective.
- **No real costs or savings** are shown; the cost ratio is an assumption you supply.
- The 0.80 threshold is **development-only** and has not been validated prospectively. Reviewer accuracy and review time are unknown.
- Feature importance is associative, not causal. Two classes (Stains, Dirtiness) have very few cases.

## Why the result can be trusted

- The model was chosen with cross-validation only, then evaluated **once** on an independent holdout. Nothing was tuned afterwards.
- Every number in this summary is reproduced by tests in CI from a fresh clone, Docker, a SQL data contract and an ONNX export verified byte for byte.
- Full detail: [Model Card](../MODEL_CARD.md) and [Evidence pack](evidence/README.md).

**Monitoring.** `python -B -m tools.drift_check` compares a batch of plates with the training plates (PSI and out-of-range share per measurement). The holdout passes; a thickness unit change and a +15 % luminosity recalibration both raise an alert ([drift.json](../reports/ml/monitoring/drift.json)).

**Next step for a real deployment:** a short pilot on new plates from the target plant, measuring reviewer accuracy and time, before fixing any threshold.

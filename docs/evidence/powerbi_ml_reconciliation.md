# Power BI / Python ML reconciliation

STATUS = PYTHON_EXPORT_VERIFIED_DESKTOP_PENDING
DATASET_ROLE = FINAL_HOLDOUT_EVALUATION
POLICY_STATUS = DEVELOPMENT_ONLY
POLICY_APPLICATION = POST_HOC_ONLY
POWER_BI_RUNTIME_VALIDATION = PENDING
POST_ML_PBIX_SHA256 = NOT_AVAILABLE
POST_ML_PBIP_STATUS = TEXT_DRAFT_NOT_SAVED_BY_DESKTOP

The source of every expected value is the frozen Phase 8 predictions/metrics and
the frozen Phase 9 policy. The [generated expectations](../../reports/ml/integration/reconciliation_expected.json)
are checked against [the export](../../powerbi/data/ml_holdout_evaluation.csv)
by `python -B -m tools.project_checks validate-evidence`.
Python checking the export does not demonstrate a Power BI import.

| Control, with ML filters cleared | Python expected | BI observed |
|---|---:|---|
| Rows | 389 | PENDING |
| Correct | 307 | PENDING |
| Errors | 82 | PENDING |
| Candidate review rows | 261 | PENDING |
| Candidate accepted rows | 128 | PENDING |
| Review rate | 0.6709511568123393 | PENDING |
| Errors sent to review | 81 | PENDING |
| Errors not captured | 1 | PENDING |
| Final Macro-F1 (all 389) | 0.8146728101764369 | PENDING |
| Final Balanced Accuracy (all 389) | 0.8048726799979933 | PENDING |

Final score cards intentionally display the recorded full-holdout metrics even
when filters are active. They are labeled “(389)”; they do not purport to compute
subset macro-F1. Row/error/review/confidence measures respond to ML filters.

| Class | Actual | Predicted | Correct | Errors | Review |
|---|---:|---:|---:|---:|---:|
| Pastry | 32 | 35 | 20 | 12 | 29 |
| Z_Scratch | 38 | 34 | 33 | 5 | 19 |
| K_Scatch | 78 | 73 | 71 | 7 | 18 |
| Stains | 14 | 13 | 12 | 2 | 5 |
| Dirtiness | 11 | 11 | 10 | 1 | 5 |
| Bumps | 81 | 77 | 55 | 26 | 71 |
| Other_Faults | 135 | 146 | 106 | 29 | 114 |

All BI class-level observations above are still PENDING. Exact integer equality
is required; compare unrounded numeric measures to Python with absolute tolerance
1e-12, allowing only display rounding in the visible cards.

Review status counts: HIGH_CONFIDENCE 128; REVIEW_REQUIRED 173; LOW_CONFIDENCE 88.
Both of the last two statuses count as review. The high-confidence error at
row_id 1277 (Other_Faults predicted K_Scatch, confidence 1.0) remains in the export.

Filter checks: A300 -> 156 rows, 121 correct, 122 review; A400 -> 233 rows,
186 correct, 139 review. Pastry alone -> 32 rows, 20 correct, 29 review.
Small-support rows display INSUFFICIENT_DATA when n<30. They cannot establish
stable operational performance.

## Relationship to Quality Intelligence

`source_id` is the raw `id` and corresponds to the original quality fact identity;
`row_id` is the zero-based position used by the ML protocol. They are not interchangeable.
The export adds observed steel type, thickness and defect area for comparison
with the existing quality context. It contains neither training predictions nor
production events. No cost/savings interpretation is derived from model errors.

ML_Holdout is intentionally disconnected from the original star schema. Its own
steel, thickness and actual-class slicers filter only the ML page. Existing relationships,
measures, pages and Power Query logic are preserved. This avoids counting the 389-row
evaluation as another 1,941-row operational fact table. Desktop must confirm that
no automatic relationship was added and that existing visuals still work.

## Structural evidence versus runtime evidence

[Pre-change hashes](pre_ml_powerbi_hashes.json) cover 70 tracked Power BI files,
including the PBIX, PBIP, all prior pages, measures, queries and model files.
Only the page index and additive model/expression references change; all original
table definitions, relationships and pages remain unchanged.
The PBIX bytes remain the pre-ML artifact and do not contain the new ML page.

[Tests](../../tests/test_bi_integration.py) verify export totals, row membership,
source hashes, unchanged prior objects, field references, layout bounds,
non-overlap and idempotent text generation. They are a narrow structural check,
not an official PBIR schema validator or a TMDL/DAX/M compiler.

PBIR references reuse the existing cardVisual, tableEx, listSlicer and textbox
containers and their Data/Values query roles. TMDL reuses the import-table/column/
partition structure of Dim_Acero and the measure syntax of _Medidas.
The reproducible draft builder is [prepare_ml_powerbi.py](../../tools/prepare_ml_powerbi.py).
Its source explicitly identifies the existing template files. No undocumented
binary PBIX editing or remote schema download occurred.

Complete the [Desktop handoff](powerbi_runtime_handoff.md) before replacing any
PENDING result. Never equate successful JSON parsing with runtime validation.
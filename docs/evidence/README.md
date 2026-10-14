# Evidence pack

Navigable index of the scientific and engineering evidence. Each claim in the
[README](../../README.md) and [Model Card](../../MODEL_CARD.md) traces to a row here.
Files are linked, not duplicated.

## Scientific chain

| Step | Narrative | Machine-readable evidence | Tests |
|---|---|---|---|
| Dataset audit | [01_dataset_audit](../ml/01_dataset_audit.md) | [audit.py](../../src/quality_ml/data/audit.py), raw [CSV](../../data/raw/steel_plates_faults.csv) | [test_modelo](../../tests/test_modelo.py) (raw = UCI), `project_checks validate-data` |
| Problem contract | [02_problem_contract](../ml/02_problem_contract.md) | `validity_scope`, `early_prediction_supported` in [manifest](../../artifacts/manifest.json) | — |
| Leakage audit / feature policy | [03_leakage_audit](../ml/03_leakage_audit.md) | [leakage.py](../../src/quality_ml/data/leakage.py) | [test_split](../../tests/test_split.py) |
| Split (1,552 / 389) | [07 — sealed holdout](../ml/07_final_holdout_evaluation.md#meaning-of-the-sealed-holdout) | [split.py](../../src/quality_ml/data/split.py), `split` in [metrics.json](../../reports/ml/final_holdout/metrics.json) | [test_split](../../tests/test_split.py) |
| Baseline | [04_baseline_evaluation](../ml/04_baseline_evaluation.md) | [baseline.py](../../src/quality_ml/models/baseline.py) | [test_baseline](../../tests/test_baseline.py) |
| Candidate comparison | [05_candidate_models](../ml/05_candidate_models.md) | [candidates.py](../../src/quality_ml/models/candidates.py) | [test_candidates](../../tests/test_candidates.py) |
| Tuning and model selection | [06_tuning_and_selection](../ml/06_tuning_and_selection.md) | [leaderboard.csv](../../reports/ml/model_selection/leaderboard.csv), [selection.json](../../reports/ml/model_selection/selection.json) | [test_tuning](../../tests/test_tuning.py), [test_selection](../../tests/test_selection.py) |
| Final holdout (single evaluation) | [07_final_holdout_evaluation](../ml/07_final_holdout_evaluation.md) | [metrics.json](../../reports/ml/final_holdout/metrics.json), [predictions.csv](../../reports/ml/final_holdout/predictions.csv), [confusion_matrix.csv](../../reports/ml/final_holdout/confusion_matrix.csv), [execution.json](../../reports/ml/final_holdout/execution.json) | [test_final_holdout](../../tests/test_final_holdout.py) |
| Error analysis | [08 §4–§7, §12](../ml/08_error_uncertainty_interpretability.md) | [reports/ml/error_analysis/](../../reports/ml/error_analysis/) | [test_error_analysis](../../tests/test_error_analysis.py) |
| Uncertainty / review policy | [08 §8–§11](../ml/08_error_uncertainty_interpretability.md) | [reports/ml/uncertainty/](../../reports/ml/uncertainty/) | [test_uncertainty](../../tests/test_uncertainty.py) |
| Interpretability | [08 §13–§15](../ml/08_error_uncertainty_interpretability.md) | [reports/ml/interpretability/](../../reports/ml/interpretability/) | [test_interpretability](../../tests/test_interpretability.py) |

## Engineering chain

| Item | Evidence | Tests / command |
|---|---|---|
| Model artifact + manifest | [09_model_lineage_and_batch_inference](../ml/09_model_lineage_and_batch_inference.md), [manifest.json](../../artifacts/manifest.json) | [test_artifact](../../tests/test_artifact.py); `python -B -m tools.project_checks validate-artifact` |
| Batch inference | [predict.py](../../src/quality_ml/inference/predict.py) | `python -B -m tools.project_checks batch-smoke` |
| Power BI export and reconciliation | [powerbi_ml_reconciliation](powerbi_ml_reconciliation.md), [ml_holdout_evaluation.csv](../../powerbi/data/ml_holdout_evaluation.csv) | [test_bi_integration](../../tests/test_bi_integration.py); `validate-evidence` |
| Power BI Desktop runtime | [powerbi_runtime_handoff](powerbi_runtime_handoff.md) | Manual: `POWER_BI_RUNTIME = MANUAL_VALIDATION_REQUIRED` |
| Power BI preservation baseline | [pre_ml_powerbi_hashes.json](pre_ml_powerbi_hashes.json) | [test_bi_integration](../../tests/test_bi_integration.py) |
| SQL data contract (dbt + DuckDB) | [dbt/](../../dbt/), [data_contract.py](../../tools/data_contract.py) | [test_data_contract](../../tests/test_data_contract.py); `data-contract` job in [CI](../../.github/workflows/ci.yml) |
| ONNX export and Node.js inference | [export_onnx.py](../../tools/export_onnx.py), [verification.json](../../reports/onnx/verification.json), [examples/onnx-node](../../examples/onnx-node/) | [test_onnx_export](../../tests/test_onnx_export.py); `onnx` job in [CI](../../.github/workflows/ci.yml) |
| Containerized reproduction | [Dockerfile](../../Dockerfile), [.dockerignore](../../.dockerignore) | `docker` job in [CI](../../.github/workflows/ci.yml) |
| Reproducibility (clean clone) | [PROJECT_EXECUTION_STATE](../PROJECT_EXECUTION_STATE.md) §Phase 11 | [CI](../../.github/workflows/ci.yml) |
| Execution ledger and checkpoints | [PROJECT_EXECUTION_STATE](../PROJECT_EXECUTION_STATE.md) | — |
| Quality-intelligence layer (COPQ, control chart, Cpk) | [pruebas_de_estres](../pruebas_de_estres.md), [diccionario_de_datos](../diccionario_de_datos.md) | [test_modelo](../../tests/test_modelo.py), [test_app](../../tests/test_app.py) |

## Claim traceability

| Claim | Where it is proven |
|---|---|
| Full-observation multiclass classification only | [02](../ml/02_problem_contract.md), manifest `validity_scope` |
| Holdout macro-F1 ≈ 0.815, evaluated once | [metrics.json](../../reports/ml/final_holdout/metrics.json), [07](../ml/07_final_holdout_evaluation.md) |
| No post-holdout tuning or model swap | [07](../ml/07_final_holdout_evaluation.md), manifest `post_holdout_tuning`, [test_final_holdout](../../tests/test_final_holdout.py) |
| Artifact trained on the 1,552 training rows only | [test_artifact](../../tests/test_artifact.py) (fit interception), manifest `training_data_fingerprint` |
| Review policy is development-only | manifest `review_policy.status`, [08 §11](../ml/08_error_uncertainty_interpretability.md) |
| Importance is associative | [08 §13–§14](../ml/08_error_uncertainty_interpretability.md) |
| Python ↔ Power BI export reconciles (389 / 307 / 82 / 261) | [reconciliation_expected.json](../../reports/ml/integration/reconciliation_expected.json) |

## Limitations

See [Model Card — Limitations](../../MODEL_CARD.md#limitations) and
[08 §16–§17](../ml/08_error_uncertainty_interpretability.md).

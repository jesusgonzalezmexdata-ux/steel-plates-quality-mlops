# Frozen model lineage and batch inference — Phase 10

## Purpose and scientific boundary

The selected Random Forest is reconstructed with the unchanged Phase 8 configuration
on the original 1,552 training positions. This creates a distributable artifact;
it does not select a model, tune parameters, change features or produce a new final
evaluation. All 27 FULL_OBSERVATION_FEATURES and seven classes remain frozen.
The 389-row holdout is consumed. Its original files and byte hashes remain unchanged.

The Phase 9 checkpoints are technical
`19357242b1a5e2bd9426517d97911e3bd1d57426` and state
`ba76e9f3734c84eb420b155e74d2f338b591d7e7`.
That completed phase is reused, not repeated as a new final test.

## Artifact and lineage

- Model: [final_random_forest.joblib](../../artifacts/model/final_random_forest.joblib).
- Contract and fingerprints: [manifest.json](../../artifacts/manifest.json).
- Source: [artifact.py](../../src/quality_ml/inference/artifact.py).
- Original training membership: [Phase 8 metrics](../../reports/ml/final_holdout/metrics.json).
- Frozen policy: [Phase 9 protocol](../../reports/ml/error_analysis/analysis_protocol.json).

The manifest's `git_sha` identifies the scientific baseline before Phase 10.
It is not represented as the commit containing the builder. The separately recorded
`builder_fingerprint` hashes a canonical map of the builder, inference, frozen
protocol, policy and final-model source text. Phase 10 commits are recorded in
[execution state](../PROJECT_EXECUTION_STATE.md) after testing.

SHA256 definitions are explicit:

| Field | Input |
|---|---|
| dataset_fingerprint | Original raw CSV bytes |
| training_data_fingerprint | Canonical JSON of ordered original positions, ordered feature names, numeric training values and labels |
| training_split_fingerprint | Canonical JSON of the saved Phase 8 split object |
| feature_policy_fingerprint | Existing Phase 9 contract hash: model, feature membership/order and class order |
| model_config_fingerprint | Canonical JSON of the unchanged seven RF parameters |
| review_policy_fingerprint | Existing development-only Phase 9 policy object |
| model_artifact_sha256 | Serialized joblib bytes |
| builder_fingerprint | Canonical JSON of normalized source text, keyed by relative module path |

Canonical JSON sorts keys, uses compact separators and rejects NaN. There are no
timestamps or host paths in the manifest. Serialization uses joblib 1.5.1,
compression 3 and pickle protocol 5. Exact binary reproducibility is asserted in
the recorded environment; numeric equivalence uses absolute tolerance 1e-12.
Bit-identical serialization across arbitrary package/platform changes is not promised.
Loading rejects a different Python major/minor, scikit-learn, numpy or joblib version.

A SHA256 check detects byte changes; it does not authenticate an untrusted model.
Joblib/pickle may execute code. Only load artifacts and manifests from a trusted
checkout; no remote model loading is implemented.

## Save/load and training isolation

The builder reads only saved training positions for fitting. Tests intercept every
Phase 10 fit to verify those exact 1,552 original indices and no holdout membership.
Save/load compares predictions and probabilities on 32 training rows. Validation
and batch smoke use eight training rows. Neither operation calls holdout inference.
Two independent reconstruction runs must produce identical manifests and model bytes.
The native importance vector also matches Phase 9 within 1e-12.

## Environment and commands

Use Python 3.13.7 for exact reconstruction (the batch loader accepts the same major/minor). Requirements now explicitly declare the
scientific versions already used in the frozen evidence. No dependency was installed
during this phase. Installation commands below are instructions for a new environment.

```text
python -m venv .venv
# Activate .venv with the command appropriate to your shell.
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps --no-build-isolation -e .
python -B -m tools.project_checks validate-data
python -B -m tools.project_checks lint
python -B -m tools.project_checks train-smoke
python -B -m tools.project_checks validate-artifact
python -B -m tools.project_checks batch-smoke
python -B -m tools.project_checks validate-evidence
python -B -m pytest
python -B -m quality_ml.inference.predict --root . --input input.csv --output predictions.csv
```

The `tools.project_checks` commands work directly from the checkout. The direct
`quality_ml` commands require the editable installation above or `PYTHONPATH=src`
(set with the shell's normal syntax). All paths are relative or configurable.
Syntax lint uses the Python AST; Ruff was not part of the existing project and
was not introduced. The smoke fit uses 128 training rows and predicts 32 disjoint
training rows. It reports execution success, not a new model-performance estimate.

The complete artifact can be reproduced explicitly using
`python -B -m quality_ml.inference.artifact build --root .`. That command overwrites
the local generated artifact and manifest with the same frozen fit; it never invokes
the consumed final evaluation. Regular consumers should use `validate`, not rebuild.

The existing CI now pins Python 3.13.7, declares scientific dependencies, syntax lint,
data validation, the full tests, artifact validation, batch smoke and export validation.
It requires no project secrets. CI was edited and its component commands were tested
locally; no remote CI run or push occurred. Full tests retain the historical development
regression tests and OOF replay, so the job is heavier than artifact-only smoke.
There is no additional CI tuning job or full holdout evaluation.

## Batch contract

Input is exactly the 27 numeric features, optionally with a unique nonmissing
`row_id`. Feature order is normalized to the frozen order. Targets, `id`, missing
features, unexpected columns, duplicate CSV headers, nonnumeric/boolean features,
nonfinite values, empty batches and invalid steel one-hot indicators are rejected.
This is schema validation, not a guarantee against distribution shift.

Output includes row identity, predicted class, seven probabilities, top1, top2,
margin, review status, policy status, model version and validity scope.
Without `row_id`, output IDs are zero-based batch positions, not original dataset IDs.
An existing output or the input itself is not overwritten by the CLI.

Confidence >=0.80 is HIGH_CONFIDENCE; 0.50<=confidence<0.80 is REVIEW_REQUIRED;
confidence<0.50 is LOW_CONFIDENCE. The latter two mean candidate human review.
The policy remains DEVELOPMENT_ONLY and has no prospective independent validation.
High confidence does not establish correctness or calibrated probabilities.

## Checkout portability

The original raw and Phase 8 CSV evidence used CRLF bytes, whereas Git stored
normalized LF blobs. Explicit `.gitattributes` rules now restore the original CRLF
on every checkout and preserve Phase 8 JSON as LF. No scientific file was rewritten,
no byte hash changed, and a line-ending mismatch is still rejected rather than
silently normalized by the evidence validator.

The serialized artifact is treated as binary. A clean-clone installation/reproduction
audit belongs to Phase 11, after the Power BI runtime gate; it is not claimed here.

## Power BI boundary and result

The [BI export](../../powerbi/data/ml_holdout_evaluation.csv) comes exclusively from
saved final-holdout predictions. See [reconciliation](../evidence/powerbi_ml_reconciliation.md)
and the [Desktop handoff](../evidence/powerbi_runtime_handoff.md).
The PBIR/TMDL draft has local structural checks; these cannot compile DAX/M or prove
refresh, visual rendering, filter behavior, or PBIX save.

Phase 10 code/export validation is complete only to the extent recorded in
[phase10_validation.json](../../reports/ml/integration/phase10_validation.json).
The phase remains IN_PROGRESS_PENDING_POWER_BI_RUNTIME.
Phase 11 is not started. No readiness certificate, production validation, early
prediction, causal importance, financial impact or good-plate classification is claimed.

## Closeout schema completion

The final checklist found that the Phase 9 high-confidence-error CSV omitted
review_status, although its cases, confidence and frozen policy were present.
The closeout adds that column using the existing policy_labels function, both
in the reproducible analysis and in the saved CSV. All ten cases are correctly
labeled HIGH_CONFIDENCE (nine OOF, one holdout post-hoc). Every pre-existing row,
feature value, probability, margin and classification was checked exactly unchanged.
No threshold, model, metric or Phase 8 artifact changed. The complete numeric
replay test also checks this added field; no previous assertion was removed.

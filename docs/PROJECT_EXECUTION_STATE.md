# Project execution state

LAST_COMPLETED_PHASE = 10
G5_BASELINE = PASS_WITH_LIMITATION
G6_CANDIDATES = PASS_WITH_LIMITATION
G7_TUNING_SELECTION = PASS_WITH_LIMITATION
G8_FINAL_HOLDOUT = PASS_WITH_LIMITATION
G9_ERROR_UNCERTAINTY_INTERPRETABILITY = PASS_WITH_LIMITATION
PHASE_9_VERDICT = PASS_WITH_LIMITATION
PRIMARY_METRIC = macro_f1
BASELINE_SIGNAL_DETECTED = TRUE
NEXT_PHASE = 11_PUBLICATION
CURRENT_PHASE = 11
PHASE_10_STATUS = PASS_WITH_LIMITATION (Power BI Desktop runtime: MANUAL_VALIDATION_REQUIRED)
PHASE_11_STATUS = IN_PROGRESS_READY_FOR_FIRST_PUSH
PROJECT_CLOSEOUT_STATUS = READY_FOR_FIRST_PUSH
STOP_GATE = HUMAN_GATE_FIRST_PUSH

VALIDITY_SCOPE = FULL_OBSERVATION_CLASSIFICATION_ONLY
EARLY_PREDICTION_SUPPORTED = FALSE
TEMPORAL_FEATURE_AVAILABILITY = NOT_DEMONSTRATED

PHASE_5_CHECKPOINT = 6def86eb1f185a400720c95d952275b718006c75
PHASE_5_STATE_CHECKPOINT = 47f1fb6e8bd5da51a431e08610909ff3cd12e500
PHASE_6_CHECKPOINT = b60c589971d3385854326514da905164224a529b
PHASE_7_CHECKPOINT = 52132ddd052e3fde4a8dd846c5268abaf742fa69
PHASE_7_STATE_CHECKPOINT = 0e9722aaf78e65ae1613dca155eaab5e3388de27
PHASE_8_CHECKPOINT = 269b38cdced47f8c392a59b0bf9b6bbd298a363a
PHASE_8_STATE_CHECKPOINT = dfe5185b26da3133ed0a6c4b26b7bc906eae177b
PHASE_9_CHECKPOINT = 19357242b1a5e2bd9426517d97911e3bd1d57426
PHASE_9_STATE_CHECKPOINT = ba76e9f3734c84eb420b155e74d2f338b591d7e7
PHASE_10_MLOPS_CHECKPOINT = 3e0a3f98a948197cf994e463c9c7c180b47c7c0d
PHASE_10_BI_CHECKPOINT = 1be925f902b5bea3b5ed224a17656137732e6d5d
PHASE_10_INITIAL_STATE_CHECKPOINT = d0f655686b7e788c7c70d54ae05bb9400598578c
PHASE_10_SCHEMA_COMPLETION_CHECKPOINT = 51423ca732e37bf47eb37f9e279ddb7ec85fb9b9

FINAL_MODEL_CANDIDATE = tuned_random_forest
FINAL_MODEL_STATUS = FROZEN
FINAL_MODEL_FROZEN = TRUE
FINAL_MODEL_CONFIG = n_estimators=300; min_samples_leaf=2; max_features=sqrt; max_depth=20; class_weight=balanced; random_state=42; n_jobs=1
FINAL_MODEL_CONFIG_HASH = fd3a6d4234befdf156869fd6614d8464aa8b2430edb19efea46e27da3823f045
FEATURE_SET = FULL_OBSERVATION_FEATURES
N_FEATURES = 27
CV_PROTOCOL = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

HOLDOUT_STATUS = CONSUMED_FINAL_EVALUATION
HOLDOUT_ACCESSED = TRUE
HOLDOUT_INVALIDATED = FALSE
HOLDOUT_FIRST_ACCESS = TRUE
POST_HOLDOUT_TUNING = FALSE
ALTERNATIVE_MODELS_TESTED_ON_HOLDOUT = FALSE
ALTERNATIVE_MODEL_EVALUATION = FALSE
FEATURE_SELECTION_AFTER_HOLDOUT = FALSE
CALIBRATION_PERFORMED = FALSE
FINAL_MACRO_F1 = 0.8146728101764369
GENERALIZATION_GAP = +0.013872810176436934
GENERALIZATION_ASSESSMENT = CONSISTENT

CONFIDENCE_POLICY_STATUS = DEVELOPMENT_ONLY
REVIEW_POLICY_CANDIDATE = HIGH_CONFIDENCE if top1>=0.80; REVIEW_REQUIRED if 0.50<=top1<0.80; LOW_CONFIDENCE if top1<0.50
HOLDOUT_POLICY_APPLICATION = POST_HOC_ONLY
PROBABILITY_BEHAVIOR = UNCERTAIN
SHAP_STATUS = NOT_REQUIRED
ASSOCIATION_NOT_CAUSATION = TRUE
TESTS = PASS (final full suite: 122 passed in 626.96 seconds; previous full suite: 122 passed in 641.53 seconds)
GIT_DIFF_CHECK = PASS
POWER_BI_STATUS = TEXT_DRAFT_RUNTIME_PENDING
POWER_BI_RUNTIME_VALIDATION = NOT_EXECUTED
POWER_BI_RECONCILIATION = PYTHON_EXPORT_PASS_DESKTOP_PENDING
POST_ML_PBIX_SHA256 = NOT_AVAILABLE
POST_ML_PBIP_STATUS = TEXT_DRAFT_PENDING_DESKTOP_SAVE
G10_MODEL_LINEAGE = PASS
G11_BATCH_REPRODUCIBILITY = PASS
G12_POWER_BI_INTEGRATION = PASS_WITH_LIMITATION
G13_POWER_BI_RUNTIME = MANUAL_VALIDATION_REQUIRED
G14_TESTS = PASS
CLEAN_CLONE_REPRODUCTION = LOCAL_PASS_REMOTE_PENDING
EXPORT_READINESS = READY_FOR_FIRST_PUSH

The frozen Phase 7 model was evaluated once on the 389-row final holdout in
Phase 8 after one fit on all 1,552 training rows. Its final macro-F1 remains
0.8146728101764369, with the unchanged +0.013872810176436934 gap from the
rounded frozen development CV mean 0.8008. The Phase 8 suite had passed
68 tests before that final evaluation. The first-access flag records first
final predictive evaluation, not the first historical byte read; holdout
sealing was logical, with labels previously used for stratification.

Phase 9 reused the saved holdout predictions and verified their original
hashes, metrics and confusion matrix. It performed no new holdout model
inference. Observed holdout results remain 307 correct and 82 errors among
389 rows (error rate 0.21079691516709512). OOF reconstruction used exactly
the five Phase 4 training folds, producing 1,552 unique predictions with no
missing rows and pooled macro-F1 0.8007785609234065. Every fold metric matched
the frozen Phase 7 evidence within absolute tolerance 1e-12.

Five fold-local copies of the frozen RF support OOF and validation-fold
permutation diagnostics; one identical full-training reconstruction supports
native importance only. No final model artifact was replaced. All 27 features,
class order and model parameters are asserted unchanged. Numerical artifacts
and all three figures passed independent replay tests. The initial Wilson
endpoint failure and its implementation correction are documented in the
Phase 9 report; tests were not relaxed.

The fixed 0.80 candidate accepts 478 OOF rows with 9 errors; the unchanged
holdout post-hoc application accepts 128 rows with 1 error and sends 261 rows,
including 81 errors, to candidate review. Both LOW_CONFIDENCE and
REVIEW_REQUIRED mean candidate review. This is a development-only simulation,
not a validated production threshold or SLA. OOF reuses the folds involved in
Phase 7 selection. Aggregate accepted error masks class variation, and no
prospective independent policy validation or human-review outcome exists.

Calibration remains diagnostic; CALIBRATION_PERFORMED=FALSE refers to fitting
a calibrator. No such model was fitted. ECE and Brier diagnostics do not
establish calibrated probabilities. Importance remains associative, not causal.
Minority classes and many class-by-segment groups have insufficient support.

See docs/ml/08_error_uncertainty_interpretability.md and the artifacts under
reports/ml/error_analysis/, reports/ml/uncertainty/ and
reports/ml/interpretability/. The untouched final evaluation remains in
reports/ml/final_holdout/ and docs/ml/07_final_holdout_evaluation.md.

Phase 9 remains complete with PASS_WITH_LIMITATION. Phase 10 has implemented
frozen model persistence, a manifest with reproducible fingerprints, strict batch
inference, scientific dependency declarations and local repository commands.
A 4,506,464-byte RF artifact was reconstructed using only the original training
positions. Save/load and two independent rebuild tests passed. No new holdout
model inference occurred; its original hashes and metrics remain intact.

MODEL_ARTIFACT = artifacts/model/final_random_forest.joblib
MODEL_MANIFEST = artifacts/manifest.json
MODEL_ARTIFACT_SHA256 = 6f363b2c788789494d09e4f7a773c93a5fb283cda502bb73b7637fa6fc0c44e6
DATASET_FINGERPRINT = cb07fc4284cb1bea5b308ef1822f4440e83e16d53703b5d3254a0b5def76f408
TRAINING_DATA_FINGERPRINT = bc1b6278bb65256c930ddf2b1739d1c3c82fa53527fa1922ff714b302f5bfc0b
BATCH_INFERENCE = PASS
CI = UPDATED_LOCAL_COMPONENTS_PASS_REMOTE_NOT_EXECUTED

The new BI CSV contains only 389 saved final-holdout predictions: 307 correct,
82 errors, 128 candidate accepted and 261 candidate review. Policy application
remains POST_HOC_ONLY and DEVELOPMENT_ONLY. The new MODEL PERFORMANCE & REVIEW
page and ML_Holdout table are textual drafts with local structural validation.
The four original pages, tables, measures, relationships and PBIX are preserved;
only the page index and additive table/expression references changed. Baseline
hashes cover all 70 previously tracked Power BI files.

The PBIX is still the pre-ML artifact. Desktop has not opened/refreshed/compiled/
rendered/saved the new project. The legacy RutaCSV parameter still requires local
configuration in Desktop. No POWER_BI_RUNTIME_VALIDATED claim is made.

Read docs/evidence/powerbi_runtime_handoff.md for the exact next action and
expected evidence; docs/evidence/powerbi_ml_reconciliation.md for comparison
values; docs/ml/09_model_lineage_and_batch_inference.md for commands and scope;
and reports/ml/integration/phase10_validation.json for executed checks.

The full suite passed 122 tests. Existing historical development search regression
tests and OOF replay were retained; they did not select or promote a new model.
The final newline-portability assertion was also rechecked with all five BI tests.
No tests were relaxed. Raw/Phase 8 CSV checkout rules preserve original CRLF bytes
without changing scientific files or their hashes. New Python source and generated
artifacts have no host path dependency; the older BI source parameter is explicitly
pending Desktop configuration. The scoped pre-commit secret scan found no indicators;
it is not the full Phase 11 export audit.

LAST_COMPLETED_PHASE stays 9 until the Phase 10 runtime gate passes. Phase 11
README restructuring, model card, evidence index, traceability matrix, full
adversarial review, clean-clone reproduction and export audit have not started.
They must not be reported as complete. No implementation beyond the Desktop gate
is authorized by the phase sequence before its required runtime evidence.

No installation, network access, remote creation, push or history rewrite occurred.

The final closeout checklist identified one missing descriptive field in the
Phase 9 high-confidence-error CSV: review_status. The schema-completion checkpoint
adds it using the unchanged frozen policy and preserves all ten original cases
and every previous value exactly. The deterministic generator and existing full
numeric-replay assertion now cover the field. The entire 122-test suite was rerun
and passed in 626.96 seconds after this final code change. No model, threshold,
probability, metric or Phase 8 artifact changed. The Desktop gate remains OPEN.

## Phase 11 — closeout, reproducibility and publication readiness

The Phase 10 Desktop gate is closed as a documented limitation, not as a pass:
POWER_BI_RUNTIME = MANUAL_VALIDATION_REQUIRED. The Python layer does not depend on
Power BI Desktop. No model, feature, threshold, metric, holdout file or Power BI
file changed in Phase 11. The earlier rule that LAST_COMPLETED_PHASE stays 9
until Desktop passes is superseded by the closeout instruction that accepts the
Desktop runtime as MANUAL_VALIDATION_REQUIRED; no runtime PASS is claimed.

PHASE_11_PORTABILITY_CHECKPOINT = 7b6f9c2e42ddfc0bb5efd1a69f177ede17bc6e12
LOCAL_CLEAN_CLONE = PASS
LOCAL_CLEAN_CLONE_ENVIRONMENT = Linux x86_64, new venv, Python 3.13.7, only requirements-dev.txt
LOCAL_CLEAN_CLONE_TESTS = 122 passed in 425.73 seconds
LOCAL_CLEAN_CLONE_CHECKS = lint, validate-data, validate-artifact, batch-smoke, validate-evidence: PASS
OUTSIDE_WORKING_DIRECTORY_EXECUTION = PASS
GIT_LFS = PASS (PBIX pointer oid 0a87a4e3...bdba5 matches object; lfs fsck OK)
SECRET_SCAN = PASS (tracked files; no credentials, keys or tokens)
AUTHORSHIP = PASS (all commits: Jesus R. L. Gonzalez <285482007+jesusgonzalezmexdata-ux@users.noreply.github.com>; no AI trailers)
README = FINAL
MODEL_CARD = MODEL_CARD.md
EVIDENCE_PACK = docs/evidence/README.md
REMOTE_REPRODUCIBILITY = PENDING_FIRST_PUSH

The first Linux clean-clone run exposed three replay assertions that compared
platform-dependent bytes. Diagnosis showed identical science: the rebuilt forest
matched the committed artifact tree by tree with probability difference 0.0; the
three figures matched pixel for pixel; OOF log-loss differed by one ULP (1.1e-16).
The tests now assert structural/pixel identity on every platform, apply the frozen
ATOL 1e-12 to JSON floats as already done for CSV replay, and keep byte identity on
win32, where the evidence was recorded. Checkpoint 7b6f9c2 contains this change.

A first cold-start Streamlit AppTest run in one fresh environment exceeded its 60 s
timeout; immediate reruns passed in under 3 s and the full clean-clone suite passed.
It is recorded as an environment warm-up sensitivity, not a functional failure.

Remaining limitations: the Power BI parameter RutaCSV keeps the original absolute
path and must be set in Desktop; the PBIX does not yet contain the ML page;
streamlit and plotly are lower-bound, not pinned, dependencies.

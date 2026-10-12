# Project execution state

LAST_COMPLETED_PHASE = 9
G5_BASELINE = PASS_WITH_LIMITATION
G6_CANDIDATES = PASS_WITH_LIMITATION
G7_TUNING_SELECTION = PASS_WITH_LIMITATION
G8_FINAL_HOLDOUT = PASS_WITH_LIMITATION
G9_ERROR_UNCERTAINTY_INTERPRETABILITY = PASS_WITH_LIMITATION
PHASE_9_VERDICT = PASS_WITH_LIMITATION
PRIMARY_METRIC = macro_f1
BASELINE_SIGNAL_DETECTED = TRUE
NEXT_PHASE = 10_MLOPS_AND_POWER_BI_INTEGRATION

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
TESTS = PASS (91 passed in 592.35 seconds)
GIT_DIFF_CHECK = PASS
POWER_BI_STATUS = CLEAN

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

Phase 9 is complete with PASS_WITH_LIMITATION. Phase 10 has not started.
Power BI, the frozen model, raw data and earlier scientific artifacts remain
unchanged. No installation, network access, remote creation or push occurred.

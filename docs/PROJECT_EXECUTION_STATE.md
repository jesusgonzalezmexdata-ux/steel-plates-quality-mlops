# Project execution state

LAST_COMPLETED_PHASE = 8
G5_BASELINE = PASS_WITH_LIMITATION
G6_CANDIDATES = PASS_WITH_LIMITATION
G7_TUNING_SELECTION = PASS_WITH_LIMITATION
G8_FINAL_HOLDOUT = PASS_WITH_LIMITATION
PRIMARY_METRIC = macro_f1
BASELINE_SIGNAL_DETECTED = TRUE
HOLDOUT_STATUS = CONSUMED_FINAL_EVALUATION
NEXT_PHASE = 9_ERROR_UNCERTAINTY_INTERPRETABILITY

VALIDITY_SCOPE = FULL_OBSERVATION_CLASSIFICATION_ONLY
EARLY_PREDICTION_SUPPORTED = FALSE
TEMPORAL_FEATURE_AVAILABILITY = NOT_DEMONSTRATED

PHASE_5_CHECKPOINT = 6def86eb1f185a400720c95d952275b718006c75
PHASE_5_STATE_CHECKPOINT = 47f1fb6e8bd5da51a431e08610909ff3cd12e500
PHASE_6_CHECKPOINT = b60c589971d3385854326514da905164224a529b
PHASE_7_CHECKPOINT = 52132ddd052e3fde4a8dd846c5268abaf742fa69
PHASE_7_STATE_CHECKPOINT = 0e9722aaf78e65ae1613dca155eaab5e3388de27
PHASE_8_CHECKPOINT = 269b38cdced47f8c392a59b0bf9b6bbd298a363a

FINAL_MODEL_CANDIDATE = tuned_random_forest
FINAL_MODEL_CONFIG = n_estimators=300; min_samples_leaf=2; max_features=sqrt; max_depth=20; class_weight=balanced; random_state=42; n_jobs=1
FEATURE_SET = FULL_OBSERVATION_FEATURES
CV_PROTOCOL = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

The frozen Phase 7 model has now been fitted once on all 1,552 training rows
and evaluated once on the 389-row holdout. Final macro-F1 is
0.8146728101764369; the gap from frozen CV mean 0.8008 is
+0.013872810176436934 (CONSISTENT, descriptive only).
The full suite passed 68 tests before the final evaluation. No post-holdout
tuning, calibration, feature change, alternative-model evaluation, Power BI
change, installation, or push was performed. Phase 8 is complete; Phase 9
has not started. Validity remains full-observation only.

HOLDOUT_ACCESSED = TRUE
HOLDOUT_INVALIDATED = FALSE
HOLDOUT_FIRST_ACCESS = TRUE
POST_HOLDOUT_TUNING = FALSE
ALTERNATIVE_MODELS_TESTED_ON_HOLDOUT = FALSE
CALIBRATION_PERFORMED = FALSE
FINAL_MACRO_F1 = 0.8146728101764369
GENERALIZATION_GAP = +0.013872810176436934
GENERALIZATION_ASSESSMENT = CONSISTENT
TESTS = PASS (68 passed)
POWER_BI_STATUS = CLEAN

The first-access flag means first final predictive evaluation; the repository
uses logical holdout sealing, with labels previously used for stratification.
See docs/ml/07_final_holdout_evaluation.md for all final metrics, class results,
the confusion matrix, probability checks, and limitations. Prediction artifacts
and the single-execution ledger are in reports/ml/final_holdout/.

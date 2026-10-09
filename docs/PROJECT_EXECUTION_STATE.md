# Project execution state

LAST_COMPLETED_PHASE = 7
G5_BASELINE = PASS_WITH_LIMITATION
G6_CANDIDATES = PASS_WITH_LIMITATION
G7_TUNING_SELECTION = PASS_WITH_LIMITATION
PRIMARY_METRIC = macro_f1
BASELINE_SIGNAL_DETECTED = TRUE
HOLDOUT_STATUS = SEALED
NEXT_PHASE = 8_FINAL_HOLDOUT_EVALUATION

VALIDITY_SCOPE = FULL_OBSERVATION_CLASSIFICATION_ONLY
EARLY_PREDICTION_SUPPORTED = FALSE
TEMPORAL_FEATURE_AVAILABILITY = NOT_DEMONSTRATED

PHASE_5_CHECKPOINT = 6def86eb1f185a400720c95d952275b718006c75
PHASE_5_STATE_CHECKPOINT = 47f1fb6e8bd5da51a431e08610909ff3cd12e500
PHASE_6_CHECKPOINT = b60c589971d3385854326514da905164224a529b
PHASE_7_CHECKPOINT = 52132ddd052e3fde4a8dd846c5268abaf742fa69

FINAL_MODEL_CANDIDATE = tuned_random_forest
FINAL_MODEL_CONFIG = n_estimators=300; min_samples_leaf=2; max_features=sqrt; max_depth=20; class_weight=balanced; random_state=42
FEATURE_SET = FULL_OBSERVATION_FEATURES
CV_PROTOCOL = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

The baseline signal is based on five stratified folds over the 1,552-row
training partition. The 389-row holdout was not accessed, and no model
candidate tuning, calibration, Power BI change or push has been performed.
Candidate selection is valid under full-observation classification only. The
complete repository suite passed after installing the declared Streamlit and
DuckDB dependencies. The holdout remains sealed for Fase 8.
